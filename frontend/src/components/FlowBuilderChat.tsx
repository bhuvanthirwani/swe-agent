import React, { useState, useEffect, useRef } from 'react';
import { useFlowBuilderWS } from '../hooks/useFlowBuilderWS';
import { DAGWorkflow } from '../types';

interface FlowBuilderChatProps {
  sessionId: string;
  workflowId?: string;
  onWorkflowProposal?: (workflow: DAGWorkflow) => void;
  onClose?: () => void;
}

export const FlowBuilderChat: React.FC<FlowBuilderChatProps> = ({ sessionId, workflowId, onWorkflowProposal, onClose }) => {
  const { messages, status, isGenerating, draftWorkflow, sendMessage, undo, canUndo } = useFlowBuilderWS(sessionId, workflowId);
  const [input, setInput] = useState('');
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Apply workflow proposal to parent
  useEffect(() => {
    if (draftWorkflow && onWorkflowProposal) {
      onWorkflowProposal(draftWorkflow);
    }
  }, [draftWorkflow, onWorkflowProposal]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '350px',
      background: 'rgba(15,23,42,0.95)',
      borderLeft: '1px solid rgba(255,255,255,0.1)',
      color: 'white',
      fontFamily: 'var(--font-sans)',
      boxShadow: '-4px 0 15px rgba(0,0,0,0.5)',
      position: 'relative'
    }}>
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(0,0,0,0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {canUndo && (
            <button onClick={undo} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '4px', padding: '2px 6px', fontSize: '11px', color: '#cbd5e1', cursor: 'pointer' }} title="Undo last AI generation">↶ Undo</button>
          )}
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%', fontWeight: 600, fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '16px' }}>✨</span> AI Architect
          </div>
          <div style={{
            width: '8px', height: '8px', borderRadius: '50%',
            background: status === 'connected' ? '#10b981' : status === 'connecting' ? '#fbbf24' : '#ef4444',
            boxShadow: `0 0 5px ${status === 'connected' ? '#10b981' : 'transparent'}`
          }} title={`Status: ${status}`} />
        </div>
        {onClose && (
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer',
            fontSize: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '24px', height: '24px', borderRadius: '4px'
          }}>✕</button>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.length === 0 && (
          <div style={{ color: '#94a3b8', fontSize: '13px', textAlign: 'center', marginTop: '20px' }}>
            What do you want to build? Try: "Build a security-first pipeline with a human reviewer loop"
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={msg.id || i} style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div style={{
              maxWidth: '85%',
              padding: '10px 14px',
              borderRadius: '12px',
              fontSize: '13px',
              lineHeight: '1.5',
              background: msg.role === 'user' ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'rgba(255,255,255,0.05)',
              border: msg.role === 'user' ? 'none' : '1px solid rgba(255,255,255,0.1)',
              color: msg.role === 'system' ? '#ef4444' : 'white',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {msg.role === 'system' && <strong>System: </strong>}
              {msg.content}
              {msg.id === 'generating' && <span style={{ marginLeft: '4px', animation: 'pulse 1.5s infinite opacity' }}>▋</span>}
            </div>
            <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px', padding: '0 4px' }}>
              {msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'Architect' : 'System'}
            </div>
          </div>
        ))}
                {isGenerating && status === 'connected' && (
          <div style={{ padding: '12px', background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '8px', fontSize: '12px', color: '#a5b4fc', display: 'flex', alignItems: 'center', gap: '8px', animation: 'pulse 2s infinite' }}>
            <span style={{ fontSize: '14px' }}>⚡</span> Architecting workflow...
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            disabled={isGenerating || status !== 'connected'}
            placeholder={status !== 'connected' ? 'Connecting...' : isGenerating ? 'AI is thinking...' : 'Describe your workflow...'}
            style={{
              flex: 1,
              background: 'rgba(0,0,0,0.3)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '20px',
              padding: '10px 16px',
              color: 'white',
              fontSize: '13px',
              outline: 'none',
              transition: 'all 0.2s'
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isGenerating || status !== 'connected'}
            style={{
              background: (!input.trim() || isGenerating || status !== 'connected') ? 'rgba(255,255,255,0.1)' : 'linear-gradient(135deg, #6366f1, #4f46e5)',
              color: 'white',
              border: 'none',
              borderRadius: '50%',
              width: '38px',
              height: '38px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: (!input.trim() || isGenerating || status !== 'connected') ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              flexShrink: 0
            }}
          >
            ➤
          </button>
        </form>
      </div>
    </div>
  );
};
