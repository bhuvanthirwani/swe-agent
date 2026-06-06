import React, { useState, useEffect } from 'react';

interface Agent {
  id: number;
  name: string;
  type: string;
  description: string;
  system_prompt: string;
  input_schema?: string;
  output_schema?: string;
  tool_ids?: number[];
}

interface Tool {
  id: number;
  name: string;
  description: string;
}

export default function AgentManagementPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editingAgentId, setEditingAgentId] = useState<number | null>(null);
  const [formData, setFormData] = useState<{name: string, type: string, description: string, system_prompt: string, input_schema: string, output_schema: string, tool_ids: number[]}>({ name: '', type: 'generator', description: '', system_prompt: '', input_schema: '', output_schema: '', tool_ids: [] });

  useEffect(() => {
    if (isOpen) {
      fetchAgents();
      fetchTools();
      fetchSystemLock();
    }
  }, [isOpen]);

  const fetchSystemLock = async () => {
    try {
      const res = await fetch('/api/system/lock');
      if (res.ok) {
        const data = await res.json();
        setIsLocked(data.locked);
      }
    } catch (err) {
      console.error('Failed to fetch system lock', err);
    }
  };

  const fetchTools = async () => {
    try {
      const res = await fetch('/api/tools');
      if (res.ok) {
        setTools(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch tools', err);
    }
  };

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/agents');
      if (res.ok) {
        const data = await res.json();
        setAgents(data);
      }
    } catch (err) {
      console.error('Failed to fetch agents', err);
    } finally {
      setLoading(false);
    }
  };

  const submitAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLocked) return;
    
    try {
      const method = editMode ? 'PUT' : 'POST';
      const url = editMode && editingAgentId ? `/api/agents/${editingAgentId}` : '/api/agents';
      
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setFormData({ name: '', type: 'generator', description: '', system_prompt: '', input_schema: '', output_schema: '', tool_ids: [] });
        setEditMode(false);
        setEditingAgentId(null);
        fetchAgents();
      }
    } catch (err) {
      console.error('Failed to save agent', err);
    }
  };

  const handleEdit = (agent: Agent) => {
    if (isLocked) return;
    setFormData({
      name: agent.name,
      type: agent.type,
      description: agent.description,
      system_prompt: agent.system_prompt,
      input_schema: agent.input_schema || '',
      output_schema: agent.output_schema || '',
      tool_ids: agent.tool_ids || []
    });
    setEditMode(true);
    setEditingAgentId(agent.id);
  };

  const deleteAgent = async (id: number) => {
    if (isLocked) return;
    try {
      await fetch(`/api/agents/${id}`, { method: 'DELETE' });
      fetchAgents();
    } catch (err) {
      console.error('Failed to delete agent', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(5px)',
      display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999
    }}>
      <div style={{
        background: 'linear-gradient(145deg, #1e293b, #0f172a)',
        borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)',
        padding: '30px', width: '700px', maxHeight: '85vh', overflowY: 'auto',
        color: '#fff', fontFamily: 'Inter, sans-serif', boxShadow: '0 20px 40px rgba(0,0,0,0.6)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600, color: '#38bdf8' }}>🤖 Agent Management</h2>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '20px' }}>✕</button>
        </div>

        {isLocked && (
          <div style={{ marginBottom: '20px', padding: '12px 16px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.4)', borderRadius: '8px', color: '#fca5a5', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>⚠️</span> <strong>System Locked:</strong> A workflow is currently running or paused. You cannot create, edit, or delete agents until it completes.
          </div>
        )}

        <form onSubmit={submitAgent} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginBottom: '30px', background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '12px' }}>
          <div style={{ display: 'flex', gap: '15px' }}>
            <input disabled={isLocked} required placeholder="Agent Name (e.g. Developer)" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} style={{ flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: '#020617', color: '#fff', opacity: isLocked ? 0.5 : 1 }} />
            <select disabled={isLocked} value={formData.type} onChange={e => setFormData({ ...formData, type: e.target.value })} style={{ width: '150px', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: '#020617', color: '#fff', opacity: isLocked ? 0.5 : 1 }}>
              <option value="generator">Generator</option>
              <option value="reviewer">Reviewer</option>
              <option value="planner">Planner</option>
            </select>
          </div>
          <input disabled={isLocked} required placeholder="Short Description" value={formData.description} onChange={e => setFormData({ ...formData, description: e.target.value })} style={{ padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: '#020617', color: '#fff', opacity: isLocked ? 0.5 : 1 }} />
          <textarea disabled={isLocked} required placeholder="System Prompt: You are an expert..." value={formData.system_prompt} onChange={e => setFormData({ ...formData, system_prompt: e.target.value })} style={{ padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: '#020617', color: '#fff', minHeight: '120px', opacity: isLocked ? 0.5 : 1 }} />
          
          <div style={{ display: 'flex', gap: '15px' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ background: '#1e1e1e', color: '#858585', padding: '6px 12px', fontSize: '11px', fontWeight: 600, borderTopLeftRadius: '8px', borderTopRightRadius: '8px', border: '1px solid #333', borderBottom: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#ff5f56' }} />
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#ffbd2e' }} />
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#27c93f' }} />
                <span style={{ marginLeft: '10px' }}>Input Schema (JSON)</span>
              </div>
              <textarea disabled={isLocked} placeholder="{}" value={formData.input_schema} onChange={e => setFormData({ ...formData, input_schema: e.target.value })} style={{ flex: 1, padding: '12px', borderBottomLeftRadius: '8px', borderBottomRightRadius: '8px', borderTop: 'none', border: '1px solid #333', background: '#1e1e1e', color: '#d4d4d4', minHeight: '120px', opacity: isLocked ? 0.5 : 1, fontFamily: '"Consolas", "Monaco", monospace', fontSize: '12px', outline: 'none', resize: 'vertical' }} />
            </div>
            
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ background: '#1e1e1e', color: '#858585', padding: '6px 12px', fontSize: '11px', fontWeight: 600, borderTopLeftRadius: '8px', borderTopRightRadius: '8px', border: '1px solid #333', borderBottom: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#ff5f56' }} />
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#ffbd2e' }} />
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#27c93f' }} />
                <span style={{ marginLeft: '10px' }}>Output Schema (JSON)</span>
              </div>
              <textarea disabled={isLocked} placeholder="{}" value={formData.output_schema} onChange={e => setFormData({ ...formData, output_schema: e.target.value })} style={{ flex: 1, padding: '12px', borderBottomLeftRadius: '8px', borderBottomRightRadius: '8px', borderTop: 'none', border: '1px solid #333', background: '#1e1e1e', color: '#d4d4d4', minHeight: '120px', opacity: isLocked ? 0.5 : 1, fontFamily: '"Consolas", "Monaco", monospace', fontSize: '12px', outline: 'none', resize: 'vertical' }} />
            </div>
          </div>

          <div style={{ padding: '15px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <strong style={{ display: 'block', marginBottom: '10px', fontSize: '14px', color: '#e2e8f0' }}>Enabled Tools</strong>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {tools.map(tool => (
                <label key={tool.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', background: 'rgba(0,0,0,0.3)', padding: '6px 12px', borderRadius: '6px', cursor: isLocked ? 'not-allowed' : 'pointer', opacity: isLocked ? 0.5 : 1 }}>
                  <input 
                    type="checkbox" 
                    disabled={isLocked}
                    checked={formData.tool_ids.includes(tool.id)}
                    onChange={e => {
                      if (e.target.checked) {
                        setFormData({ ...formData, tool_ids: [...formData.tool_ids, tool.id] });
                      } else {
                        setFormData({ ...formData, tool_ids: formData.tool_ids.filter(id => id !== tool.id) });
                      }
                    }}
                  />
                  {tool.name}
                </label>
              ))}
              {tools.length === 0 && <span style={{ color: '#64748b', fontSize: '13px' }}>No tools available.</span>}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button disabled={isLocked} type="submit" style={{ padding: '12px', borderRadius: '8px', background: editMode ? '#10b981' : '#0ea5e9', color: '#fff', border: 'none', fontWeight: 600, cursor: isLocked ? 'not-allowed' : 'pointer', opacity: isLocked ? 0.5 : 1, flex: 1 }}>
              {editMode ? '✓ Update Agent' : '+ Register Agent'}
            </button>
            {editMode && (
              <button disabled={isLocked} type="button" onClick={() => { setEditMode(false); setFormData({ name: '', type: 'generator', description: '', system_prompt: '', input_schema: '', output_schema: '', tool_ids: [] }); setEditingAgentId(null); }} style={{ padding: '12px', borderRadius: '8px', background: 'transparent', color: '#9ca3af', border: '1px solid #475569', fontWeight: 600, cursor: 'pointer', width: '100px' }}>
                Cancel
              </button>
            )}
          </div>
        </form>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {loading ? <p>Loading agents...</p> : agents.map(agent => (
            <div key={agent.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '15px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px', color: '#fff', marginBottom: '5px' }}>
                  {agent.name} <span style={{ fontSize: '10px', background: '#334155', padding: '2px 6px', borderRadius: '4px', textTransform: 'uppercase' }}>{agent.type}</span>
                </strong>
                <span style={{ fontSize: '13px', color: '#9ca3af', display: 'block', marginBottom: '8px' }}>{agent.description}</span>
                <div style={{ fontSize: '11px', color: '#64748b', background: '#020617', padding: '8px', borderRadius: '6px', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '500px' }}>
                  {agent.system_prompt}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button disabled={isLocked} onClick={() => handleEdit(agent)} style={{ background: '#3b82f6', border: 'none', borderRadius: '6px', padding: '6px 12px', color: '#fff', cursor: isLocked ? 'not-allowed' : 'pointer', fontSize: '12px', opacity: isLocked ? 0.5 : 1 }}>Edit</button>
                <button disabled={isLocked} onClick={() => deleteAgent(agent.id)} style={{ background: '#ef4444', border: 'none', borderRadius: '6px', padding: '6px 12px', color: '#fff', cursor: isLocked ? 'not-allowed' : 'pointer', fontSize: '12px', opacity: isLocked ? 0.5 : 1 }}>Delete</button>
              </div>
            </div>
          ))}
          {agents.length === 0 && !loading && <p style={{ color: '#9ca3af', textAlign: 'center' }}>No agents registered yet.</p>}
        </div>
      </div>
    </div>
  );
}
