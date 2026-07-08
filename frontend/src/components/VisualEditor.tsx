import React, { useEffect, useMemo, useRef, useState } from "react";
import { FlowBuilderChat } from './FlowBuilderChat';

import {
  DAGEdge,
  DAGEdgeType,
  DAGNode,
  DAGNodeType,
  DAGPort,
  DAGPortKind,
  DAGPortPosition,
  DAGWorkflow,
  RESOURCE_EDGE_TYPES,
} from "@/lib/flows/dagExecutor";
import { AGENT_CONFIGS, AgentName } from "@/lib/types";
import { Connector, fetchConnectors } from "@/lib/connectors";
import ToolSelectionModal from "./ToolSelectionModal";
import MemoryConfigModal from "./MemoryConfigModal";
import ConnectorConfigModal from "./ConnectorConfigModal";

interface VisualEditorProps {
  onRunWorkflow: (workflowId: string) => void;
}

interface Point {
  x: number;
  y: number;
}

interface ConnectionDraft {
  sourceNodeId: string;
  sourceHandleId: string;
  sourceKind: DAGPortKind;
  start: Point;
  current: Point;
}

const NODE_WIDTH = 230;
const NODE_HEIGHT = 108;
const HANDLE_SIZE = 12;
const RESOURCE_BOX_SIZE = 22;

const CORE_NODE_TYPES: DAGNodeType[] = [
  "trigger",
  "agent",
  "condition",
  "parallel",
  "action",
  "human_checkpoint",
  "merge",
];

const COMPONENT_NODE_TYPES: DAGNodeType[] = [
  "model",
  "tool",
  "rag",
  "vector_store",
  "buffer_memory",
  "summary_memory",
  "hippocampus_memory",
  "guardrail",
];

const TOOL_OPTIONS = ["searchWeb", "readFile", "lintCode", "run_code"];
const MODEL_OPTIONS = ["llama-3.3-70b", "qwen/qwen3-32b", "llama-3.1-8b-instant"];
const MEMORY_OPTIONS = ["Buffer Memory", "Summary Memory", "Hippocampus Memory"];
const RAG_OPTIONS = ["Chroma DB", "Workflow Knowledge Base", "Project Docs"];
const GUARDRAIL_OPTIONS = ["PII/Secrets", "Prompt Injection", "Schema Validation", "Security Review"];

const EDGE_COLORS: Record<string, string> = {
  control: "rgba(148,163,184,0.45)",
  data: "#60a5fa",
  context: "#a78bfa",
  model: "#818cf8",
  tool: "#10b981",
  memory: "#f59e0b",
  rag: "#38bdf8",
  guardrail: "#f43f5e",
  vector: "#22d3ee",
  vector_write: "#22d3ee",
  connector: "#d946ef",
  error: "#ef4444",
};

const PORT_ICONS: Record<string, string> = {
  model: "🧠",
  tool: "🛠️",
  memory: "📝",
  rag: "🔎",
  guardrail: "🛡️",
  vector: "🧲",
  connector: "🔌",
};

interface PopupOption {
  label: string;
  nodeType: DAGNodeType;
  configKey?: string;
  configValue?: string;
}

function getPopupOptions(kind: DAGPortKind): PopupOption[] {
  switch (kind) {
    case "tool":
      return TOOL_OPTIONS.map((t) => ({ label: t, nodeType: "tool" as DAGNodeType, configKey: "toolName", configValue: t }));
    case "model":
      return MODEL_OPTIONS.map((m) => ({ label: m, nodeType: "model" as DAGNodeType, configKey: "modelName", configValue: m }));
    case "memory":
      return MEMORY_OPTIONS.map((m) => ({
        label: m,
        nodeType: (m === "Buffer Memory" ? "buffer_memory" : m === "Summary Memory" ? "summary_memory" : "hippocampus_memory") as DAGNodeType,
      }));
    case "rag":
      return RAG_OPTIONS.map((r) => ({ label: r, nodeType: "rag" as DAGNodeType, configKey: "collectionName", configValue: r }));
    case "guardrail":
      return GUARDRAIL_OPTIONS.map((g) => ({ label: g, nodeType: "guardrail" as DAGNodeType, configKey: "policies", configValue: g }));
    default:
      return [];
  }
}

function labelForType(type: DAGNodeType): string {
  const labels: Record<DAGNodeType, string> = {
    trigger: "Trigger",
    agent: "Agent",
    condition: "Condition",
    parallel: "Parallel",
    action: "Action",
    human_checkpoint: "Human Checkpoint",
    merge: "Merge",
    model: "Chat Model",
    tool: "Tool",
    rag: "RAG (Chroma DB)",
    vector_store: "Vector Store",
    buffer_memory: "Buffer Memory",
    summary_memory: "Summary Memory",
    hippocampus_memory: "Hippocampus Memory",
    guardrail: "Guardrail",
    subworkflow: "Sub-Workflow",
  };
  return labels[type];
}

function getNodeColor(type: DAGNodeType, agentName?: AgentName): string {
  if (type === "agent" && agentName) return AGENT_CONFIGS[agentName]?.color ?? "#6366f1";
  const colors: Record<DAGNodeType, string> = {
    trigger: "#84cc16",
    agent: "#6366f1",
    condition: "#f59e0b",
    parallel: "#06b6d4",
    action: "#d946ef",
    human_checkpoint: "#ec4899",
    merge: "#10b981",
    model: "#818cf8",
    tool: "#10b981",
    rag: "#38bdf8",
    vector_store: "#22d3ee",
    buffer_memory: "#f59e0b",
    summary_memory: "#fb923c",
    hippocampus_memory: "#a78bfa",
    guardrail: "#f43f5e",
    subworkflow: "#3b82f6",
  };
  return colors[type];
}

function getNodeIcon(type: DAGNodeType, agentName?: AgentName): string {
  if (type === "agent" && agentName) return AGENT_CONFIGS[agentName]?.icon ?? "🤖";
  const icons: Record<DAGNodeType, string> = {
    trigger: "🔌",
    agent: "🤖",
    condition: "🔀",
    parallel: "⚡",
    action: "🚀",
    human_checkpoint: "👤",
    merge: "✅",
    model: "🧠",
    tool: "🛠️",
    rag: "🔎",
    vector_store: "🧲",
    buffer_memory: "📝",
    summary_memory: "📚",
    hippocampus_memory: "🦛",
    guardrail: "🛡️",
    subworkflow: "🔄",
  };
  return icons[type];
}

function defaultConfigForType(type: DAGNodeType): Record<string, unknown> | undefined {
  if (type === "rag") {
    return {
      provider: "chroma",
      collectionName: "workflow_knowledge",
      topK: 5,
      scoreThreshold: 0.35,
      queryMode: "combined",
      allowAgentWrites: true,
    };
  }
  if (type === "vector_store") {
    return {
      provider: "chroma",
      collectionName: "workflow_knowledge",
      persistDirectory: ".workspace/chroma",
      ingestAgentOutputs: true,
    };
  }
  if (type === "buffer_memory") {
    return {
      scope: "session",
      filePath: ".workspace/memory/{workflow_id}/{session_id}/buffer.md",
      maxTokens: 2500,
      writable: true,
      clearOnRunStart: true,
    };
  }
  if (type === "summary_memory") {
    return {
      scope: "workflow",
      filePath: ".workspace/memory/{workflow_id}/{session_id}/summary.md",
      updateOnComplete: true,
      updateOnFailure: true,
      maxSummaryTokens: 2000,
    };
  }
  if (type === "hippocampus_memory") {
    return {
      scope: "project",
      filePath: ".workspace/memory/{project_id}/hippocampus.md",
      importanceThreshold: 0.75,
      topK: 8,
      allowWrites: true,
    };
  }
  if (type === "guardrail") {
    return {
      phase: "both",
      policies: ["PII/Secrets", "Prompt Injection"],
      action: "warn",
      allowRetry: true,
    };
  }
  if (type === "model") {
    return {
      provider: "groq",
      modelName: "llama-3.3-70b-versatile",
      temperature: 0.3,
      maxTokens: 4096,
    };
  }
  if (type === "tool") {
    return {
      toolName: "searchWeb",
      description: "Search the web for additional context.",
    };
  }
  return undefined;
}

function makePort(
  id: string,
  label: string,
  direction: "input" | "output",
  kind: DAGPortKind,
  position: DAGPortPosition,
  accepts?: DAGPortKind[],
): DAGPort {
  return { id, label, direction, kind, position, accepts };
}

function getDefaultPorts(node: DAGNode): DAGPort[] {
  switch (node.type) {
    case "trigger":
      return [makePort("flow.out", "Flow", "output", "control", "right")];
    case "agent":
      return [
        makePort("flow.in", "Flow", "input", "control", "left", ["control", "error"]),
        makePort("context.in", "Context", "input", "data", "left", ["data", "context"]),
        makePort("flow.out", "Flow", "output", "control", "right"),
        makePort("data.out", "Data", "output", "data", "right"),
        makePort("error.out", "Error", "output", "error", "right"),
        makePort("model.in", "Model", "input", "model", "bottom", ["model"]),
        makePort("tools.in", "Tools", "input", "tool", "bottom", ["tool"]),
        makePort("memory.in", "Memory", "input", "memory", "bottom", ["memory"]),
        makePort("connectors.in", "Connectors", "input", "connector", "bottom", ["connector"]),
        makePort("rag.in", "RAG", "input", "rag", "bottom", ["rag"]),
        makePort("guardrails.in", "Guard", "input", "guardrail", "bottom", ["guardrail"]),
      ];
    case "condition":
      return [
        makePort("flow.in", "In", "input", "control", "left", ["control"]),
        makePort("true.out", "True", "output", "control", "right"),
        makePort("false.out", "False", "output", "control", "right"),
      ];
    case "parallel":
      return [
        makePort("flow.in", "In", "input", "control", "left", ["control"]),
        makePort("branch.a", "A", "output", "control", "right"),
        makePort("branch.b", "B", "output", "control", "right"),
      ];
    case "merge":
      return [
        makePort("flow.in.1", "In 1", "input", "control", "left", ["control"]),
        makePort("flow.in.2", "In 2", "input", "control", "left", ["control"]),
        makePort("flow.out", "Out", "output", "control", "right"),
      ];
    case "human_checkpoint":
      return [
        makePort("flow.in", "In", "input", "control", "left", ["control"]),
        makePort("approved.out", "Approve", "output", "control", "right"),
        makePort("rejected.out", "Reject", "output", "control", "right"),
      ];
    case "action":
      return [
        makePort("flow.in", "In", "input", "control", "left", ["control"]),
        makePort("payload.in", "Payload", "input", "data", "left", ["data", "context"]),
        makePort("flow.out", "Out", "output", "control", "right"),
      ];
    case "model":
      return [makePort("model.out", "Model", "output", "model", "right")];
    case "tool":
      return [makePort("tool.out", "Tool", "output", "tool", "right")];
    case "rag":
      return [
        makePort("store.in", "Store", "input", "vector", "left", ["vector"]),
        makePort("rag.out", "RAG", "output", "rag", "right"),
      ];
    case "vector_store":
      return [
        makePort("documents.in", "Docs", "input", "data", "left", ["data", "context"]),
        makePort("store.out", "Store", "output", "vector", "right"),
      ];
    case "buffer_memory":
    case "summary_memory":
    case "hippocampus_memory":
      return [
        makePort("update.in", "Update", "input", "data", "left", ["data", "context"]),
        makePort("memory.out", "Memory", "output", "memory", "right"),
      ];
    case "guardrail":
      return [makePort("guardrail.out", "Guard", "output", "guardrail", "right")];
    default:
      return [];
  }
}

function getNodePorts(node: DAGNode): DAGPort[] {
  const defaults = getDefaultPorts(node);
  const custom = node.ports ?? [];
  const seen = new Set(defaults.map((port) => port.id));
  return [...defaults, ...custom.filter((port) => !seen.has(port.id))];
}

function getPortSide(port: DAGPort): DAGPortPosition {
  if (port.position) return port.position;
  return port.direction === "input" ? "left" : "right";
}

function getPortsOnSide(node: DAGNode, side: DAGPortPosition): DAGPort[] {
  return getNodePorts(node).filter((port) => getPortSide(port) === side);
}

function getPortCenter(node: DAGNode, port: DAGPort, zoom: number): Point {
  const side = getPortSide(port);
  const sidePorts = getPortsOnSide(node, side);
  const index = Math.max(0, sidePorts.findIndex((candidate) => candidate.id === port.id));
  const count = Math.max(1, sidePorts.length);

  if (side === "left") {
    return {
      x: node.x * zoom,
      y: (node.y + ((index + 1) * NODE_HEIGHT) / (count + 1)) * zoom,
    };
  }
  if (side === "right") {
    return {
      x: (node.x + NODE_WIDTH) * zoom,
      y: (node.y + ((index + 1) * NODE_HEIGHT) / (count + 1)) * zoom,
    };
  }
  if (side === "top") {
    return {
      x: (node.x + ((index + 1) * NODE_WIDTH) / (count + 1)) * zoom,
      y: node.y * zoom,
    };
  }
  return {
    x: (node.x + ((index + 1) * NODE_WIDTH) / (count + 1)) * zoom,
    y: (node.y + NODE_HEIGHT + 27) * zoom,
  };
}

function portsCompatible(source: DAGPort, target: DAGPort): boolean {
  if (source.direction !== "output" || target.direction !== "input") return false;
  if (target.accepts?.includes(source.kind)) return true;
  if (source.kind === target.kind) return true;
  if (source.kind === "data" && target.kind === "context") return true;
  if (source.kind === "context" && target.kind === "data") return true;
  return false;
}

function inferEdgeType(source: DAGPort, target: DAGPort): DAGEdgeType {
  if (target.kind === "model" || source.kind === "model") return "model";
  if (target.kind === "tool" || source.kind === "tool") return "tool";
  if (target.kind === "memory" || source.kind === "memory") return "memory";
  if (target.kind === "rag" || source.kind === "rag") return "rag";
  if (target.kind === "guardrail" || source.kind === "guardrail") return "guardrail";
  if (source.kind === "vector" || target.kind === "vector") return "vector";
  if (source.kind === "error" || target.kind === "error") return "error";
  if (source.kind === "data" || target.kind === "data") return "data";
  if (source.kind === "context" || target.kind === "context") return "context";
  return "control";
}

function pathForEdge(start: Point, end: Point, zoom: number): string {
  const delta = Math.max(40 * zoom, Math.abs(end.x - start.x) * 0.35);
  return `M ${start.x} ${start.y} C ${start.x + delta} ${start.y}, ${end.x - delta} ${end.y}, ${end.x} ${end.y}`;
}

function configString(node: DAGNode, key: string, fallback = ""): string {
  const value = node.config?.[key];
  if (value === undefined || value === null) return fallback;
  return String(value);
}

function configNumber(node: DAGNode, key: string, fallback: number): number {
  const value = node.config?.[key];
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default function VisualEditor({ onRunWorkflow }: VisualEditorProps) {
  const [workflows, setWorkflows] = useState<DAGWorkflow[]>([]);
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState<Point>({ x: 0, y: 0 });
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [builderSessionId, setBuilderSessionId] = useState<string>(() => "bs-" + Date.now().toString(36) + Math.random().toString(36).substr(2, 5));

  const [isPanning, setIsPanning] = useState(false);
  const [connectionDraft, setConnectionDraft] = useState<ConnectionDraft | null>(null);
  const [activeMenu, setActiveMenu] = useState<{ nodeId: string; portId: string } | null>(null);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [editingToolsNodeId, setEditingToolsNodeId] = useState<string | null>(null);
  const [editingMemoryNodeId, setEditingMemoryNodeId] = useState<string | null>(null);
  const [editingConnectorsNodeId, setEditingConnectorsNodeId] = useState<string | null>(null);
  const [newInputName, setNewInputName] = useState("");
  const [newOutputName, setNewOutputName] = useState("");

  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchConnectors().then(setConnectors).catch(console.error);
    fetch("/api/workflows")
      .then((res) => res.json())
      .then((data: DAGWorkflow[]) => {
        setWorkflows(data);
        if (data.length > 0 && !activeWorkflowId) setActiveWorkflowId(data[0].id);
      })
      .catch(console.error);
  }, [activeWorkflowId]);

  const activeWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.id === activeWorkflowId) ?? null,
    [workflows, activeWorkflowId],
  );

  const selectedNode = activeWorkflow?.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedEdge = activeWorkflow?.edges.find((edge) => edge.id === selectedEdgeId) ?? null;

  const getCanvasPoint = (event: React.MouseEvent): Point => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return {
      x: event.clientX - rect.left - pan.x,
      y: event.clientY - rect.top - pan.y,
    };
  };

  const updateActiveWorkflow = (updater: (workflow: DAGWorkflow) => DAGWorkflow) => {
    setWorkflows((prev) => prev.map((workflow) => (workflow.id === activeWorkflowId ? updater(workflow) : workflow)));
  };

  const updateNodeById = (nodeId: string, updater: (node: DAGNode) => DAGNode) => {
    updateActiveWorkflow((workflow) => ({
      ...workflow,
      nodes: workflow.nodes.map((node) => (node.id === nodeId ? updater(node) : node)),
    }));
  };

  const updateSelectedNode = (updates: Partial<DAGNode>) => {
    if (!selectedNodeId) return;
    updateNodeById(selectedNodeId, (node) => ({ ...node, ...updates }));
  };

  const updateSelectedNodeConfig = (key: string, value: unknown) => {
    if (!selectedNodeId) return;
    updateNodeById(selectedNodeId, (node) => ({
      ...node,
      config: {
        ...(node.config ?? {}),
        [key]: value,
      },
    }));
  };

  const handleAddCustomPort = (direction: "input" | "output", name: string) => {
    if (!selectedNodeId || !name.trim()) return;
    const cleanName = name.trim().toLowerCase().replace(/\s+/g, "_");
    const portId = `custom.${direction}.${cleanName}`;
    updateNodeById(selectedNodeId, (node) => {
      const existingPorts = node.ports ?? [];
      if (existingPorts.find(p => p.id === portId)) return node;
      const newPort = makePort(portId, name.trim(), direction, "data", direction === "input" ? "left" : "right", ["data", "context"]);
      return { ...node, ports: [...existingPorts, newPort] };
    });
    if (direction === "input") setNewInputName("");
    else setNewOutputName("");
  };

  const handleRemoveCustomPort = (portId: string) => {
    if (!selectedNodeId) return;
    updateNodeById(selectedNodeId, (node) => ({
      ...node,
      ports: (node.ports ?? []).filter(p => p.id !== portId)
    }));
  };

  const updateSelectedEdge = (updates: Partial<DAGEdge>) => {
    if (!selectedEdgeId) return;
    updateActiveWorkflow((workflow) => ({
      ...workflow,
      edges: workflow.edges.map((edge) => (edge.id === selectedEdgeId ? { ...edge, ...updates } : edge)),
    }));
  };

  const handleCreateWorkflow = () => {
    const newWorkflow = {
      name: "New Custom Workflow",
      description: "A custom orchestration flow",
      version: "1.0",
      nodes: [],
      edges: [],
    };
    fetch("/api/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newWorkflow),
    })
      .then((res) => res.json())
      .then((saved) => {
        setWorkflows((prev) => [saved, ...prev]);
        setActiveWorkflowId(saved.id);
      });
  };

  const handleSaveWorkflow = () => {
    if (!activeWorkflow) return;
    fetch(`/api/workflows/${activeWorkflow.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(activeWorkflow),
    }).then(() => alert("Workflow Saved Successfully!"));
  };

  const handleAddNode = (type: DAGNodeType) => {
    if (!activeWorkflow) return;
    const newNode: DAGNode = {
      id: `n-${Date.now().toString(36)}`,
      type,
      label: labelForType(type),
      x: 300,
      y: 300,
      config: defaultConfigForType(type),
      useCompaction: type === "agent" ? true : undefined,
      compactionStrategy: type === "agent" ? "auto" : undefined,
      maxContextTokens: type === "agent" ? 12000 : undefined,
    };
    updateActiveWorkflow((workflow) => ({ ...workflow, nodes: [...workflow.nodes, newNode] }));
    setSelectedNodeId(newNode.id);
    setSelectedEdgeId(null);
  };

  const handleNodeMouseDown = (event: React.MouseEvent<HTMLDivElement>, nodeId: string) => {
    if (!activeWorkflow || connectionDraft) return;
    event.preventDefault();
    event.stopPropagation();
    setSelectedNodeId(nodeId);
    setSelectedEdgeId(null);
    setActiveMenu(null);
    const rect = event.currentTarget.getBoundingClientRect();
    setDragOffset({ x: event.clientX - rect.left, y: event.clientY - rect.top });
    setIsDragging(true);
  };

  const startConnection = (event: React.MouseEvent, node: DAGNode, port: DAGPort) => {
    if (port.direction !== "output") return;
    event.preventDefault();
    event.stopPropagation();
    const start = getPortCenter(node, port, zoom);
    setConnectionDraft({
      sourceNodeId: node.id,
      sourceHandleId: port.id,
      sourceKind: port.kind,
      start,
      current: start,
    });
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setActiveMenu(null);
  };

  const completeConnection = (event: React.MouseEvent, targetNode: DAGNode, targetPort: DAGPort) => {
    if (!connectionDraft || !activeWorkflow) return;
    event.preventDefault();
    event.stopPropagation();
    const sourceNode = activeWorkflow.nodes.find((node) => node.id === connectionDraft.sourceNodeId);
    const sourcePort = sourceNode ? getNodePorts(sourceNode).find((port) => port.id === connectionDraft.sourceHandleId) : null;
    if (!sourceNode || !sourcePort || sourceNode.id === targetNode.id || !portsCompatible(sourcePort, targetPort)) {
      setConnectionDraft(null);
      return;
    }

    const newEdge: DAGEdge = {
      id: `e-${Date.now().toString(36)}`,
      from: sourceNode.id,
      to: targetNode.id,
      sourceHandle: sourcePort.id,
      targetHandle: targetPort.id,
      edgeType: inferEdgeType(sourcePort, targetPort),
    };
    updateActiveWorkflow((workflow) => ({ ...workflow, edges: [...workflow.edges, newEdge] }));
    setConnectionDraft(null);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button === 0 && !e.shiftKey) {
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setActiveMenu(null);
    }
    if (e.button === 1 || e.shiftKey || e.target === canvasRef.current || (e.target as HTMLElement).id === "canvas-inner") {
      setIsPanning(true);
      setDragOffset({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isPanning) {
      setPan({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y,
      });
      return;
    }

    if (connectionDraft) {
      setConnectionDraft((prev) => (prev ? { ...prev, current: getCanvasPoint(e) } : null));
      return;
    }

    if (!isDragging || !selectedNodeId || !activeWorkflow || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - dragOffset.x - pan.x) / zoom;
    const y = (e.clientY - rect.top - dragOffset.y - pan.y) / zoom;
    updateSelectedNode({ x, y });
  };

  const stopDragging = () => {
    setIsDragging(false);
    setIsPanning(false);
    if (connectionDraft) setConnectionDraft(null);
  };

  const handleQuickAdd = (parentNode: DAGNode, port: DAGPort, option: PopupOption) => {
    if (!activeWorkflow) return;
    const newNode: DAGNode = {
      id: `n-${Date.now().toString(36)}`,
      type: option.nodeType,
      label: option.label,
      x: parentNode.x + (getPortsOnSide(parentNode, "bottom").indexOf(port)) * 60 - 40,
      y: parentNode.y + NODE_HEIGHT + 90,
      config: option.configKey
        ? { ...defaultConfigForType(option.nodeType), [option.configKey]: option.configValue }
        : defaultConfigForType(option.nodeType),
    };

    const newNodePorts = getDefaultPorts(newNode);
    const outputPort = newNodePorts.find((p) => p.direction === "output" && p.kind === port.kind);

    const newEdge: DAGEdge = {
      id: `e-${Date.now().toString(36)}`,
      from: newNode.id,
      to: parentNode.id,
      sourceHandle: outputPort?.id,
      targetHandle: port.id,
      edgeType: outputPort ? inferEdgeType(outputPort, port) : (port.kind as DAGEdgeType),
    };

    updateActiveWorkflow((wf) => ({
      ...wf,
      nodes: [...wf.nodes, newNode],
      edges: [...wf.edges, newEdge],
    }));
    setActiveMenu(null);
    setSelectedNodeId(newNode.id);
    setSelectedEdgeId(null);
  };

  const handleDisconnectPort = (edgeId: string) => {
    updateActiveWorkflow((wf) => ({
      ...wf,
      edges: wf.edges.filter((e) => e.id !== edgeId),
    }));
  };

  const renderEdges = () => {
    if (!activeWorkflow) return null;
    return (
      <svg
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          zIndex: 1,
          overflow: "visible",
        }}
      >
        <defs>
          <marker id="ve-arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255,255,255,0.35)" />
          </marker>
          <marker id="ve-arrow-selected" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#6366f1" />
          </marker>
        </defs>
        {activeWorkflow.edges.map((edge) => {
          const fromNode = activeWorkflow.nodes.find((n) => n.id === edge.from);
          const toNode = activeWorkflow.nodes.find((n) => n.id === edge.to);
          if (!fromNode || !toNode) return null;

          const sourcePort = getNodePorts(fromNode).find((p) => p.id === edge.sourceHandle);
          const targetPort = getNodePorts(toNode).find((p) => p.id === edge.targetHandle);

          const start = sourcePort
            ? getPortCenter(fromNode, sourcePort, zoom)
            : { x: (fromNode.x + NODE_WIDTH) * zoom, y: (fromNode.y + NODE_HEIGHT / 2) * zoom };
          const end = targetPort
            ? getPortCenter(toNode, targetPort, zoom)
            : { x: toNode.x * zoom, y: (toNode.y + NODE_HEIGHT / 2) * zoom };

          const path = pathForEdge(start, end, zoom);
          const isEdgeSelected = edge.id === selectedEdgeId;
          const isResourceEdge = RESOURCE_EDGE_TYPES.includes(edge.edgeType as DAGEdgeType);
          const edgeColor = isEdgeSelected
            ? "#6366f1"
            : EDGE_COLORS[edge.edgeType ?? "control"] ?? "rgba(148,163,184,0.45)";

          return (
            <g
              key={edge.id}
              style={{ pointerEvents: "auto", cursor: "pointer" }}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedNodeId(null);
                setSelectedEdgeId(edge.id);
              }}
            >
              {/* Invisible thicker hit area for easy clicking */}
              <path d={path} fill="none" stroke="transparent" strokeWidth={20} />
              <path
                d={path}
                fill="none"
                stroke={edgeColor}
                strokeWidth={isEdgeSelected ? 3 : 2}
                strokeDasharray={isResourceEdge && !isEdgeSelected ? "6 3" : "none"}
                markerEnd={isEdgeSelected ? "url(#ve-arrow-selected)" : "url(#ve-arrow)"}
              />
              <circle cx={end.x} cy={end.y} r={4 * zoom} fill={isEdgeSelected ? "#6366f1" : edgeColor} />
            </g>
          );
        })}
        {connectionDraft && (
          <path
            d={pathForEdge(connectionDraft.start, connectionDraft.current, 1)}
            fill="none"
            stroke="#f59e0b"
            strokeWidth={2}
            strokeDasharray="4 4"
            style={{ pointerEvents: "none" }}
          />
        )}
      </svg>
    );
  };

  const renderPorts = (node: DAGNode) => {
    return getNodePorts(node).map((port) => {
      const side = getPortSide(port);
      const isBottomResource = side === "bottom";
      const isInput = port.direction === "input";
      const isOutput = port.direction === "output";

      if (isBottomResource) {
        const center = getPortCenter(node, port, zoom);
        const left = center.x / zoom - node.x;
        const top = center.y / zoom - node.y;

        const isMenuOpen = activeMenu?.nodeId === node.id && activeMenu.portId === port.id;
        const iconColor =
          port.kind === "tool" ? "#10b981" : port.kind === "memory" ? "#f59e0b" : port.kind === "model" ? "#818cf8" : port.kind === "guardrail" ? "#f43f5e" : "#38bdf8";

        // Check how many edges are connected to this port
        const connectedEdges = activeWorkflow?.edges.filter(
          (e) => (e.to === node.id && e.targetHandle === port.id) || (e.from === node.id && e.sourceHandle === port.id),
        ) ?? [];
        const isConnected = connectedEdges.length > 0;
        const displayIcon = isConnected ? "●" : (PORT_ICONS[port.kind] || "+");

        const popupOptions = getPopupOptions(port.kind);

        return (
          <div
            key={port.id}
            onClick={(e) => {
              e.stopPropagation();
              setActiveMenu(isMenuOpen ? null : { nodeId: node.id, portId: port.id });
            }}
            onMouseUp={(e) => isInput && completeConnection(e, node, port)}
            style={{
              position: "absolute",
              left: `${left - RESOURCE_BOX_SIZE / 2}px`,
              top: `${top - RESOURCE_BOX_SIZE / 2}px`,
              width: `${RESOURCE_BOX_SIZE}px`,
              height: `${RESOURCE_BOX_SIZE}px`,
              borderRadius: "5px",
              background: isConnected ? `${iconColor}20` : "rgba(15,23,42,0.95)",
              border: `1.5px solid ${iconColor}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: iconColor,
              fontSize: isConnected ? "10px" : "11px",
              boxShadow: `0 0 8px ${iconColor}44`,
              zIndex: 30,
              transition: "all 0.15s ease",
            }}
          >
            {displayIcon}
            {/* Vertical connector line up to the node */}
            <div
              style={{
                position: "absolute",
                top: "-18px",
                width: "2px",
                height: "16px",
                background: isConnected ? iconColor : "rgba(148,163,184,0.3)",
                pointerEvents: "none",
                transition: "background 0.2s",
              }}
            />
            {/* Port label */}
            <span
              style={{
                position: "absolute",
                top: "26px",
                fontSize: "8px",
                color: isConnected ? iconColor : "#94a3b8",
                whiteSpace: "nowrap",
                pointerEvents: "none",
                fontWeight: isConnected ? 600 : 400,
                letterSpacing: "0.03em",
              }}
            >
              {port.label}{isConnected ? ` (${connectedEdges.length})` : ""}
            </span>

            {/* Connection count badge */}
            {isConnected && (
              <div
                style={{
                  position: "absolute",
                  top: "-6px",
                  right: "-6px",
                  width: "14px",
                  height: "14px",
                  borderRadius: "50%",
                  background: iconColor,
                  color: "#0f172a",
                  fontSize: "8px",
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  pointerEvents: "none",
                }}
              >
                {connectedEdges.length}
              </div>
            )}

            {/* Popup Quick-Add Menu */}
            {isMenuOpen && (
              <div
                style={{
                  position: "absolute",
                  top: "38px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  background: "linear-gradient(135deg, #1e293b, #0f172a)",
                  border: "1px solid #334155",
                  borderRadius: "10px",
                  padding: "10px",
                  width: "180px",
                  zIndex: 50,
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                  boxShadow: "0 12px 32px rgba(0,0,0,0.6)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div style={{ fontSize: "10px", color: iconColor, fontWeight: 700, marginBottom: "4px", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                  Add {port.label}
                </div>

                {/* Available options */}
                {port.kind === 'tool' ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingToolsNodeId(node.id);
                      setActiveMenu(null);
                    }}
                    style={{
                      display: "flex", alignItems: "center", gap: "6px", padding: "6px 8px", borderRadius: "6px", border: "none",
                      background: "rgba(255,255,255,0.04)", color: "#e2e8f0", fontSize: "11px", cursor: "pointer", textAlign: "left", transition: "background 0.12s"
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = `${iconColor}22`)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                  >
                    <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: iconColor, flexShrink: 0 }} />
                    Configure Tools
                  </button>
                ) : port.kind === 'memory' ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingMemoryNodeId(node.id);
                      setActiveMenu(null);
                    }}
                    style={{
                      display: "flex", alignItems: "center", gap: "6px", padding: "6px 8px", borderRadius: "6px", border: "none",
                      background: "rgba(255,255,255,0.04)", color: "#e2e8f0", fontSize: "11px", cursor: "pointer", textAlign: "left", transition: "background 0.12s"
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = `${iconColor}22`)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                  >
                    <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: iconColor, flexShrink: 0 }} />
                    Configure Memory
                  </button>
                ) : port.kind === 'connector' ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingConnectorsNodeId(node.id);
                      setActiveMenu(null);
                    }}
                    style={{
                      display: "flex", alignItems: "center", gap: "6px", padding: "6px 8px", borderRadius: "6px", border: "none",
                      background: "rgba(255,255,255,0.04)", color: "#e2e8f0", fontSize: "11px", cursor: "pointer", textAlign: "left", transition: "background 0.12s"
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = `${iconColor}22`)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                  >
                    <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: iconColor, flexShrink: 0 }} />
                    Configure Connectors
                  </button>
                ) : (
                  popupOptions.map((opt) => (
                    <button
                      key={opt.label}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleQuickAdd(node, port, opt);
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "6px 8px",
                        borderRadius: "6px",
                        border: "none",
                        background: "rgba(255,255,255,0.04)",
                        color: "#e2e8f0",
                        fontSize: "11px",
                        cursor: "pointer",
                        textAlign: "left",
                        transition: "background 0.12s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = `${iconColor}22`)}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                    >
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: iconColor, flexShrink: 0 }} />
                      {opt.label}
                    </button>
                  ))
                )}

                {/* Connected items with disconnect */}
                {connectedEdges.length > 0 && (
                  <>
                    <div style={{ height: "1px", background: "#334155", margin: "4px 0" }} />
                    <div style={{ fontSize: "9px", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em" }}>Connected</div>
                    {connectedEdges.map((ce) => {
                      const connectedNode = activeWorkflow?.nodes.find(
                        (n) => (ce.to === node.id ? n.id === ce.from : n.id === ce.to),
                      );
                      return (
                        <div
                          key={ce.id}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "4px 6px",
                            borderRadius: "5px",
                            background: `${iconColor}12`,
                            fontSize: "10px",
                            color: "#cbd5e1",
                          }}
                        >
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "110px" }}>
                            {connectedNode?.label ?? ce.id}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDisconnectPort(ce.id);
                            }}
                            style={{
                              background: "none",
                              border: "none",
                              color: "#ef4444",
                              cursor: "pointer",
                              fontSize: "12px",
                              padding: "0 2px",
                              lineHeight: 1,
                            }}
                            title="Disconnect"
                          >
                            ✕
                          </button>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            )}
          </div>
        );
      }

      // Draw standard side handle (left/right circles)
      const center = getPortCenter(node, port, zoom);
      const left = center.x / zoom - node.x;
      const top = center.y / zoom - node.y;

      const handleColor = port.direction === "output"
        ? EDGE_COLORS[port.kind] ?? "#10b981"
        : "#94a3b8";

      return (
        <div
          key={port.id}
          onMouseDown={(e) => isOutput && startConnection(e, node, port)}
          onMouseUp={(e) => isInput && completeConnection(e, node, port)}
          style={{
            position: "absolute",
            left: `${left - HANDLE_SIZE / 2}px`,
            top: `${top - HANDLE_SIZE / 2}px`,
            width: `${HANDLE_SIZE}px`,
            height: `${HANDLE_SIZE}px`,
            borderRadius: "50%",
            background: handleColor,
            border: "2px solid #0f172a",
            cursor: port.direction === "output" ? "crosshair" : "default",
            zIndex: 25,
            transition: "transform 0.12s",
          }}
          title={`${port.label} (${port.kind})`}
          onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.3)")}
          onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
        />
      );
    });
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 320px", height: "100%" }}>
      {/* Left Sidebar - Workflow List */}
      <aside style={{ borderRight: "1px solid var(--border-primary)", background: "rgba(10,14,24,0.9)", padding: "14px", overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
          <div style={{ fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>
            Workflows
          </div>
          <button
            onClick={handleCreateWorkflow}
            style={{
              background: "rgba(99,102,241,0.2)",
              color: "#a5b4fc",
              border: "none",
              padding: "4px 8px",
              borderRadius: "4px",
              fontSize: "11px",
              cursor: "pointer",
            }}
          >
            + New
          </button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {workflows.map((wf) => {
            const active = wf.id === activeWorkflowId;
            return (
              <button
                key={wf.id}
                onClick={() => {
                  setActiveWorkflowId(wf.id);
                  setSelectedNodeId(null);
                  setSelectedEdgeId(null);
                }}
                style={{
                  textAlign: "left",
                  padding: "10px 12px",
                  borderRadius: "10px",
                  border: active ? "1px solid rgba(99,102,241,0.5)" : "1px solid var(--border-primary)",
                  background: active ? "rgba(99,102,241,0.15)" : "rgba(255,255,255,0.03)",
                  color: active ? "#c7d2fe" : "var(--text-secondary)",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "13px", color: active ? "#e0e7ff" : "#d1d5db" }}>{wf.name}</div>
                <div style={{ fontSize: "11px", marginTop: "4px", opacity: 0.8 }}>{wf.description}</div>
              </button>
            );
          })}
        </div>

        <div style={{ marginTop: "20px", paddingTop: "14px", borderTop: "1px solid var(--border-primary)" }}>
          <div style={{ fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "10px" }}>
            Add Components
          </div>
          {/* Core Nodes */}
          {CORE_NODE_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => handleAddNode(type)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "12px",
                color: "var(--text-secondary)",
                marginBottom: "6px",
                width: "100%",
                background: "transparent",
                border: "1px solid rgba(255,255,255,0.1)",
                padding: "8px",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              <span style={{ width: "8px", height: "8px", borderRadius: "999px", background: getNodeColor(type) }} />
              <span>+ Add {labelForType(type)}</span>
            </button>
          ))}
          {/* Component Nodes */}
          <div style={{ fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", marginTop: "16px", marginBottom: "10px" }}>
            Resources
          </div>
          {COMPONENT_NODE_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => handleAddNode(type)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "12px",
                color: "var(--text-secondary)",
                marginBottom: "6px",
                width: "100%",
                background: "transparent",
                border: "1px solid rgba(255,255,255,0.1)",
                padding: "8px",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              <span style={{ width: "8px", height: "8px", borderRadius: "999px", background: getNodeColor(type) }} />
              <span>+ Add {labelForType(type)}</span>
            </button>
          ))}
        </div>
      </aside>

      {/* Main Canvas Area */}
      <section style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Canvas Toolbar */}
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-primary)", background: "rgba(9,12,20,0.9)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: "15px", fontWeight: 700, color: "#e5e7eb" }}>{activeWorkflow?.name || "Loading..."}</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>Interactive Workflow Builder</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button onClick={() => setIsChatOpen(prev => !prev)} style={{ padding: "8px 14px", borderRadius: "9px", border: isChatOpen ? "1px solid rgba(99,102,241,0.6)" : "1px solid var(--border-primary)", background: isChatOpen ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.04)", color: isChatOpen ? "#a5b4fc" : "#d1d5db", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>✨ AI Architect</button>
            <div style={{ width: "1px", height: "20px", background: "var(--border-primary)", margin: "0 4px" }} />
            <button onClick={() => setZoom((z) => Math.max(0.6, Number((z - 0.1).toFixed(2))))} style={{ padding: "6px 10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.04)", color: "#d1d5db", cursor: "pointer" }}>-</button>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "#94a3b8", minWidth: "52px", textAlign: "center" }}>{Math.round(zoom * 100)}%</div>
            <button onClick={() => setZoom((z) => Math.min(1.8, Number((z + 0.1).toFixed(2))))} style={{ padding: "6px 10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.04)", color: "#d1d5db", cursor: "pointer" }}>+</button>

            <button onClick={handleSaveWorkflow} style={{ marginLeft: "6px", padding: "8px 14px", borderRadius: "9px", border: "1px solid rgba(16,185,129,0.4)", background: "rgba(16,185,129,0.1)", color: "#34d399", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}>Save Workflow</button>
            <button onClick={() => activeWorkflow && onRunWorkflow(activeWorkflow.id)} style={{ marginLeft: "6px", padding: "8px 14px", borderRadius: "9px", border: "1px solid rgba(16,185,129,0.4)", background: "linear-gradient(135deg, rgba(16,185,129,0.35), rgba(5,150,105,0.22))", color: "#ecfdf5", fontSize: "12px", fontWeight: 700, cursor: "pointer" }}>Run Workflow</button>
          </div>
        </div>

        {/* Canvas */}
        <div
          ref={canvasRef}
          onClick={() => { setSelectedNodeId(null); setSelectedEdgeId(null); }}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={stopDragging}
          onMouseLeave={stopDragging}
          onMouseDown={handleCanvasMouseDown}
          style={{
            position: "relative",
            flex: 1,
            overflow: "hidden",
            backgroundColor: "#070b14",
            backgroundImage: "linear-gradient(rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.08) 1px, transparent 1px)",
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
            backgroundPosition: `${pan.x}px ${pan.y}px`,
            cursor: isPanning ? "grabbing" : "grab",
          }}
        >
                    {isChatOpen && (
            <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, zIndex: 100, boxShadow: "5px 0 20px rgba(0,0,0,0.5)" }}>
              <FlowBuilderChat 
                sessionId={builderSessionId} 
                workflowId={activeWorkflowId || undefined} 
                onClose={() => setIsChatOpen(false)}
                onWorkflowProposal={(wf) => {
                  updateActiveWorkflow(() => wf);
                }}
              />
            </div>
          )}
          <div id="canvas-inner"  style={{ position: "absolute", inset: 0, transform: `translate(${pan.x}px, ${pan.y}px)` }}>
            {renderEdges()}
            {activeWorkflow?.nodes.map((node) => {
              const isSelected = node.id === selectedNodeId;
              const nodeColor = getNodeColor(node.type, node.agentName);
              const nodeIcon = getNodeIcon(node.type, node.agentName);

              return (
                <div
                  key={node.id}
                  style={{ position: "absolute", left: node.x * zoom, top: node.y * zoom }}
                >
                  <div
                    onClick={(e) => { e.stopPropagation(); setSelectedNodeId(node.id); setSelectedEdgeId(null); setActiveMenu(null); }}
                    onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                    style={{
                      position: "relative",
                      width: NODE_WIDTH * zoom,
                      height: NODE_HEIGHT * zoom,
                      borderRadius: 12 * zoom,
                      border: `1px solid ${isSelected ? nodeColor : "rgba(148,163,184,0.28)"}`,
                      background: "linear-gradient(135deg, rgba(15,23,42,0.96), rgba(9,14,28,0.98))",
                      boxShadow: isSelected ? `0 0 0 1px ${nodeColor}, 0 18px 38px rgba(2,6,23,0.65)` : "none",
                      zIndex: isSelected ? 20 : 10,
                      cursor: isDragging && isSelected ? "grabbing" : "pointer",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "center",
                    }}
                  >
                    <div style={{ height: "4px", background: nodeColor, opacity: 0.9, flexShrink: 0, borderTopLeftRadius: 10 * zoom, borderTopRightRadius: 10 * zoom }} />
                    <div style={{ padding: `${10 * zoom}px ${12 * zoom}px`, display: "flex", alignItems: "center", gap: `${10 * zoom}px`, flex: 1 }}>
                      <div style={{ width: `${30 * zoom}px`, height: `${30 * zoom}px`, borderRadius: `${8 * zoom}px`, background: `${nodeColor}24`, color: nodeColor, display: "flex", alignItems: "center", justifyContent: "center", fontSize: `${16 * zoom}px`, flexShrink: 0 }}>
                        {nodeIcon}
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: `${12 * zoom}px`, fontWeight: 700, color: "#e2e8f0", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{node.label}</div>
                        <div style={{ fontSize: `${10 * zoom}px`, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em" }}>{labelForType(node.type)}</div>
                      </div>
                    </div>
                  </div>
                  {/* Render the ports (handles) for this node */}
                  {renderPorts(node)}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Right Sidebar - Inspector */}
      <aside style={{ borderLeft: "1px solid var(--border-primary)", background: "rgba(10,14,24,0.9)", padding: "14px", overflowY: "auto" }}>
        <div style={{ fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)", marginBottom: "8px" }}>
          {selectedNode ? "Node Inspector" : selectedEdge ? "Edge Inspector" : "Workflow Config"}
        </div>
        {!selectedNode && !selectedEdge && activeWorkflow && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ padding: "10px", borderRadius: "9px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)" }}>
              <div style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "6px" }}>Workflow Name</div>
              <input type="text" value={activeWorkflow.name} onChange={(e) => updateActiveWorkflow((w) => ({ ...w, name: e.target.value }))} style={{ width: "100%", background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-primary)", color: "white", padding: "8px", borderRadius: "4px", outline: "none", fontSize: "12px" }} />
            </div>
          </div>
        )}
        {selectedNode && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {/* Header */}
            <div style={{ padding: "12px", borderRadius: "10px", border: `1px solid ${getNodeColor(selectedNode.type, selectedNode.agentName)}44`, background: `${getNodeColor(selectedNode.type, selectedNode.agentName)}11` }}>
              <input type="text" value={selectedNode.label} onChange={(e) => updateSelectedNode({ label: e.target.value })} style={{ width: "100%", background: "transparent", border: "none", color: "#e0e7ff", fontWeight: 700, fontSize: "13px", outline: "none" }} />
              <div style={{ color: getNodeColor(selectedNode.type, selectedNode.agentName), fontSize: "11px", marginTop: "4px" }}>{labelForType(selectedNode.type)}</div>
              <div style={{ color: "#64748b", fontSize: "10px", fontFamily: "var(--font-mono)", marginTop: "2px" }}>{selectedNode.id}</div>
            </div>

            {/* Agent-specific fields */}
            {selectedNode.type === "agent" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Agent Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Agent Name</div>
                  <select
                    value={selectedNode.agentName ?? ""}
                    onChange={(e) => updateSelectedNode({ agentName: (e.target.value || undefined) as AgentName | undefined })}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}
                  >
                    <option value="">Select agent...</option>
                    {Object.keys(AGENT_CONFIGS).map((name) => (
                      <option key={name} value={name}>{AGENT_CONFIGS[name as AgentName]?.displayName ?? name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Compaction</div>
                  <select
                    value={selectedNode.compactionStrategy ?? "auto"}
                    onChange={(e) => updateSelectedNode({ compactionStrategy: e.target.value as DAGNode["compactionStrategy"] })}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}
                  >
                    <option value="off">Off</option>
                    <option value="auto">Auto</option>
                    <option value="aggressive">Aggressive</option>
                    <option value="memory_first">Memory First</option>
                    <option value="rag_first">RAG First</option>
                  </select>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Max Context Tokens</div>
                  <input
                    type="number"
                    value={selectedNode.maxContextTokens ?? 12000}
                    onChange={(e) => updateSelectedNode({ maxContextTokens: parseInt(e.target.value) || 12000 })}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}
                  />
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
                  <input
                    type="checkbox"
                    checked={!!selectedNode.config?.canWriteGlobalState}
                    onChange={(e) => updateSelectedNodeConfig("canWriteGlobalState", e.target.checked)}
                    id="global-state-toggle"
                  />
                  <label htmlFor="global-state-toggle" style={{ color: "#94a3b8", fontSize: "11px", cursor: "pointer" }}>Write to Global State</label>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
                  <input
                    type="checkbox"
                    checked={!!selectedNode.config?.runPerItem}
                    onChange={(e) => updateSelectedNodeConfig("runPerItem", e.target.checked)}
                    id="run-per-item-toggle"
                  />
                  <label htmlFor="run-per-item-toggle" style={{ color: "#94a3b8", fontSize: "11px", cursor: "pointer" }}>Run Per Item (Map-Reduce)</label>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
                  <input
                    type="checkbox"
                    checked={!!selectedNode.config?.requireHumanApproval}
                    onChange={(e) => updateSelectedNodeConfig("requireHumanApproval", e.target.checked)}
                    id="hitl-toggle"
                  />
                  <label htmlFor="hitl-toggle" style={{ color: "#94a3b8", fontSize: "11px", cursor: "pointer" }}>Require Human Approval (HITL)</label>
                </div>
                {/* Connected resources summary */}
                {(() => {
                  const agentEdges = activeWorkflow?.edges.filter((e) => e.to === selectedNode.id && RESOURCE_EDGE_TYPES.includes(e.edgeType as DAGEdgeType)) ?? [];
                  if (agentEdges.length === 0) return null;
                  return (
                    <div style={{ marginTop: "4px" }}>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>Connected Resources</div>
                      {agentEdges.map((ae) => {
                        const resourceNode = activeWorkflow?.nodes.find((n) => n.id === ae.from);
                        const color = EDGE_COLORS[ae.edgeType ?? "control"] ?? "#94a3b8";
                        return (
                          <div key={ae.id} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "3px 0", fontSize: "11px" }}>
                            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: color, flexShrink: 0 }} />
                            <span style={{ color: "#cbd5e1" }}>{resourceNode?.label ?? ae.from}</span>
                            <span style={{ color: "#64748b", fontSize: "9px" }}>{ae.edgeType}</span>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}

                {/* Dynamic Ports UI */}
                <div style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>Dynamic Inputs</div>
                  {(selectedNode.ports ?? []).filter(p => p.id.startsWith("custom.input.")).map(p => (
                    <div key={p.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px", marginBottom: "4px", fontSize: "11px", color: "#cbd5e1" }}>
                      <span>{p.label}</span>
                      <button onClick={() => handleRemoveCustomPort(p.id)} style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "12px", padding: "0 4px" }}>✕</button>
                    </div>
                  ))}
                  <div style={{ display: "flex", gap: "4px", marginTop: "4px" }}>
                    <input type="text" placeholder="New Input..." value={newInputName} onChange={e => setNewInputName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddCustomPort("input", newInputName)} style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "4px 6px", borderRadius: "4px", fontSize: "11px" }} />
                    <button onClick={() => handleAddCustomPort("input", newInputName)} style={{ padding: "4px 8px", borderRadius: "4px", border: "none", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", cursor: "pointer", fontSize: "11px" }}>Add</button>
                  </div>

                  <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", margin: "12px 0 6px 0" }}>Dynamic Outputs</div>
                  {(selectedNode.ports ?? []).filter(p => p.id.startsWith("custom.output.")).map(p => (
                    <div key={p.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px", marginBottom: "4px", fontSize: "11px", color: "#cbd5e1" }}>
                      <span>{p.label}</span>
                      <button onClick={() => handleRemoveCustomPort(p.id)} style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "12px", padding: "0 4px" }}>✕</button>
                    </div>
                  ))}
                  <div style={{ display: "flex", gap: "4px", marginTop: "4px" }}>
                    <input type="text" placeholder="New Output..." value={newOutputName} onChange={e => setNewOutputName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddCustomPort("output", newOutputName)} style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "4px 6px", borderRadius: "4px", fontSize: "11px" }} />
                    <button onClick={() => handleAddCustomPort("output", newOutputName)} style={{ padding: "4px 8px", borderRadius: "4px", border: "none", background: "rgba(16,185,129,0.2)", color: "#6ee7b7", cursor: "pointer", fontSize: "11px" }}>Add</button>
                  </div>
                </div>
              </div>
            )}

            {/* Sub-Workflow node config */}
            {selectedNode.type === "subworkflow" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Sub-Workflow Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Target Workflow</div>
                  <select value={configString(selectedNode, "targetWorkflowId", "")} onChange={(e) => updateSelectedNodeConfig("targetWorkflowId", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="">Select workflow...</option>
                    {workflows.map((wf) => (
                      <option key={wf.id} value={wf.id}>{wf.name}</option>
                    ))}
                  </select>
                </div>
                
                {/* Dynamic Ports UI */}
                <div style={{ marginTop: "8px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>Dynamic Inputs</div>
                  {(selectedNode.ports ?? []).filter(p => p.id.startsWith("custom.input.")).map(p => (
                    <div key={p.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px", marginBottom: "4px", fontSize: "11px", color: "#cbd5e1" }}>
                      <span>{p.label}</span>
                      <button onClick={() => handleRemoveCustomPort(p.id)} style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "12px", padding: "0 4px" }}>✕</button>
                    </div>
                  ))}
                  <div style={{ display: "flex", gap: "4px", marginTop: "4px" }}>
                    <input type="text" placeholder="New Input..." value={newInputName} onChange={e => setNewInputName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddCustomPort("input", newInputName)} style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "4px 6px", borderRadius: "4px", fontSize: "11px" }} />
                    <button onClick={() => handleAddCustomPort("input", newInputName)} style={{ padding: "4px 8px", borderRadius: "4px", border: "none", background: "rgba(99,102,241,0.2)", color: "#a5b4fc", cursor: "pointer", fontSize: "11px" }}>Add</button>
                  </div>

                  <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", margin: "12px 0 6px 0" }}>Dynamic Outputs</div>
                  {(selectedNode.ports ?? []).filter(p => p.id.startsWith("custom.output.")).map(p => (
                    <div key={p.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px", marginBottom: "4px", fontSize: "11px", color: "#cbd5e1" }}>
                      <span>{p.label}</span>
                      <button onClick={() => handleRemoveCustomPort(p.id)} style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "12px", padding: "0 4px" }}>✕</button>
                    </div>
                  ))}
                  <div style={{ display: "flex", gap: "4px", marginTop: "4px" }}>
                    <input type="text" placeholder="New Output..." value={newOutputName} onChange={e => setNewOutputName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddCustomPort("output", newOutputName)} style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "4px 6px", borderRadius: "4px", fontSize: "11px" }} />
                    <button onClick={() => handleAddCustomPort("output", newOutputName)} style={{ padding: "4px 8px", borderRadius: "4px", border: "none", background: "rgba(16,185,129,0.2)", color: "#6ee7b7", cursor: "pointer", fontSize: "11px" }}>Add</button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Condition node config */}
            {selectedNode.type === "condition" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Condition Expression</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Python Expression</div>
                  <input value={configString(selectedNode, "expression", "context.get('developer_output', {}).get('needs_revision')")} onChange={(e) => updateSelectedNodeConfig("expression", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px", fontFamily: "var(--font-mono)" }} />
                  <div style={{ fontSize: "9px", color: "#64748b", marginTop: "4px" }}>Evaluates to True or False to activate edges labeled "True" or "False".</div>
                </div>
              </div>
            )}
            
            {/* Trigger node config */}
            {selectedNode.type === "trigger" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Trigger Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Trigger Type</div>
                  <select value={configString(selectedNode, "triggerType", "manual")} onChange={(e) => updateSelectedNodeConfig("triggerType", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="manual">Manual Execution</option>
                    <option value="webhook">Webhook</option>
                    <option value="schedule">Schedule (Cron)</option>
                  </select>
                </div>
                {configString(selectedNode, "triggerType", "manual") === "schedule" && (
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Cron Expression</div>
                    <input value={configString(selectedNode, "cronExpression", "0 0 * * *")} onChange={(e) => updateSelectedNodeConfig("cronExpression", e.target.value)} placeholder="0 0 * * *" style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px", fontFamily: "var(--font-mono)" }} />
                  </div>
                )}
                {configString(selectedNode, "triggerType", "manual") === "webhook" && (
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Webhook Endpoint</div>
                    <div style={{ fontSize: "11px", color: "#6ee7b7", background: "rgba(16,185,129,0.1)", padding: "4px 8px", borderRadius: "4px", border: "1px dashed rgba(16,185,129,0.3)", userSelect: "all" }}>
                      /api/webhook/{activeWorkflowId}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Model node config */}
            {selectedNode.type === "model" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Model Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Provider</div>
                  <input value={configString(selectedNode, "provider", "groq")} onChange={(e) => updateSelectedNodeConfig("provider", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Model Name</div>
                  <select value={configString(selectedNode, "modelName", "")} onChange={(e) => updateSelectedNodeConfig("modelName", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="">Select model...</option>
                    {MODEL_OPTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Temperature</div>
                    <input type="number" step="0.1" min="0" max="2" value={configNumber(selectedNode, "temperature", 0.3)} onChange={(e) => updateSelectedNodeConfig("temperature", parseFloat(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                  </div>
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Max Tokens</div>
                    <input type="number" value={configNumber(selectedNode, "maxTokens", 4096)} onChange={(e) => updateSelectedNodeConfig("maxTokens", parseInt(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                  </div>
                </div>
              </div>
            )}

            {/* Tool node config */}
            {selectedNode.type === "tool" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Tool Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Tool Name</div>
                  <select value={configString(selectedNode, "toolName", "")} onChange={(e) => { updateSelectedNodeConfig("toolName", e.target.value); updateSelectedNode({ label: e.target.value }); }} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="">Select tool...</option>
                    {TOOL_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Description</div>
                  <textarea value={configString(selectedNode, "description", "")} onChange={(e) => updateSelectedNodeConfig("description", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px", minHeight: "50px", resize: "vertical" }} />
                </div>
              </div>
            )}

            {/* Memory node configs */}
            {(selectedNode.type === "buffer_memory" || selectedNode.type === "summary_memory" || selectedNode.type === "hippocampus_memory") && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Memory Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Scope</div>
                  <select value={configString(selectedNode, "scope", "session")} onChange={(e) => updateSelectedNodeConfig("scope", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="session">Session</option>
                    <option value="workflow">Workflow</option>
                    <option value="project">Project</option>
                  </select>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>File Path</div>
                  <input value={configString(selectedNode, "filePath", "")} onChange={(e) => updateSelectedNodeConfig("filePath", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px", fontFamily: "var(--font-mono)" }} />
                </div>
                {selectedNode.type === "buffer_memory" && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                    <div>
                      <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Max Tokens</div>
                      <input type="number" value={configNumber(selectedNode, "maxTokens", 2500)} onChange={(e) => updateSelectedNodeConfig("maxTokens", parseInt(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", paddingTop: "18px" }}>
                      <input type="checkbox" checked={!!selectedNode.config?.clearOnRunStart} onChange={(e) => updateSelectedNodeConfig("clearOnRunStart", e.target.checked)} />
                      <span style={{ color: "#94a3b8", fontSize: "11px" }}>Clear on start</span>
                    </div>
                  </div>
                )}
                {selectedNode.type === "summary_memory" && (
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Max Summary Tokens</div>
                    <input type="number" value={configNumber(selectedNode, "maxSummaryTokens", 2000)} onChange={(e) => updateSelectedNodeConfig("maxSummaryTokens", parseInt(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                  </div>
                )}
                {selectedNode.type === "hippocampus_memory" && (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                    <div>
                      <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Top K</div>
                      <input type="number" value={configNumber(selectedNode, "topK", 8)} onChange={(e) => updateSelectedNodeConfig("topK", parseInt(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                    </div>
                    <div>
                      <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Importance</div>
                      <input type="number" step="0.05" min="0" max="1" value={configNumber(selectedNode, "importanceThreshold", 0.75)} onChange={(e) => updateSelectedNodeConfig("importanceThreshold", parseFloat(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* RAG node config */}
            {selectedNode.type === "rag" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>RAG Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Collection</div>
                  <select value={configString(selectedNode, "collectionName", "")} onChange={(e) => updateSelectedNodeConfig("collectionName", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="">Select collection...</option>
                    {RAG_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Top K</div>
                    <input type="number" value={configNumber(selectedNode, "topK", 5)} onChange={(e) => updateSelectedNodeConfig("topK", parseInt(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                  </div>
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Score Threshold</div>
                    <input type="number" step="0.05" min="0" max="1" value={configNumber(selectedNode, "scoreThreshold", 0.35)} onChange={(e) => updateSelectedNodeConfig("scoreThreshold", parseFloat(e.target.value))} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }} />
                  </div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Query Mode</div>
                  <select value={configString(selectedNode, "queryMode", "combined")} onChange={(e) => updateSelectedNodeConfig("queryMode", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="combined">Combined</option>
                    <option value="semantic">Semantic</option>
                    <option value="keyword">Keyword</option>
                  </select>
                </div>
              </div>
            )}

            {/* Guardrail node config */}
            {selectedNode.type === "guardrail" && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Guardrail Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Phase</div>
                  <select value={configString(selectedNode, "phase", "both")} onChange={(e) => updateSelectedNodeConfig("phase", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="input">Input</option>
                    <option value="output">Output</option>
                    <option value="both">Both</option>
                  </select>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Policies</div>
                  {GUARDRAIL_OPTIONS.map((pol) => {
                    const currentPolicies: string[] = (selectedNode.config?.policies as string[]) ?? [];
                    const isChecked = currentPolicies.includes(pol);
                    return (
                      <label key={pol} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "2px 0", fontSize: "11px", color: "#cbd5e1", cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {
                            const updated = isChecked ? currentPolicies.filter((p) => p !== pol) : [...currentPolicies, pol];
                            updateSelectedNodeConfig("policies", updated);
                          }}
                        />
                        {pol}
                      </label>
                    );
                  })}
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Action</div>
                  <select value={configString(selectedNode, "action", "warn")} onChange={(e) => updateSelectedNodeConfig("action", e.target.value)} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="warn">Warn</option>
                    <option value="block">Block</option>
                    <option value="flag">Flag</option>
                  </select>
                </div>
              </div>
            )}

            {/* Connector node config */}
            {(selectedNode.type === "trigger" || selectedNode.type === "action") && (
              <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Connector Config</div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Connector ID</div>
                  <select value={selectedNode.connectorId ?? ""} onChange={(e) => updateSelectedNode({ connectorId: e.target.value })} style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px" }}>
                    <option value="">Select connector...</option>
                    {connectors.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Config (JSON)</div>
                  <textarea
                    value={configString(selectedNode, "connectorConfig", "{}")}
                    onChange={(e) => updateSelectedNodeConfig("connectorConfig", e.target.value)}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px", minHeight: "60px", fontFamily: "var(--font-mono)", resize: "vertical" }}
                  />
                </div>
              </div>
            )}

            {/* Description field for all nodes */}
            <div style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)" }}>
              <div style={{ color: "#94a3b8", fontSize: "11px", marginBottom: "4px" }}>Description</div>
              <textarea
                value={selectedNode.description ?? ""}
                onChange={(e) => updateSelectedNode({ description: e.target.value })}
                placeholder="Optional node description..."
                style={{ width: "100%", background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-primary)", color: "white", padding: "6px", borderRadius: "4px", fontSize: "11px", minHeight: "40px", resize: "vertical", outline: "none" }}
              />
            </div>
            
            <button
              onClick={() => {
                updateActiveWorkflow((wf) => ({
                  ...wf,
                  nodes: wf.nodes.filter((n) => n.id !== selectedNode.id),
                  edges: wf.edges.filter((e) => e.from !== selectedNode.id && e.to !== selectedNode.id),
                }));
                setSelectedNodeId(null);
              }}
              style={{ padding: "8px", borderRadius: "6px", background: "rgba(239,68,68,0.15)", color: "#f87171", border: "1px solid rgba(239,68,68,0.4)", cursor: "pointer", fontSize: "12px", fontWeight: 600, marginTop: "10px" }}
            >
              Delete Node
            </button>
          </div>
        )}
        {selectedEdge && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ padding: "10px", borderRadius: "9px", border: "1px solid var(--border-primary)", background: "rgba(255,255,255,0.03)", fontSize: "12px" }}>
              <div style={{ color: "var(--text-muted)", marginBottom: "6px" }}>Edge ID</div>
              <div style={{ color: "#cbd5e1", fontFamily: "var(--font-mono)" }}>{selectedEdge.id}</div>
            </div>
            <button
              onClick={() => {
                updateActiveWorkflow((wf) => ({ ...wf, edges: wf.edges.filter((e) => e.id !== selectedEdge.id) }));
                setSelectedEdgeId(null);
              }}
              style={{ padding: "8px", borderRadius: "6px", background: "rgba(239,68,68,0.15)", color: "#f87171", border: "1px solid rgba(239,68,68,0.4)", cursor: "pointer", fontSize: "12px", fontWeight: 600, marginTop: "10px" }}
            >
              Delete Edge
            </button>
          </div>
        )}
      </aside>

      {editingToolsNodeId && (
        <ToolSelectionModal
          initialTools={activeWorkflow?.nodes.find(n => n.id === editingToolsNodeId)?.tools || []}
          onSave={(tools) => {
            updateNodeById(editingToolsNodeId, n => ({ ...n, tools }));
            setEditingToolsNodeId(null);
          }}
          onCancel={() => setEditingToolsNodeId(null)}
        />
      )}

      {editingMemoryNodeId && (
        <MemoryConfigModal
          initialConfig={activeWorkflow?.nodes.find(n => n.id === editingMemoryNodeId)?.memoryConfig}
          onSave={(memoryConfig) => {
            updateNodeById(editingMemoryNodeId, n => ({ ...n, memoryConfig }));
            setEditingMemoryNodeId(null);
          }}
          onCancel={() => setEditingMemoryNodeId(null)}
        />
      )}

      {editingConnectorsNodeId && (
        <ConnectorConfigModal
          initialConnectors={activeWorkflow?.nodes.find(n => n.id === editingConnectorsNodeId)?.connectedConnectors || []}
          availableConnectors={connectors}
          onSave={(connectedConnectors) => {
            updateNodeById(editingConnectorsNodeId, n => ({ ...n, connectedConnectors }));
            setEditingConnectorsNodeId(null);
          }}
          onCancel={() => setEditingConnectorsNodeId(null)}
        />
      )}
    </div>
  );
}