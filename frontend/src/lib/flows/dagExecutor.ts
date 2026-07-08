// ============================================================
// DAG-Based Workflow Executor (Competitor Feature: Flexible Workflow Graphs)
// Supports branching, conditional routing, resource/context edges,
// and human checkpoints — similar to Microsoft Agent Framework.
// ============================================================

import { AgentName } from "@/lib/types";

// ─── DAG Node Types ──────────────────────────────────────────

export type DAGNodeType =
  | "agent"
  | "condition"
  | "parallel"
  | "human_checkpoint"
  | "merge"
  | "trigger"
  | "action"
  | "model"
  | "tool"
  | "rag"
  | "vector_store"
  | "buffer_memory"
  | "summary_memory"
  | "hippocampus_memory"
  | "guardrail"
  | "subworkflow";

export type DAGPortDirection = "input" | "output";

export type DAGPortKind =
  | "control"
  | "data"
  | "context"
  | "model"
  | "tool"
  | "memory"
  | "rag"
  | "vector"
  | "guardrail"
  | "connector"
  | "error";

export type DAGPortPosition = "left" | "right" | "top" | "bottom";

export type DAGEdgeType =
  | "control"
  | "data"
  | "context"
  | "model"
  | "tool"
  | "memory"
  | "rag"
  | "vector"
  | "vector_write"
  | "guardrail"
  | "connector"
  | "error";

export interface DAGPort {
  id: string;
  label: string;
  direction: DAGPortDirection;
  kind: DAGPortKind;
  position?: DAGPortPosition;
  accepts?: DAGPortKind[];
  required?: boolean;
  maxConnections?: number;
  description?: string;
}

export interface DAGNode {
  id: string;
  type: DAGNodeType;
  agentName?: AgentName;
  label: string;
  description?: string;
  // Position for visual editor
  x: number;
  y: number;
  // Custom dynamic ports beyond the default ports derived from node type
  ports?: DAGPort[];
  // Agent resource/configuration overrides
  chatModel?: string;
  memory?: string;
  memoryConfig?: string;
  tools?: string[];
  connectedConnectors?: string[];
  useCompaction?: boolean;
  compactionStrategy?:
    | "off"
    | "auto"
    | "aggressive"
    | "memory_first"
    | "rag_first";
  maxContextTokens?: number;
  // Component configuration stored as JSON in workflows.nodes_json
  config?: Record<string, unknown>;
  // Connector configuration
  connectorId?: string;
  // Condition node config
  condition?: {
    field: string; // e.g., 'review.decision'
    operator: "==" | "!=" | ">" | "<" | "contains";
    value: string;
    trueBranch: string; // target node id
    falseBranch: string; // target node id
  };
  // Parallel node config
  parallelBranches?: string[][]; // arrays of node IDs per branch
  // Human checkpoint config
  checkpointConfig?: {
    timeoutMs: number;
    autoApprove: boolean;
    instructions: string;
  };
}

export interface DAGEdge {
  id: string;
  from: string;
  to: string;
  sourceHandle?: string;
  targetHandle?: string;
  edgeType?: DAGEdgeType;
  label?: string;
  description?: string;
  condition?: string; // e.g., 'approved', 'rejected'
  mapping?: Record<string, string>;
}

export interface DAGWorkflow {
  id: string;
  name: string;
  description: string;
  version: string;
  cron_schedule?: string;
  nodes: DAGNode[];
  edges: DAGEdge[];
  entryNodeId: string;
  createdAt: string;
  updatedAt: string;
}

// ─── Execution State ─────────────────────────────────────────

export type NodeExecutionStatus =
  | "pending"
  | "running"
  | "complete"
  | "error"
  | "skipped"
  | "waiting";

export interface NodeExecution {
  nodeId: string;
  status: NodeExecutionStatus;
  startedAt?: number;
  completedAt?: number;
  output?: string;
  error?: string;
}

export interface DAGExecutionState {
  workflowId: string;
  runId: string;
  nodeExecutions: Record<string, NodeExecution>;
  currentNodes: string[]; // nodes currently executing (can be parallel)
  completedNodes: string[];
  isComplete: boolean;
  startedAt: number;
}

// ─── Graph Utilities ─────────────────────────────────────────

export const RESOURCE_EDGE_TYPES: DAGEdgeType[] = [
  "model",
  "tool",
  "memory",
  "rag",
  "vector",
  "guardrail",
  "connector",
];

export function isExecutionEdge(edge: DAGEdge): boolean {
  return (
    !edge.edgeType ||
    edge.edgeType === "control" ||
    edge.edgeType === "data" ||
    edge.edgeType === "error" ||
    edge.edgeType === "vector_write"
  );
}

/**
 * Topological sort of a DAG. Returns ordered node IDs.
 * Throws if a cycle is detected in execution edges.
 */
export function topologicalSort(nodes: DAGNode[], edges: DAGEdge[]): string[] {
  const adjacency: Record<string, string[]> = {};
  const inDegree: Record<string, number> = {};

  nodes.forEach((n) => {
    adjacency[n.id] = [];
    inDegree[n.id] = 0;
  });

  edges.filter(isExecutionEdge).forEach((e) => {
    if (adjacency[e.from]) {
      adjacency[e.from].push(e.to);
      inDegree[e.to] = (inDegree[e.to] || 0) + 1;
    }
  });

  const queue: string[] = [];
  Object.entries(inDegree).forEach(([id, deg]) => {
    if (deg === 0) queue.push(id);
  });

  const sorted: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    sorted.push(current);
    for (const neighbor of adjacency[current] || []) {
      inDegree[neighbor]--;
      if (inDegree[neighbor] === 0) queue.push(neighbor);
    }
  }

  if (sorted.length !== nodes.length) {
    throw new Error("Cycle detected in workflow execution DAG");
  }
  return sorted;
}

/**
 * Get the immediate successors of a node.
 */
export function getSuccessors(nodeId: string, edges: DAGEdge[]): string[] {
  return edges
    .filter((e) => e.from === nodeId && isExecutionEdge(e))
    .map((e) => e.to);
}

/**
 * Get the immediate predecessors of a node.
 */
export function getPredecessors(nodeId: string, edges: DAGEdge[]): string[] {
  return edges
    .filter((e) => e.to === nodeId && isExecutionEdge(e))
    .map((e) => e.from);
}

/**
 * Check if all execution predecessors are complete.
 */
export function allPredecessorsComplete(
  nodeId: string,
  edges: DAGEdge[],
  completedNodes: Set<string>,
): boolean {
  const preds = getPredecessors(nodeId, edges);
  return preds.every((p) => completedNodes.has(p));
}

/**
 * Get the next executable nodes given current state.
 */
export function getNextExecutableNodes(
  workflow: DAGWorkflow,
  completedNodes: Set<string>,
  runningNodes: Set<string>,
): string[] {
  return workflow.nodes
    .filter(
      (n) =>
        !completedNodes.has(n.id) &&
        !runningNodes.has(n.id) &&
        allPredecessorsComplete(n.id, workflow.edges, completedNodes),
    )
    .map((n) => n.id);
}

// ─── Built-in DAG Workflows moved to Database Backend ─────────────────────────────────
