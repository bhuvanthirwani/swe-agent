'use client';

import { useState } from 'react';
import { Connector } from '@/lib/connectors';

interface ConnectorConfigModalProps {
  initialConnectors?: string[];
  availableConnectors: Connector[];
  onSave: (connectors: string[]) => void;
  onCancel: () => void;
}

export default function ConnectorConfigModal({ initialConnectors = [], availableConnectors, onSave, onCancel }: ConnectorConfigModalProps) {
  const [selectedConnectors, setSelectedConnectors] = useState<Set<string>>(new Set(initialConnectors));

  const toggleConnector = (id: string) => {
    const newSet = new Set(selectedConnectors);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedConnectors(newSet);
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)', padding: '24px'
    }}>
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,15,25,0.98) 0%, rgba(20,20,35,0.98) 100%)',
        border: '1px solid rgba(255,255,255,0.12)', borderRadius: '16px', padding: '32px',
        width: '100%', maxWidth: '500px', boxShadow: '0 25px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(217,70,239,0.15)'
      }}>
        <h2 style={{ margin: '0 0 16px 0', color: '#fff', fontSize: '20px' }}>Configure Connectors</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
          Select the external system connectors this agent should use (e.g., Slack, GitHub).
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px', maxHeight: '300px', overflowY: 'auto' }}>
          {availableConnectors.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontStyle: 'italic' }}>
              No connectors available. Configure them in the Connectors Panel.
            </div>
          ) : (
            availableConnectors.map(connector => (
              <label key={connector.id} style={{
                display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '12px',
                background: selectedConnectors.has(connector.id) ? 'rgba(217,70,239,0.1)' : 'rgba(255,255,255,0.04)',
                border: `1px solid ${selectedConnectors.has(connector.id) ? 'rgba(217,70,239,0.3)' : 'rgba(255,255,255,0.1)'}`,
                borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
              }}>
                <input 
                  type="checkbox" 
                  checked={selectedConnectors.has(connector.id)}
                  onChange={() => toggleConnector(connector.id)}
                  style={{ marginTop: '4px' }}
                />
                <div>
                  <div style={{ color: '#fff', fontSize: '14px', fontWeight: 600 }}>{connector.icon} {connector.name}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '2px' }}>{connector.description}</div>
                </div>
              </label>
            ))
          )}
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{
            padding: '10px 16px', borderRadius: '8px', background: 'transparent',
            border: '1px solid rgba(255,255,255,0.2)', color: '#fff', cursor: 'pointer'
          }}>Cancel</button>
          <button onClick={() => onSave(Array.from(selectedConnectors))} style={{
            padding: '10px 16px', borderRadius: '8px', background: 'rgba(217,70,239,0.2)',
            border: '1px solid rgba(217,70,239,0.4)', color: '#d946ef', fontWeight: 600, cursor: 'pointer'
          }}>Save Connectors</button>
        </div>
      </div>
    </div>
  );
}
