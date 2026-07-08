'use client';

import { useState } from 'react';

interface MemoryConfigModalProps {
  initialConfig?: any;
  onSave: (config: any) => void;
  onCancel: () => void;
}

export default function MemoryConfigModal({ initialConfig, onSave, onCancel }: MemoryConfigModalProps) {
  const [memoryType, setMemoryType] = useState(initialConfig?.type || 'none');
  const [windowSize, setWindowSize] = useState(initialConfig?.windowSize || 10);

  const handleSave = () => {
    onSave({
      type: memoryType,
      windowSize: memoryType === 'buffer_window' ? windowSize : undefined
    });
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)', padding: '24px'
    }}>
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,15,25,0.98) 0%, rgba(20,20,35,0.98) 100%)',
        border: '1px solid rgba(255,255,255,0.12)', borderRadius: '16px', padding: '32px',
        width: '100%', maxWidth: '400px', boxShadow: '0 25px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(59,130,246,0.15)'
      }}>
        <h2 style={{ margin: '0 0 16px 0', color: '#fff', fontSize: '20px' }}>Configure Memory</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
          Set up how this agent remembers past interactions.
        </p>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: '12px', marginBottom: '8px' }}>Memory Type</label>
          <select 
            value={memoryType} 
            onChange={e => setMemoryType(e.target.value)}
            style={{
              width: '100%', padding: '10px', background: 'rgba(0,0,0,0.2)',
              border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '8px', outline: 'none'
            }}
          >
            <option value="none">None (Stateless)</option>
            <option value="buffer">Conversation Buffer</option>
            <option value="buffer_window">Conversation Buffer Window</option>
            <option value="vector_db">Vector Database</option>
          </select>
        </div>

        {memoryType === 'buffer_window' && (
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', color: 'var(--text-muted)', fontSize: '12px', marginBottom: '8px' }}>Window Size (messages)</label>
            <input 
              type="number" 
              value={windowSize} 
              onChange={e => setWindowSize(parseInt(e.target.value) || 1)}
              min="1"
              style={{
                width: '100%', padding: '10px', background: 'rgba(0,0,0,0.2)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '8px', outline: 'none'
              }}
            />
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
          <button onClick={onCancel} style={{
            padding: '10px 16px', borderRadius: '8px', background: 'transparent',
            border: '1px solid rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer'
          }}>Cancel</button>
          <button onClick={handleSave} style={{
            padding: '10px 16px', borderRadius: '8px', background: 'rgba(59,130,246,0.2)',
            border: '1px solid rgba(59,130,246,0.4)', color: '#60a5fa', fontWeight: 600, cursor: 'pointer'
          }}>Save Memory</button>
        </div>
      </div>
    </div>
  );
}
