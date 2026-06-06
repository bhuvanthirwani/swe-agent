import React, { useState, useEffect } from 'react';

export default function SuggestionPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([
    {
      id: 1, project_name: 'swe-agent', title: 'Migrate to Universal Agent Runtime',
      impact_level: 'High', description: 'Replace hardcoded agent files with dynamic SQLite configurations.',
      files_affected: ['Task.md', 'agent_runtime.py', 'tools_runtime.py']
    }
  ]);



  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(5px)',
      display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999
    }}>
      <div style={{
        background: 'linear-gradient(145deg, #181824, #0f0f17)',
        borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)',
        padding: '30px', width: '800px', maxHeight: '85vh', overflowY: 'auto',
        color: '#fff', fontFamily: 'Inter, sans-serif', boxShadow: '0 20px 40px rgba(0,0,0,0.8)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600, color: '#f472b6' }}>💡 Intelligence Suggestions</h2>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '20px' }}>✕</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {suggestions.map(s => (
            <div key={s.id} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(244,114,182,0.3)', borderRadius: '12px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: '#fff' }}>{s.title}</h3>
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                    <span style={{ fontSize: '12px', background: '#312e81', color: '#a5b4fc', padding: '4px 8px', borderRadius: '4px' }}>Project: {s.project_name}</span>
                    <span style={{ fontSize: '12px', background: '#831843', color: '#fbcfe8', padding: '4px 8px', borderRadius: '4px' }}>Impact: {s.impact_level}</span>
                  </div>
                  <p style={{ fontSize: '14px', color: '#cbd5e1', marginBottom: '15px', lineHeight: '1.5' }}>{s.description}</p>
                  <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                    <strong>Files:</strong> {s.files_affected.join(', ')}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '15px' }}>
                <span style={{ fontSize: '13px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  🔄 Processed automatically every 5 minutes and sent to Slack
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
