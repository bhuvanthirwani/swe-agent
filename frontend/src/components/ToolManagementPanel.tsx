import React, { useState, useEffect } from 'react';

interface Tool {
  id: number;
  name: string;
  description: string;
  code_reference?: string;
}

export default function ToolManagementPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchTools();
    }
  }, [isOpen]);

  const fetchTools = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/tools');
      if (res.ok) {
        const data = await res.json();
        setTools(data);
      }
    } catch (err) {
      console.error('Failed to fetch tools', err);
    } finally {
      setLoading(false);
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
        background: 'linear-gradient(145deg, #1e1e2f, #252542)',
        borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)',
        padding: '30px', width: '600px', maxHeight: '80vh', overflowY: 'auto',
        color: '#fff', fontFamily: 'Inter, sans-serif', boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600, color: '#a5b4fc' }}>🛠️ Tool Management</h2>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '20px' }}>✕</button>
        </div>


        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {loading ? <p>Loading tools...</p> : tools.map(tool => (
            <div key={tool.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '15px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div>
                <strong style={{ display: 'block', fontSize: '16px', color: '#fff', marginBottom: '5px' }}>{tool.name}</strong>
                <span style={{ fontSize: '13px', color: '#9ca3af' }}>{tool.description}</span>
              </div>
            </div>
          ))}
          {tools.length === 0 && !loading && <p style={{ color: '#9ca3af', textAlign: 'center' }}>No tools registered yet.</p>}
        </div>
      </div>
    </div>
  );
}
