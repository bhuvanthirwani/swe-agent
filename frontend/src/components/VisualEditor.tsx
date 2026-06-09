import React, { useMemo, useRef, useState, useEffect } from "react";
import {
  DAGNodeType,
  DAGWorkflow,
  DAGNode,
  DAGEdge,
} from "@/lib/flows/dagExecutor";
import { AGENT_CONFIGS, AgentName } from "@/lib/types";
import { fetchConnectors, Connector } from "@/lib/connectors";

interface VisualEditorProps {
  onRunWorkflow: (workflowId: string) => void;
}

const NODE_WIDTH = 230;
const NODE_HEIGHT = 96;

export default function VisualEditor({ onRunWorkflow }: VisualEditorProps) {
  const [workflows, setWorkflows] = useState<DAGWorkflow[]>([]);
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);

  const [edgeSource, setEdgeSource] = useState<string | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [activeMenu, setActiveMenu] = useState<{
    nodeId: string;
    handleType: string;
  } | null>(null);

  useEffect(() => {
    fetchConnectors().then(setConnectors).catch(console.error);
    fetch("/api/workflows")
      .then((res) => res.json())
      .then((data: DAGWorkflow[]) => {
        setWorkflows(data);
        if (data.length > 0 && !activeWorkflowId) {
          setActiveWorkflowId(data[0].id);
        }
      })
      .catch(console.error);
  }, [activeWorkflowId]);

  const activeWorkflow = useMemo(
    () => workflows.find((w) => w.id === activeWorkflowId) ?? null,
    [workflows, activeWorkflowId],
  );
  const selectedNode =
    activeWorkflow?.nodes.find((n) => n.id === selectedNodeId) ?? null;
  const selectedEdge =
    activeWorkflow?.edges.find((e) => e.id === selectedEdgeId) ?? null;

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
        setWorkflows([saved, ...workflows]);
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
      id: `n-${Date.now()}`,
      type,
      label: `New ${type}`,
      x: 300,
      y: 300,
    };
    setWorkflows((prev) =>
      prev.map((wf) =>
        wf.id === activeWorkflowId
          ? { ...wf, nodes: [...wf.nodes, newNode] }
          : wf,
      ),
    );
    setSelectedNodeId(newNode.id);
  };

  const handleNodeClick = (nodeId: string) => {
    if (edgeSource) {
      if (edgeSource !== nodeId) {
        // Create Edge
        const newEdge: DAGEdge = {
          id: `e-${Date.now()}`,
          from: edgeSource,
          to: nodeId,
        };
        setWorkflows((prev) =>
          prev.map((wf) =>
            wf.id === activeWorkflowId
              ? { ...wf, edges: [...wf.edges, newEdge] }
              : wf,
          ),
        );
      }
      setEdgeSource(null);
    } else {
      setSelectedNodeId(nodeId);
    }
  };

  const handleNodeMouseDown = (
    e: React.MouseEvent<HTMLDivElement>,
    nodeId: string,
  ) => {
    if (!activeWorkflow) return;
    if (edgeSource) return; // Prevent drag while drawing edge
    e.preventDefault();
    e.stopPropagation();
    setSelectedNodeId(nodeId);
    const rect = e.currentTarget.getBoundingClientRect();
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setIsDragging(true);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button === 0 && !e.shiftKey) {
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setActiveMenu(null);
    }
    if (
      e.button === 1 ||
      e.shiftKey ||
      e.target === canvasRef.current ||
      (e.target as HTMLElement).id === "canvas-inner"
    ) {
      setIsPanning(true);
      setDragOffset({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleUpdateNodeConfig = (
    nodeId: string,
    field: "chatModel" | "memory" | "tools",
    value: string,
  ) => {
    setWorkflows((prev) =>
      prev.map((wf) => {
        if (wf.id !== activeWorkflowId) return wf;
        return {
          ...wf,
          nodes: wf.nodes.map((n) => {
            if (n.id !== nodeId) return n;

            if (field === "tools") {
              const currentTools = n.tools || [];
              if (currentTools.includes(value)) return n; // Prevent duplicates
              return { ...n, tools: [...currentTools, value] };
            } else {
              return { ...n, [field]: value };
            }
          }),
        };
      }),
    );
    setActiveMenu(null);
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isPanning) {
      setPan({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y,
      });
      return;
    }

    if (!isDragging || !selectedNodeId || !activeWorkflow || !canvasRef.current)
      return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - dragOffset.x - pan.x) / zoom;
    const y = (e.clientY - rect.top - dragOffset.y - pan.y) / zoom;
    setWorkflows((prev) =>
      prev.map((wf) =>
        wf.id !== activeWorkflowId
          ? wf
          : {
              ...wf,
              nodes: wf.nodes.map((n) =>
                n.id === selectedNodeId ? { ...n, x, y } : n,
              ),
            },
      ),
    );
  };

  const stopDragging = () => {
    setIsDragging(false);
    setIsPanning(false);
  };

  const updateSelectedNode = (updates: Partial<DAGNode>) => {
    setWorkflows((prev) =>
      prev.map((wf) =>
        wf.id === activeWorkflowId
          ? {
              ...wf,
              nodes: wf.nodes.map((n) =>
                n.id === selectedNodeId ? { ...n, ...updates } : n,
              ),
            }
          : wf,
      ),
    );
  };

  const updateSelectedEdge = (updates: Partial<DAGEdge>) => {
    setWorkflows((prev) =>
      prev.map((wf) =>
        wf.id === activeWorkflowId
          ? {
              ...wf,
              edges: wf.edges.map((e) =>
                e.id === selectedEdgeId ? { ...e, ...updates } : e,
              ),
            }
          : wf,
      ),
    );
  };

  const getNodeColor = (type: DAGNodeType, agentName?: AgentName) => {
    if (type === "agent" && agentName)
      return AGENT_CONFIGS[agentName]?.color ?? "#6366f1";
    if (type === "condition") return "#f59e0b";
    if (type === "parallel") return "#06b6d4";
    if (type === "human_checkpoint") return "#ec4899";
    if (type === "merge") return "#10b981";
    if (type === "trigger") return "#84cc16";
    if (type === "action") return "#d946ef";
    return "#6366f1";
  };

  const getNodeIcon = (type: DAGNodeType, agentName?: AgentName) => {
    if (type === "agent" && agentName)
      return AGENT_CONFIGS[agentName]?.icon ?? "⚙️";
    if (type === "condition") return "🔀";
    if (type === "parallel") return "⚡";
    if (type === "human_checkpoint") return "👤";
    if (type === "merge") return "✅";
    if (type === "trigger") return "🔌";
    if (type === "action") return "🚀";
    return "⚙️";
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
          <marker
            id="ve-arrow"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255,255,255,0.35)" />
          </marker>
          <marker
            id="ve-arrow-selected"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#6366f1" />
          </marker>
        </defs>
        {activeWorkflow.edges.map((edge) => {
          const fromNode = activeWorkflow.nodes.find((n) => n.id === edge.from);
          const toNode = activeWorkflow.nodes.find((n) => n.id === edge.to);
          if (!fromNode || !toNode) return null;

          const startX = (fromNode.x + NODE_WIDTH + 6) * zoom;
          const startY = (fromNode.y + NODE_HEIGHT / 2) * zoom;
          const endX = (toNode.x - 6) * zoom;
          const endY = (toNode.y + NODE_HEIGHT / 2) * zoom;
          const midY = startY + (endY - startY) * 0.5;
          const path = `M ${startX} ${startY} C ${startX + 40 * zoom} ${startY}, ${endX - 40 * zoom} ${endY}, ${endX} ${endY}`;
          const isEdgeSelected = edge.id === selectedEdgeId;

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
              <path
                d={path}
                fill="none"
                stroke="transparent"
                strokeWidth={20}
              />
              <path
                d={path}
                fill="none"
                stroke={isEdgeSelected ? "#6366f1" : "rgba(148,163,184,0.45)"}
                strokeWidth={isEdgeSelected ? 3 : 2}
                markerEnd={
                  isEdgeSelected ? "url(#ve-arrow-selected)" : "url(#ve-arrow)"
                }
              />
              <circle
                cx={endX}
                cy={endY}
                r={4 * zoom}
                fill={isEdgeSelected ? "#6366f1" : "#94a3b8"}
              />
              {(edge.label || edge.description) && (
                <text
                  x={(startX + endX) / 2}
                  y={midY - 6}
                  fill={isEdgeSelected ? "#c7d2fe" : "#a5b4fc"}
                  fontSize="10"
                  textAnchor="middle"
                >
                  {edge.label && (
                    <tspan
                      x={(startX + endX) / 2}
                      dy="-0.2em"
                      fontWeight={isEdgeSelected ? "bold" : "normal"}
                    >
                      {edge.label}
                    </tspan>
                  )}
                  {edge.description && (
                    <tspan
                      x={(startX + endX) / 2}
                      dy="1.4em"
                      fill="#9ca3af"
                      fontSize="9"
                    >
                      {edge.description.length > 30
                        ? edge.description.substring(0, 30) + "..."
                        : edge.description}
                    </tspan>
                  )}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "280px 1fr 320px",
        height: "100%",
      }}
    >
      <aside
        style={{
          borderRight: "1px solid var(--border-primary)",
          background: "rgba(10,14,24,0.9)",
          padding: "14px",
          overflowY: "auto",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "10px",
          }}
        >
          <div
            style={{
              fontSize: "11px",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
            }}
          >
            Workflow Catalog
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
                  border: active
                    ? "1px solid rgba(99,102,241,0.5)"
                    : "1px solid var(--border-primary)",
                  background: active
                    ? "rgba(99,102,241,0.15)"
                    : "rgba(255,255,255,0.03)",
                  color: active ? "#c7d2fe" : "var(--text-secondary)",
                  cursor: "pointer",
                }}
              >
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: "13px",
                    color: active ? "#e0e7ff" : "#d1d5db",
                  }}
                >
                  {wf.name}
                </div>
                <div
                  style={{ fontSize: "11px", marginTop: "4px", opacity: 0.8 }}
                >
                  {wf.description}
                </div>
              </button>
            );
          })}
        </div>

        <div
          style={{
            marginTop: "20px",
            paddingTop: "14px",
            borderTop: "1px solid var(--border-primary)",
          }}
        >
          <div
            style={{
              fontSize: "11px",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
              marginBottom: "10px",
            }}
          >
            Node Palette (Drag & Drop)
          </div>
          {[
            "trigger",
            "agent",
            "condition",
            "parallel",
            "action",
            "human_checkpoint",
            "merge",
          ].map((type) => (
            <button
              key={type}
              onClick={() => handleAddNode(type as DAGNodeType)}
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
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "999px",
                  background: getNodeColor(type as DAGNodeType),
                }}
              />
              <span>+ Add {type.replace("_", " ")}</span>
            </button>
          ))}
        </div>
      </aside>

      <section
        style={{ display: "flex", flexDirection: "column", minWidth: 0 }}
      >
        <div
          style={{
            padding: "12px 16px",
            borderBottom: "1px solid var(--border-primary)",
            background: "rgba(9,12,20,0.9)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div
              style={{ fontSize: "15px", fontWeight: 700, color: "#e5e7eb" }}
            >
              {activeWorkflow?.name || "Loading..."}
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                marginTop: "2px",
              }}
            >
              Interactive Workflow Builder
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={() =>
                setZoom((z) => Math.max(0.6, Number((z - 0.1).toFixed(2))))
              }
              style={{
                padding: "6px 10px",
                borderRadius: "8px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.04)",
                color: "#d1d5db",
                cursor: "pointer",
              }}
            >
              -
            </button>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "#94a3b8",
                minWidth: "52px",
                textAlign: "center",
              }}
            >
              {Math.round(zoom * 100)}%
            </div>
            <button
              onClick={() =>
                setZoom((z) => Math.min(1.8, Number((z + 0.1).toFixed(2))))
              }
              style={{
                padding: "6px 10px",
                borderRadius: "8px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.04)",
                color: "#d1d5db",
                cursor: "pointer",
              }}
            >
              +
            </button>

            <button
              onClick={handleSaveWorkflow}
              style={{
                marginLeft: "6px",
                padding: "8px 14px",
                borderRadius: "9px",
                border: "1px solid rgba(16,185,129,0.4)",
                background: "rgba(16,185,129,0.1)",
                color: "#34d399",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Save Workflow
            </button>

            <button
              onClick={() => activeWorkflow && onRunWorkflow(activeWorkflow.id)}
              style={{
                marginLeft: "6px",
                padding: "8px 14px",
                borderRadius: "9px",
                border: "1px solid rgba(16,185,129,0.4)",
                background:
                  "linear-gradient(135deg, rgba(16,185,129,0.35), rgba(5,150,105,0.22))",
                color: "#ecfdf5",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Run Workflow
            </button>
          </div>
        </div>

        <div
          ref={canvasRef}
          onClick={() => {
            setSelectedNodeId(null);
            setSelectedEdgeId(null);
            if (edgeSource) setEdgeSource(null);
          }}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={stopDragging}
          onMouseLeave={stopDragging}
          onMouseDown={handleCanvasMouseDown}
          style={{
            position: "relative",
            flex: 1,
            overflow: "hidden",
            backgroundColor: "#070b14",
            backgroundImage:
              "linear-gradient(rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.08) 1px, transparent 1px)",
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
            backgroundPosition: `${pan.x}px ${pan.y}px`,
            cursor: isPanning ? "grabbing" : "grab",
          }}
        >
          <div
            id="canvas-inner"
            style={{
              position: "absolute",
              inset: 0,
              transform: `translate(${pan.x}px, ${pan.y}px)`,
            }}
          >
            {renderEdges()}
            {activeWorkflow?.nodes.map((node) => {
              const isSelected = node.id === selectedNodeId;
              const isEdgeSource = node.id === edgeSource;
              const nodeColor = getNodeColor(node.type, node.agentName);
              const nodeIcon = getNodeIcon(node.type, node.agentName);

              const isConnector =
                node.type === "trigger" || node.type === "action";
              const isCondition = node.type === "condition";

              let clipPath = "none";
              let borderRadius = 12 * zoom;
              let customPadding = `${10 * zoom}px ${12 * zoom}px`;
              let customFlexDirection: "row" | "column" = "row";
              let heightStr = "auto";

              if (isConnector) {
                clipPath = "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)";
                borderRadius = 0;
                customPadding = `${25 * zoom}px ${45 * zoom}px`;
                customFlexDirection = "column";
                heightStr = `${NODE_WIDTH * zoom}px`; // Make it a perfect square bounding box so it becomes a perfect diamond
              } else if (isCondition) {
                clipPath =
                  "polygon(15% 0, 85% 0, 100% 50%, 85% 100%, 15% 100%, 0 50%)";
                borderRadius = 0;
                customPadding = `${15 * zoom}px ${35 * zoom}px`;
              }

              // We rely on drop-shadow instead of box-shadow because clip-path hides box-shadow
              const shadowFilter = isSelected
                ? `drop-shadow(0 0 8px ${nodeColor})`
                : "drop-shadow(0 10px 15px rgba(2,6,23,0.45))";
              const borderStyle =
                isConnector || isCondition
                  ? "none"
                  : `1px solid ${isSelected ? nodeColor : isEdgeSource ? "#f59e0b" : "rgba(148,163,184,0.28)"}`;

              return (
                <div
                  key={node.id}
                  style={{
                    position: "absolute",
                    left: node.x * zoom,
                    top: node.y * zoom,
                  }}
                >
                  {/* The Main Node Container */}
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      handleNodeClick(node.id);
                      setSelectedEdgeId(null);
                      setActiveMenu(null);
                    }}
                    onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                    style={{
                      position: "relative",
                      width: NODE_WIDTH * zoom,
                      minHeight: isConnector ? heightStr : NODE_HEIGHT * zoom,
                      height: isConnector ? heightStr : "auto",
                      borderRadius,
                      clipPath,
                      border: borderStyle,
                      background:
                        isSelected && (isConnector || isCondition)
                          ? `linear-gradient(135deg, ${nodeColor}22, rgba(9,14,28,0.98))`
                          : "linear-gradient(135deg, rgba(15,23,42,0.96), rgba(9,14,28,0.98))",
                      filter: shadowFilter,
                      boxShadow:
                        isConnector || isCondition
                          ? "none"
                          : isSelected
                            ? `0 0 0 1px ${nodeColor}, 0 18px 38px rgba(2,6,23,0.65)`
                            : "none",
                      zIndex: isSelected ? 20 : 10,
                      cursor:
                        isDragging && isSelected
                          ? "grabbing"
                          : edgeSource
                            ? "crosshair"
                            : "pointer",
                      userSelect: "none",
                      overflow: "visible",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "center",
                    }}
                  >
                    {!(isConnector || isCondition) && (
                      <div
                        style={{
                          height: "4px",
                          background: nodeColor,
                          opacity: 0.9,
                          flexShrink: 0,
                        }}
                      />
                    )}
                    <div
                      style={{
                        padding: customPadding,
                        display: "flex",
                        flexDirection: customFlexDirection,
                        alignItems: "center",
                        justifyContent: "center",
                        gap: `${10 * zoom}px`,
                        flex: 1,
                      }}
                    >
                      <div
                        style={{
                          width: `${30 * zoom}px`,
                          height: `${30 * zoom}px`,
                          borderRadius: `${8 * zoom}px`,
                          background: `${nodeColor}24`,
                          color: nodeColor,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: `${16 * zoom}px`,
                          flexShrink: 0,
                        }}
                      >
                        {nodeIcon}
                      </div>
                      <div
                        style={{
                          minWidth: 0,
                          textAlign:
                            customFlexDirection === "column"
                              ? "center"
                              : "left",
                        }}
                      >
                        <div
                          style={{
                            fontSize: `${12 * zoom}px`,
                            fontWeight: 700,
                            color: "#e2e8f0",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {node.label}
                        </div>
                        <div
                          style={{
                            fontSize: `${10 * zoom}px`,
                            color: "#94a3b8",
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                          }}
                        >
                          {node.type}
                        </div>
                      </div>
                    </div>
                    {!(isConnector || isCondition) && (
                      <div
                        style={{
                          padding: `0 ${12 * zoom}px ${10 * zoom}px`,
                          fontSize: `${10 * zoom}px`,
                          color: "#a5b4fc",
                          fontFamily: "var(--font-mono)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {node.agentName || node.connectorId || node.id}
                      </div>
                    )}

                    {/* Left Edge: Input Connection */}
                    {!(isConnector && node.type === "trigger") && (
                      <div
                        style={{
                          position: "absolute",
                          left: -6 * zoom,
                          top: "50%",
                          transform: "translateY(-50%)",
                          width: 12 * zoom,
                          height: 12 * zoom,
                          borderRadius: "50%",
                          background: "#94a3b8",
                          border: "2px solid #0f172a",
                          cursor: "crosshair",
                          zIndex: 25,
                        }}
                      />
                    )}

                    {/* Right Edge: Output Connection */}
                    <div
                      style={{
                        position: "absolute",
                        right: -6 * zoom,
                        top: "50%",
                        transform: "translateY(-50%)",
                        width: 12 * zoom,
                        height: 12 * zoom,
                        borderRadius: "50%",
                        background: "#94a3b8",
                        border: "2px solid #0f172a",
                        cursor: "crosshair",
                        zIndex: 25,
                      }}
                    />
                  </div>

                  {/* Bottom Extension Handles (Chat Model, Memory, Tool) */}
                  {node.type === "agent" && (
                    <div
                      style={{
                        position: "absolute",
                        width: "100%",
                        bottom: -40 * zoom,
                        display: "flex",
                        justifyContent: "space-evenly",
                        zIndex: 15,
                      }}
                    >
                      {(["Chat Model", "Memory", "Tool"] as const).map(
                        (handleType) => {
                          let boxColor = "#6366f1";
                          let isConfigured = false;
                          let count = 0;

                          if (handleType === "Chat Model" && node.chatModel) {
                            isConfigured = true;
                          }
                          if (handleType === "Memory" && node.memory) {
                            isConfigured = true;
                            boxColor = "#f59e0b";
                          }
                          if (handleType === "Tool") {
                            boxColor = "#10b981";
                            count = node.tools?.length || 0;
                            isConfigured = count > 0;
                          }

                          return (
                            <div
                              key={handleType}
                              style={{
                                position: "relative",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                              }}
                            >
                              {/* The line popping out the bottom */}
                              <div
                                style={{
                                  width: 2 * zoom,
                                  height: 16 * zoom,
                                  background: "rgba(148,163,184,0.28)",
                                }}
                              />

                              {/* The Handle Box */}
                              <div
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenu(
                                    activeMenu?.nodeId === node.id &&
                                      activeMenu.handleType === handleType
                                      ? null
                                      : { nodeId: node.id, handleType },
                                  );
                                }}
                                style={{
                                  width: 22 * zoom,
                                  height: 22 * zoom,
                                  borderRadius: 4 * zoom,
                                  background: "rgba(15,23,42,0.9)",
                                  border: `1px solid ${boxColor}`,
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  cursor: "pointer",
                                  color: boxColor,
                                  fontSize: 14 * zoom,
                                  boxShadow: `0 0 8px ${boxColor}44`,
                                  transition: "transform 0.1s",
                                }}
                              >
                                {isConfigured
                                  ? handleType === "Tool"
                                    ? count
                                    : "✓"
                                  : "+"}
                              </div>
                              {/* Label */}
                              <span
                                style={{
                                  fontSize: 9 * zoom,
                                  color: "#94a3b8",
                                  marginTop: 4 * zoom,
                                  fontWeight: 500,
                                }}
                              >
                                {handleType}
                              </span>

                              {/* Pop-up menu when this handle is clicked */}
                              {activeMenu?.nodeId === node.id &&
                                activeMenu?.handleType === handleType && (
                                  <div
                                    style={{
                                      position: "absolute",
                                      top: 45 * zoom,
                                      background: "#1e293b",
                                      border: "1px solid #334155",
                                      borderRadius: 8 * zoom,
                                      padding: 8 * zoom,
                                      width: 140 * zoom,
                                      zIndex: 50,
                                      display: "flex",
                                      flexDirection: "column",
                                      gap: 6 * zoom,
                                      boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
                                    }}
                                  >
                                    <div
                                      style={{
                                        fontSize: 10 * zoom,
                                        color: "#cbd5e1",
                                        fontWeight: "bold",
                                        marginBottom: 4 * zoom,
                                      }}
                                    >
                                      Select {handleType}
                                    </div>

                                    {handleType === "Tool" &&
                                      ["searchWeb", "readFile", "lintCode"].map(
                                        (tool) => (
                                          <button
                                            key={tool}
                                            onClick={() =>
                                              handleUpdateNodeConfig(
                                                node.id,
                                                "tools",
                                                tool,
                                              )
                                            }
                                            style={{
                                              textAlign: "left",
                                              padding: "4px 8px",
                                              background: node.tools?.includes(
                                                tool,
                                              )
                                                ? "#10b98133"
                                                : "transparent",
                                              color: "#f8fafc",
                                              border: "none",
                                              borderRadius: 4,
                                              cursor: "pointer",
                                              fontSize: 11 * zoom,
                                            }}
                                          >
                                            {tool}{" "}
                                            {node.tools?.includes(tool) && "✓"}
                                          </button>
                                        ),
                                      )}

                                    {handleType === "Chat Model" &&
                                      [
                                        "llama-3.3-70b",
                                        "gpt-4o-mini",
                                        "claude-3-haiku",
                                      ].map((model) => (
                                        <button
                                          key={model}
                                          onClick={() =>
                                            handleUpdateNodeConfig(
                                              node.id,
                                              "chatModel",
                                              model,
                                            )
                                          }
                                          style={{
                                            textAlign: "left",
                                            padding: "4px 8px",
                                            background:
                                              node.chatModel === model
                                                ? "#6366f133"
                                                : "transparent",
                                            color: "#f8fafc",
                                            border: "none",
                                            borderRadius: 4,
                                            cursor: "pointer",
                                            fontSize: 11 * zoom,
                                          }}
                                        >
                                          {model}
                                        </button>
                                      ))}

                                    {handleType === "Memory" &&
                                      [
                                        "Buffer Memory",
                                        "Summary Memory",
                                        "Vector Store",
                                      ].map((mem) => (
                                        <button
                                          key={mem}
                                          onClick={() =>
                                            handleUpdateNodeConfig(
                                              node.id,
                                              "memory",
                                              mem,
                                            )
                                          }
                                          style={{
                                            textAlign: "left",
                                            padding: "4px 8px",
                                            background:
                                              node.memory === mem
                                                ? "#f59e0b33"
                                                : "transparent",
                                            color: "#f8fafc",
                                            border: "none",
                                            borderRadius: 4,
                                            cursor: "pointer",
                                            fontSize: 11 * zoom,
                                          }}
                                        >
                                          {mem}
                                        </button>
                                      ))}
                                  </div>
                                )}
                            </div>
                          );
                        },
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <aside
        style={{
          borderLeft: "1px solid var(--border-primary)",
          background: "rgba(10,14,24,0.9)",
          padding: "14px",
          overflowY: "auto",
        }}
      >
        <div
          style={{
            fontSize: "11px",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text-muted)",
            marginBottom: "8px",
          }}
        >
          {selectedNode
            ? "Node Inspector"
            : selectedEdge
              ? "Edge Inspector"
              : "Workflow Config"}
        </div>
        {!selectedNode && !selectedEdge && activeWorkflow && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            <div
              style={{
                padding: "10px",
                borderRadius: "9px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.03)",
              }}
            >
              <div
                style={{
                  color: "var(--text-muted)",
                  fontSize: "12px",
                  marginBottom: "6px",
                }}
              >
                Workflow Name
              </div>
              <input
                type="text"
                value={activeWorkflow.name}
                onChange={(e) =>
                  setWorkflows((prev) =>
                    prev.map((w) =>
                      w.id === activeWorkflow.id
                        ? { ...w, name: e.target.value }
                        : w,
                    ),
                  )
                }
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border-primary)",
                  color: "white",
                  padding: "8px",
                  borderRadius: "4px",
                  outline: "none",
                  fontSize: "12px",
                }}
              />
            </div>

            <div
              style={{
                padding: "10px",
                borderRadius: "9px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.03)",
              }}
            >
              <div
                style={{
                  color: "var(--text-muted)",
                  fontSize: "12px",
                  marginBottom: "6px",
                }}
              >
                Cron Schedule (e.g. */5 * * * *)
              </div>
              <input
                type="text"
                placeholder="Leave blank for manual trigger only"
                value={activeWorkflow.cron_schedule || ""}
                onChange={(e) =>
                  setWorkflows((prev) =>
                    prev.map((w) =>
                      w.id === activeWorkflow.id
                        ? { ...w, cron_schedule: e.target.value }
                        : w,
                    ),
                  )
                }
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border-primary)",
                  color: "white",
                  padding: "8px",
                  borderRadius: "4px",
                  outline: "none",
                  fontSize: "12px",
                }}
              />
              <div
                style={{
                  color: "var(--text-muted)",
                  fontSize: "10px",
                  marginTop: "6px",
                  lineHeight: 1.4,
                }}
              >
                A standard Cron string. Examples:
                <br />
                <b>*/5 * * * *</b> (Every 5 mins)
                <br />
                <b>0 * * * *</b> (Hourly)
              </div>
            </div>

            <div
              style={{
                padding: "10px",
                borderRadius: "9px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.03)",
              }}
            >
              <div
                style={{
                  color: "var(--text-muted)",
                  fontSize: "12px",
                  marginBottom: "6px",
                }}
              >
                Description
              </div>
              <textarea
                value={activeWorkflow.description || ""}
                onChange={(e) =>
                  setWorkflows((prev) =>
                    prev.map((w) =>
                      w.id === activeWorkflow.id
                        ? { ...w, description: e.target.value }
                        : w,
                    ),
                  )
                }
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border-primary)",
                  color: "white",
                  padding: "8px",
                  borderRadius: "4px",
                  outline: "none",
                  fontSize: "12px",
                  minHeight: "60px",
                  resize: "vertical",
                }}
              />
            </div>
          </div>
        )}
        {selectedNode && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            <div
              style={{
                padding: "12px",
                borderRadius: "10px",
                border: "1px solid rgba(99,102,241,0.3)",
                background: "rgba(99,102,241,0.1)",
              }}
            >
              <input
                type="text"
                value={selectedNode.label}
                onChange={(e) => updateSelectedNode({ label: e.target.value })}
                style={{
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  color: "#e0e7ff",
                  fontWeight: 700,
                  fontSize: "13px",
                  outline: "none",
                }}
              />
              <div
                style={{ color: "#a5b4fc", fontSize: "11px", marginTop: "4px" }}
              >
                {selectedNode.type}
              </div>
            </div>

            <div
              style={{
                padding: "10px",
                borderRadius: "9px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.03)",
                fontSize: "12px",
              }}
            >
              <div style={{ color: "var(--text-muted)", marginBottom: "6px" }}>
                Node ID
              </div>
              <div style={{ color: "#cbd5e1", fontFamily: "var(--font-mono)" }}>
                {selectedNode.id}
              </div>
            </div>

            {selectedNode.type === "agent" && (
              <div
                style={{
                  padding: "10px",
                  borderRadius: "9px",
                  border: "1px solid var(--border-primary)",
                  background: "rgba(255,255,255,0.03)",
                  fontSize: "12px",
                }}
              >
                <div
                  style={{ color: "var(--text-muted)", marginBottom: "6px" }}
                >
                  Bound Agent
                </div>
                <select
                  value={selectedNode.agentName || ""}
                  onChange={(e) =>
                    updateSelectedNode({
                      agentName: e.target.value as AgentName,
                    })
                  }
                  style={{
                    width: "100%",
                    background: "rgba(0,0,0,0.2)",
                    border: "1px solid var(--border-primary)",
                    color: "white",
                    padding: "6px",
                    borderRadius: "4px",
                  }}
                >
                  <option value="">-- Select Agent --</option>
                  {Object.keys(AGENT_CONFIGS).map((agent) => (
                    <option key={agent} value={agent}>
                      {agent}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {(selectedNode.type === "trigger" ||
              selectedNode.type === "action") && (
              <div
                style={{
                  padding: "10px",
                  borderRadius: "9px",
                  border: "1px solid var(--border-primary)",
                  background: "rgba(255,255,255,0.03)",
                  fontSize: "12px",
                }}
              >
                <div
                  style={{ color: "var(--text-muted)", marginBottom: "6px" }}
                >
                  Connector
                </div>
                <select
                  value={selectedNode.connectorId || ""}
                  onChange={(e) =>
                    updateSelectedNode({ connectorId: e.target.value })
                  }
                  style={{
                    width: "100%",
                    background: "rgba(0,0,0,0.2)",
                    border: "1px solid var(--border-primary)",
                    color: "white",
                    padding: "6px",
                    borderRadius: "4px",
                  }}
                >
                  <option value="">-- Select Connector --</option>
                  {connectors.map((conn) => (
                    <option key={conn.id} value={conn.id}>
                      {conn.icon} {conn.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={() => setEdgeSource(selectedNode.id)}
              style={{
                padding: "8px",
                borderRadius: "6px",
                background: "rgba(245,158,11,0.15)",
                color: "#fbbf24",
                border: "1px solid rgba(245,158,11,0.4)",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              {edgeSource === selectedNode.id
                ? "Click target node..."
                : "+ Add Outgoing Edge"}
            </button>

            <button
              onClick={() => {
                setSelectedNodeId(null);
                setSelectedEdgeId(null);
                setWorkflows((prev) =>
                  prev.map((wf) =>
                    wf.id === activeWorkflowId
                      ? {
                          ...wf,
                          nodes: wf.nodes.filter(
                            (n) => n.id !== selectedNode.id,
                          ),
                          edges: wf.edges.filter(
                            (e) =>
                              e.from !== selectedNode.id &&
                              e.to !== selectedNode.id,
                          ),
                        }
                      : wf,
                  ),
                );
              }}
              style={{
                padding: "8px",
                borderRadius: "6px",
                background: "rgba(239,68,68,0.15)",
                color: "#f87171",
                border: "1px solid rgba(239,68,68,0.4)",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: 600,
                marginTop: "10px",
              }}
            >
              Delete Node
            </button>
          </div>
        )}

        {selectedEdge && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            <div
              style={{
                padding: "10px",
                borderRadius: "9px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.03)",
                fontSize: "12px",
              }}
            >
              <div style={{ color: "var(--text-muted)", marginBottom: "6px" }}>
                Edge ID
              </div>
              <div style={{ color: "#cbd5e1", fontFamily: "var(--font-mono)" }}>
                {selectedEdge.id}
              </div>
              <div
                style={{
                  color: "var(--text-muted)",
                  marginTop: "8px",
                  marginBottom: "6px",
                }}
              >
                Transition
              </div>
              <div style={{ color: "#a5b4fc", fontSize: "11px" }}>
                {activeWorkflow?.nodes.find((n) => n.id === selectedEdge.from)
                  ?.label || selectedEdge.from}
                <span style={{ margin: "0 5px" }}>→</span>
                {activeWorkflow?.nodes.find((n) => n.id === selectedEdge.to)
                  ?.label || selectedEdge.to}
              </div>
            </div>

            <div
              style={{
                padding: "10px",
                borderRadius: "9px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.03)",
              }}
            >
              <div
                style={{
                  color: "var(--text-muted)",
                  fontSize: "12px",
                  marginBottom: "6px",
                }}
              >
                Label (Short)
              </div>
              <input
                type="text"
                placeholder="e.g. Approved"
                value={selectedEdge.label || ""}
                onChange={(e) => updateSelectedEdge({ label: e.target.value })}
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border-primary)",
                  color: "white",
                  padding: "8px",
                  borderRadius: "4px",
                  outline: "none",
                  fontSize: "12px",
                }}
              />
            </div>

            <div
              style={{
                padding: "10px",
                borderRadius: "9px",
                border: "1px solid var(--border-primary)",
                background: "rgba(255,255,255,0.03)",
              }}
            >
              <div
                style={{
                  color: "var(--text-muted)",
                  fontSize: "12px",
                  marginBottom: "6px",
                }}
              >
                Description (Instructions)
              </div>
              <textarea
                placeholder="Detailed context for the target node..."
                value={selectedEdge.description || ""}
                onChange={(e) =>
                  updateSelectedEdge({ description: e.target.value })
                }
                style={{
                  width: "100%",
                  background: "rgba(0,0,0,0.2)",
                  border: "1px solid var(--border-primary)",
                  color: "white",
                  padding: "8px",
                  borderRadius: "4px",
                  outline: "none",
                  fontSize: "12px",
                  minHeight: "100px",
                  resize: "vertical",
                }}
              />
            </div>

            <button
              onClick={() => {
                setWorkflows((prev) =>
                  prev.map((wf) =>
                    wf.id === activeWorkflowId
                      ? {
                          ...wf,
                          edges: wf.edges.filter(
                            (e) => e.id !== selectedEdge.id,
                          ),
                        }
                      : wf,
                  ),
                );
                setSelectedEdgeId(null);
              }}
              style={{
                padding: "8px",
                borderRadius: "6px",
                background: "rgba(239,68,68,0.15)",
                color: "#f87171",
                border: "1px solid rgba(239,68,68,0.4)",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: 600,
                marginTop: "10px",
              }}
            >
              Delete Edge
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}
