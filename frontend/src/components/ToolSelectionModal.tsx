'use client';

import { useState } from 'react';

const AVAILABLE_TOOLS = [
  { id: 'web_search', label: 'Web Search', description: 'Search the internet for information' },
  { id: 'file_read', label: 'Read File', description: 'Read contents of a local file' },
  { id: 'file_write', label: 'Write File', description: 'Write or modify a local file' },
  { id: 'execute_cmd', label: 'Execute Command', description: 'Run a shell command' },
  { id: 'database_query', label: 'Database Query', description: 'Query the connected database' },
];

interface ToolSelectionModalProps {
  initialTools?: string[];
  onSave: (tools: string[]) => void;
  onCancel: () => void;
}

export default function ToolSelectionModal({ initialTools = [], onSave, onCancel }: ToolSelectionModalProps) {
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set(initialTools));

  const toggleTool = (id: string) => {
    const newSet = new Set(selectedTools);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedTools(newSet);
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)', padding: '24px'
    }}>
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,15,25,0.98) 0%, rgba(20,20,35,0.98) 100%)',
        border: '1px solid rgba(255,255,255,0.12)', borderRadius: '16px', padding: '32px',
        width: '100%', maxWidth: '500px', boxShadow: '0 25px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(16,185,129,0.15)'
      }}>
        <h2 style={{ margin: '0 0 16px 0', color: '#fff', fontSize: '20px' }}>Configure Tools</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
          Select the tools this agent has access to during execution.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px', maxHeight: '300px', overflowY: 'auto' }}>
          {AVAILABLE_TOOLS.map(tool => (
            <label key={tool.id} style={{
              display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '12px',
              background: selectedTools.has(tool.id) ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${selectedTools.has(tool.id) ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
            }}>
              <input 
                type="checkbox" 
                checked={selectedTools.has(tool.id)}
                onChange={() => toggleTool(tool.id)}
                style={{ marginTop: '4px' }}
              />
              <div>
                <div style={{ color: '#fff', fontSize: '14px', fontWeight: 600 }}>{tool.label}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '2px' }}>{tool.description}</div>
              </div>
            </label>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{
            padding: '10px 16px', borderRadius: '8px', background: 'transparent',
            border: '1px solid rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer'
          }}>Cancel</button>
          <button onClick={() => onSave(Array.from(selectedTools))} style={{
            padding: '10px 16px', borderRadius: '8px', background: 'rgba(16,185,129,0.2)',
            border: '1px solid rgba(16,185,129,0.4)', color: '#34d399', fontWeight: 600, cursor: 'pointer'
          }}>Save Tools</button>
        </div>
      </div>
    </div>
  );
}
