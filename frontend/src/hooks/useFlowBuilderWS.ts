import { useState, useEffect, useCallback, useRef } from 'react';
import { DAGWorkflow } from '../types';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export function useFlowBuilderWS(sessionId: string, workflowId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [isGenerating, setIsGenerating] = useState(false);
  const [draftWorkflow, setDraftWorkflow] = useState<DAGWorkflow | null>(null);
  const [history, setHistory] = useState<DAGWorkflow[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    setStatus('connecting');
    const wsUrl = `ws://localhost:8000/api/flow-builder/ws?sessionId=${sessionId}${workflowId ? `&workflowId=${workflowId}` : ''}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setStatus('connected');
      ws.send(JSON.stringify({ type: 'ping' }));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleMessage(data);
      } catch (e) {
        console.error("WS parse error", e);
      }
    };
    
    ws.onclose = () => {
      setStatus('disconnected');
      // Exponential backoff could be implemented here
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };
    
    wsRef.current = ws;
  }, [sessionId, workflowId]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connect]);

  const handleMessage = (data: any) => {
    switch (data.type) {
      case 'assistant_token':
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant' && last.id === 'generating') {
            return [...prev.slice(0, -1), { ...last, content: last.content + data.token }];
          } else {
            return [...prev, { id: 'generating', role: 'assistant', content: data.token }];
          }
        });
        break;
      case 'assistant_message_complete':
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last && last.id === 'generating') {
            return [...prev.slice(0, -1), { ...last, id: Date.now().toString() }];
          }
          return prev;
        });
        break;
      case 'graph_delta':
        setDraftWorkflow(prev => applyGraphDelta(prev, data, sessionId));
        break;
      case 'workflow_proposal':
        setDraftWorkflow(prev => {
          if (prev) setHistory(h => [...h, prev]);
          return data.workflow;
        });
        setIsGenerating(false);
        break;
      case 'validation_result':
        if (!data.valid) {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'system',
            content: `Validation failed: ${data.errors.join(', ')}`
          }]);
        }
        break;
      case 'pong':
        break;
    }
  };

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setIsGenerating(true);
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content }]);
      // Pre-add assistant placeholder
      setMessages(prev => [...prev, { id: 'generating', role: 'assistant', content: '' }]);
      
      wsRef.current.send(JSON.stringify({
        type: 'user_message',
        content,
        sessionId,
        workflowId,
        currentWorkflow: draftWorkflow
      }));
    }
  }, [sessionId, workflowId]);


  const undo = useCallback(() => {
    setHistory(prev => {
      if (prev.length === 0) return prev;
      const newHistory = [...prev];
      const lastState = newHistory.pop();
      if (lastState) setDraftWorkflow(lastState);
      return newHistory;
    });
  }, []);

  return {
    messages,
    status,
    isGenerating,
    draftWorkflow,
    sendMessage,
    undo,
    canUndo: history.length > 0
  };

}
