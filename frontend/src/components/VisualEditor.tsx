import React, { useMemo, useRef, useState, useEffect } from 'react';
import { DAGNodeType, DAGWorkflow, DAGNode, DAGEdge } from '@/lib/flows/dagExecutor';
import { AGENT_CONFIGS, AgentName } from '@/lib/types';
import { AVAILABLE_CONNECTORS } from '@/lib/connectors';

interface VisualEditorProps {
  onRunWorkflow: (workflowId: string) => void;
}

const NODE_WIDTH = 230;
const NODE_HEIGHT = 96;

export default function VisualEditor({ onRunWorkflow }: VisualEditorProps) {
  const [workflows, setWorkflows] = useState<DAGWorkflow[]>([]);
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  
  const [edgeSource, setEdgeSource] = useState<string | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/workflows')
      .then(res => res.json())
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
    [workflows, activeWorkflowId]
  );
  const selectedNode = activeWorkflow?.nodes.find((n) => n.id === selectedNodeId) ?? null;

  const handleCreateWorkflow = () => {
    const newWorkflow = {
      name: 'New Custom Workflow',
      description: 'A custom orchestration flow',
      version: '1.0',
      nodes: [],
      edges: []
    };
    fetch('/api/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newWorkflow)
    }).then(res => res.json()).then((saved) => {
      setWorkflows([saved, ...workflows]);
      setActiveWorkflowId(saved.id);
    });
  };

  const handleSaveWorkflow = () => {
    if (!activeWorkflow) return;
    fetch(`/api/workflows/${activeWorkflow.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(activeWorkflow)
    }).then(() => alert('Workflow Saved Successfully!'));
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
    setWorkflows(prev => prev.map(wf => 
      wf.id === activeWorkflowId 
        ? { ...wf, nodes: [...wf.nodes, newNode] }
        : wf
    ));
    setSelectedNodeId(newNode.id);
  };

  const handleNodeClick = (nodeId: string) => {
    if (edgeSource) {
      if (edgeSource !== nodeId) {
        // Create Edge
        const newEdge: DAGEdge = {
          id: `e-${Date.now()}`,
          from: edgeSource,
          to: nodeId
        };
        setWorkflows(prev => prev.map(wf => 
          wf.id === activeWorkflowId 
            ? { ...wf, edges: [...wf.edges, newEdge] }
            : wf
        ));
      }
      setEdgeSource(null);
    } else {
      setSelectedNodeId(nodeId);
    }
  };

  const handleNodeMouseDown = (e: React.MouseEvent<HTMLDivElement>, nodeId: string) => {
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
    if (e.target === canvasRef.current || (e.target as HTMLElement).id === 'canvas-inner') {
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

    if (!isDragging || !selectedNodeId || !activeWorkflow || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - dragOffset.x - pan.x) / zoom;
    const y = (e.clientY - rect.top - dragOffset.y - pan.y) / zoom;
    setWorkflows((prev) =>
      prev.map((wf) =>
        wf.id !== activeWorkflowId
          ? wf
          : { ...wf, nodes: wf.nodes.map((n) => (n.id === selectedNodeId ? { ...n, x, y } : n)) }
      )
    );
  };

  const stopDragging = () => {
    setIsDragging(false);
    setIsPanning(false);
  };

  const updateSelectedNode = (updates: Partial<DAGNode>) => {
    setWorkflows(prev => prev.map(wf => 
      wf.id === activeWorkflowId 
        ? { ...wf, nodes: wf.nodes.map(n => n.id === selectedNodeId ? { ...n, ...updates } : n) }
        : wf
    ));
  };

  const getNodeColor = (type: DAGNodeType, agentName?: AgentName) => {
    if (type === 'agent' && agentName) return AGENT_CONFIGS[agentName]?.color ?? '#6366f1';
    if (type === 'condition') return '#f59e0b';
    if (type === 'parallel') return '#06b6d4';
    if (type === 'human_checkpoint') return '#ec4899';
    if (type === 'merge') return '#10b981';
    if (type === 'trigger') return '#84cc16';
    if (type === 'action') return '#d946ef';
    return '#6366f1';
  };

  const getNodeIcon = (type: DAGNodeType, agentName?: AgentName) => {
    if (type === 'agent' && agentName) return AGENT_CONFIGS[agentName]?.icon ?? '⚙️';
    if (type === 'condition') return '🔀';
    if (type === 'parallel') return '⚡';
    if (type === 'human_checkpoint') return '👤';
    if (type === 'merge') return '✅';
    if (type === 'trigger') return '🔌';
    if (type === 'action') return '🚀';
    return '⚙️';
  };

  const renderEdges = () => {
    if (!activeWorkflow) return null;
    return (
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1 }}>
        <defs>
          <marker id="ve-arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255,255,255,0.35)" />
          </marker>
        </defs>
        {activeWorkflow.edges.map((edge) => {
          const fromNode = activeWorkflow.nodes.find((n) => n.id === edge.from);
          const toNode = activeWorkflow.nodes.find((n) => n.id === edge.to);
          if (!fromNode || !toNode) return null;

          const startX = fromNode.x * zoom + NODE_WIDTH * zoom * 0.5;
          const startY = fromNode.y * zoom + NODE_HEIGHT * zoom;
          const endX = toNode.x * zoom + NODE_WIDTH * zoom * 0.5;
          const endY = toNode.y * zoom;
          const midY = startY + (endY - startY) * 0.5;
          const path = `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;

          return (
            <g key={edge.id}>
              <path d={path} fill="none" stroke="rgba(148,163,184,0.45)" strokeWidth={2} markerEnd="url(#ve-arrow)" />
              {edge.label && (
                <text x={(startX + endX) / 2} y={midY - 6} fill="#a5b4fc" fontSize="10" textAnchor="middle">
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 320px', height: '100%' }}>
      <aside style={{ borderRight: '1px solid var(--border-primary)', background: 'rgba(10,14,24,0.9)', padding: '14px', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <div style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Workflow Catalog
          </div>
          <button 
            onClick={handleCreateWorkflow}
            style={{ background: 'rgba(99,102,241,0.2)', color: '#a5b4fc', border: 'none', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
          >
            + New
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {workflows.map((wf) => {
            const active = wf.id === activeWorkflowId;
            return (
              <button
                key={wf.id}
                onClick={() => { setActiveWorkflowId(wf.id); setSelectedNodeId(null); }}
                style={{
                  textAlign: 'left', padding: '10px 12px', borderRadius: '10px',
                  border: active ? '1px solid rgba(99,102,241,0.5)' : '1px solid var(--border-primary)',
                  background: active ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.03)',
                  color: active ? '#c7d2fe' : 'var(--text-secondary)', cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '13px', color: active ? '#e0e7ff' : '#d1d5db' }}>{wf.name}</div>
                <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.8 }}>{wf.description}</div>
              </button>
            );
          })}
        </div>

        <div style={{ marginTop: '20px', paddingTop: '14px', borderTop: '1px solid var(--border-primary)' }}>
          <div style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>
            Node Palette (Drag & Drop)
          </div>
          {['trigger', 'agent', 'condition', 'parallel', 'action', 'human_checkpoint', 'merge'].map((type) => (
            <button 
              key={type} 
              onClick={() => handleAddNode(type as DAGNodeType)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px', width: '100%', background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', padding: '8px', borderRadius: '6px', cursor: 'pointer' }}
            >
              <span style={{ width: '8px', height: '8px', borderRadius: '999px', background: getNodeColor(type as DAGNodeType) }} />
              <span>+ Add {type.replace('_', ' ')}</span>
            </button>
          ))}
        </div>
      </aside>

      <section style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-primary)', background: 'rgba(9,12,20,0.9)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: '#e5e7eb' }}>{activeWorkflow?.name || 'Loading...'}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Interactive Workflow Builder
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button onClick={() => setZoom((z) => Math.max(0.6, Number((z - 0.1).toFixed(2))))} style={{ padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--border-primary)', background: 'rgba(255,255,255,0.04)', color: '#d1d5db', cursor: 'pointer' }}>-</button>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#94a3b8', minWidth: '52px', textAlign: 'center' }}>
              {Math.round(zoom * 100)}%
            </div>
            <button onClick={() => setZoom((z) => Math.min(1.8, Number((z + 0.1).toFixed(2))))} style={{ padding: '6px 10px', borderRadius: '8px', border: '1px solid var(--border-primary)', background: 'rgba(255,255,255,0.04)', color: '#d1d5db', cursor: 'pointer' }}>+</button>
            
            <button
              onClick={handleSaveWorkflow}
              style={{ marginLeft: '6px', padding: '8px 14px', borderRadius: '9px', border: '1px solid rgba(16,185,129,0.4)', background: 'rgba(16,185,129,0.1)', color: '#34d399', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
            >
              Save Workflow
            </button>

            <button
              onClick={() => activeWorkflow && onRunWorkflow(activeWorkflow.id)}
              style={{ marginLeft: '6px', padding: '8px 14px', borderRadius: '9px', border: '1px solid rgba(16,185,129,0.4)', background: 'linear-gradient(135deg, rgba(16,185,129,0.35), rgba(5,150,105,0.22))', color: '#ecfdf5', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
            >
              Run Workflow
            </button>
          </div>
        </div>

        <div
          ref={canvasRef}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={stopDragging}
          onMouseLeave={stopDragging}
          onMouseDown={handleCanvasMouseDown}
          style={{ position: 'relative', flex: 1, overflow: 'hidden', backgroundColor: '#070b14', backgroundImage: 'linear-gradient(rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.08) 1px, transparent 1px)', backgroundSize: `${24 * zoom}px ${24 * zoom}px`, backgroundPosition: `${pan.x}px ${pan.y}px`, cursor: isPanning ? 'grabbing' : 'grab' }}
        >
          <div id="canvas-inner" style={{ position: 'absolute', inset: 0, transform: `translate(${pan.x}px, ${pan.y}px)` }}>
            {renderEdges()}
            {activeWorkflow?.nodes.map((node) => {
              const isSelected = node.id === selectedNodeId;
              const isEdgeSource = node.id === edgeSource;
              const nodeColor = getNodeColor(node.type, node.agentName);
              const nodeIcon = getNodeIcon(node.type, node.agentName);
              
              const isConnector = node.type === 'trigger' || node.type === 'action';
              const isCondition = node.type === 'condition';

              let clipPath = 'none';
              let borderRadius = 12 * zoom;
              let customPadding = `${10 * zoom}px ${12 * zoom}px`;
              let customFlexDirection: 'row' | 'column' = 'row';
              let heightStr = 'auto';

              if (isConnector) {
                clipPath = 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)';
                borderRadius = 0;
                customPadding = `${25 * zoom}px ${45 * zoom}px`;
                customFlexDirection = 'column';
                heightStr = `${NODE_WIDTH * zoom}px`; // Make it a perfect square bounding box so it becomes a perfect diamond
              } else if (isCondition) {
                clipPath = 'polygon(15% 0, 85% 0, 100% 50%, 85% 100%, 15% 100%, 0 50%)';
                borderRadius = 0;
                customPadding = `${15 * zoom}px ${35 * zoom}px`;
              }
              
              // We rely on drop-shadow instead of box-shadow because clip-path hides box-shadow
              const shadowFilter = isSelected ? `drop-shadow(0 0 8px ${nodeColor})` : 'drop-shadow(0 10px 15px rgba(2,6,23,0.45))';
              const borderStyle = (isConnector || isCondition) ? 'none' : `1px solid ${isSelected ? nodeColor : isEdgeSource ? '#f59e0b' : 'rgba(148,163,184,0.28)'}`;

              return (
                <div
                  key={node.id}
                  onClick={() => handleNodeClick(node.id)}
                  onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                  style={{
                    position: 'absolute', left: node.x * zoom, top: node.y * zoom, 
                    width: NODE_WIDTH * zoom, 
                    minHeight: isConnector ? heightStr : NODE_HEIGHT * zoom,
                    height: isConnector ? heightStr : 'auto',
                    borderRadius,
                    clipPath,
                    border: borderStyle,
                    background: isSelected && (isConnector || isCondition) ? `linear-gradient(135deg, ${nodeColor}22, rgba(9,14,28,0.98))` : 'linear-gradient(135deg, rgba(15,23,42,0.96), rgba(9,14,28,0.98))',
                    filter: shadowFilter,
                    boxShadow: (isConnector || isCondition) ? 'none' : isSelected ? `0 0 0 1px ${nodeColor}, 0 18px 38px rgba(2,6,23,0.65)` : 'none',
                    zIndex: isSelected ? 20 : 10, cursor: isDragging && isSelected ? 'grabbing' : edgeSource ? 'crosshair' : 'pointer', userSelect: 'none', overflow: 'hidden',
                    display: 'flex', flexDirection: 'column', justifyContent: 'center'
                  }}
                >
                  {!(isConnector || isCondition) && <div style={{ height: '4px', background: nodeColor, opacity: 0.9, flexShrink: 0 }} />}
                  <div style={{ padding: customPadding, display: 'flex', flexDirection: customFlexDirection, alignItems: 'center', justifyContent: 'center', gap: `${10 * zoom}px`, flex: 1 }}>
                    <div style={{ width: `${30 * zoom}px`, height: `${30 * zoom}px`, borderRadius: `${8 * zoom}px`, background: `${nodeColor}24`, color: nodeColor, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: `${16 * zoom}px`, flexShrink: 0 }}>
                      {nodeIcon}
                    </div>
                    <div style={{ minWidth: 0, textAlign: customFlexDirection === 'column' ? 'center' : 'left' }}>
                      <div style={{ fontSize: `${12 * zoom}px`, fontWeight: 700, color: '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.label}</div>
                      <div style={{ fontSize: `${10 * zoom}px`, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{node.type}</div>
                    </div>
                  </div>
                  {!(isConnector || isCondition) && (
                    <div style={{ padding: `0 ${12 * zoom}px ${10 * zoom}px`, fontSize: `${10 * zoom}px`, color: '#a5b4fc', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {node.agentName || node.connectorId || node.id}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <aside style={{ borderLeft: '1px solid var(--border-primary)', background: 'rgba(10,14,24,0.9)', padding: '14px', overflowY: 'auto' }}>
        <div style={{ fontSize: '11px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px' }}>
          Node Inspector
        </div>
        {!selectedNode && (
          <div style={{ padding: '12px', borderRadius: '10px', border: '1px solid var(--border-primary)', background: 'rgba(255,255,255,0.03)', color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.6 }}>
            Select a node to inspect and edit configuration.
          </div>
        )}
        {selectedNode && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ padding: '12px', borderRadius: '10px', border: '1px solid rgba(99,102,241,0.3)', background: 'rgba(99,102,241,0.1)' }}>
              <input 
                type="text" 
                value={selectedNode.label} 
                onChange={(e) => updateSelectedNode({ label: e.target.value })}
                style={{ width: '100%', background: 'transparent', border: 'none', color: '#e0e7ff', fontWeight: 700, fontSize: '13px', outline: 'none' }}
              />
              <div style={{ color: '#a5b4fc', fontSize: '11px', marginTop: '4px' }}>{selectedNode.type}</div>
            </div>
            
            <div style={{ padding: '10px', borderRadius: '9px', border: '1px solid var(--border-primary)', background: 'rgba(255,255,255,0.03)', fontSize: '12px' }}>
              <div style={{ color: 'var(--text-muted)', marginBottom: '6px' }}>Node ID</div>
              <div style={{ color: '#cbd5e1', fontFamily: 'var(--font-mono)' }}>{selectedNode.id}</div>
            </div>

            {selectedNode.type === 'agent' && (
              <div style={{ padding: '10px', borderRadius: '9px', border: '1px solid var(--border-primary)', background: 'rgba(255,255,255,0.03)', fontSize: '12px' }}>
                <div style={{ color: 'var(--text-muted)', marginBottom: '6px' }}>Bound Agent</div>
                <select 
                  value={selectedNode.agentName || ''}
                  onChange={(e) => updateSelectedNode({ agentName: e.target.value as AgentName })}
                  style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-primary)', color: 'white', padding: '6px', borderRadius: '4px' }}
                >
                  <option value="">-- Select Agent --</option>
                  {Object.keys(AGENT_CONFIGS).map(agent => (
                    <option key={agent} value={agent}>{agent}</option>
                  ))}
                </select>
              </div>
            )}

            {(selectedNode.type === 'trigger' || selectedNode.type === 'action') && (
              <div style={{ padding: '10px', borderRadius: '9px', border: '1px solid var(--border-primary)', background: 'rgba(255,255,255,0.03)', fontSize: '12px' }}>
                <div style={{ color: 'var(--text-muted)', marginBottom: '6px' }}>Connector</div>
                <select 
                  value={selectedNode.connectorId || ''}
                  onChange={(e) => updateSelectedNode({ connectorId: e.target.value })}
                  style={{ width: '100%', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-primary)', color: 'white', padding: '6px', borderRadius: '4px' }}
                >
                  <option value="">-- Select Connector --</option>
                  {AVAILABLE_CONNECTORS.map(conn => (
                    <option key={conn.id} value={conn.id}>{conn.icon} {conn.name}</option>
                  ))}
                </select>
              </div>
            )}

            <button 
              onClick={() => setEdgeSource(selectedNode.id)}
              style={{ padding: '8px', borderRadius: '6px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.4)', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
            >
              {edgeSource === selectedNode.id ? 'Click target node...' : '+ Add Outgoing Edge'}
            </button>
            
            <button 
              onClick={() => {
                setWorkflows(prev => prev.map(wf => wf.id === activeWorkflowId ? {
                  ...wf, 
                  nodes: wf.nodes.filter(n => n.id !== selectedNode.id),
                  edges: wf.edges.filter(e => e.from !== selectedNode.id && e.to !== selectedNode.id)
                } : wf));
                setSelectedNodeId(null);
              }}
              style={{ padding: '8px', borderRadius: '6px', background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.4)', cursor: 'pointer', fontSize: '12px', fontWeight: 600, marginTop: '10px' }}
            >
              Delete Node
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}
