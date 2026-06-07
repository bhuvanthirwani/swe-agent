'use client';

import { useState, useEffect } from 'react';
import { ProviderName, AgentName } from '@/lib/types';



interface LLMConfig {
  id: number;
  name: string;
  provider: string;
  model_name: string;
  api_key?: string;
  base_url?: string;
}

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  hitlEnabled: boolean;
  onHITLToggle: (enabled: boolean) => void;
}

export default function SettingsPanel({
  isOpen,
  onClose,
  hitlEnabled,
  onHITLToggle,
}: SettingsPanelProps) {
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([]);
  const [llmProviders, setLlmProviders] = useState<any[]>([]);
  const [agentLlms, setAgentLlms] = useState<Record<string, number>>({});
  
  const [githubToken, setGithubToken] = useState('');
  const [githubOwner, setGithubOwner] = useState('');
  const [slackWebhook, setSlackWebhook] = useState('');
  const [slackToken, setSlackToken] = useState('');
  const [agents, setAgents] = useState<any[]>([]);
  
  const [saved, setSaved] = useState(false);
  const [memoryRunCount, setMemoryRunCount] = useState(0);
  const [activeTab, setActiveTab] = useState<'providers' | 'agents' | 'connectors' | 'memory'>('providers');

  const [isTesting, setIsTesting] = useState(false);
  const [testStatus, setTestStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [slackTestStatus, setSlackTestStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Form for new LLM Config
  const [editingLLMId, setEditingLLMId] = useState<number | null>(null);
  const [newName, setNewName] = useState('');
  const [newProviderId, setNewProviderId] = useState<number>(0);
  const [newModelName, setNewModelName] = useState('');
  const [newApiKey, setNewApiKey] = useState('');

  const fetchConfigs = async () => {
    try {
      const res = await fetch('/api/llm_configs');
      if (res.ok) {
        setLlmConfigs(await res.json());
      }
      
      const resAgentsMapping = await fetch('/api/agent_llms');
      if (resAgentsMapping.ok) {
        setAgentLlms(await resAgentsMapping.json());
      }
      
      const resAgentsList = await fetch('/api/agents');
      if (resAgentsList.ok) {
        setAgents(await resAgentsList.json());
      }

      const resProviders = await fetch('/api/llm_providers');
      if (resProviders.ok) {
        const providers = await resProviders.json();
        setLlmProviders(providers);
        if (providers.length > 0 && newProviderId === 0) setNewProviderId(providers[0].id);
      }

      const resService = await fetch('/api/service_integrations/github_mcp');
      if (resService.ok) {
        const data = await resService.json();
        setGithubToken(data.github_token || '');
        setGithubOwner(data.github_owner || '');
        if (data.github_token) {
          setTestStatus('success');
        }
      }

      const resSlack = await fetch('/api/service_integrations/slack');
      if (resSlack.ok) {
        const data = await resSlack.json();
        setSlackWebhook(data.webhookUrl || '');
        setSlackToken(data.token || '');
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchConfigs();
      setMemoryRunCount(0);
    }
  }, [isOpen]);

  const handleAddLLM = async () => {
    if (!newModelName) return;
    try {
      const url = editingLLMId ? `/api/llm_configs/${editingLLMId}` : '/api/llm_configs';
      const method = editingLLMId ? 'PUT' : 'POST';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newName,
          provider_id: newProviderId,
          model_name: newModelName,
          api_key: newApiKey || undefined
        })
      });
      if (res.ok) {
        setNewName('');
        setNewModelName('');
        setNewApiKey('');
        setEditingLLMId(null);
        fetchConfigs();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleEditLLM = (config: any) => {
    setEditingLLMId(config.id);
    setNewName(config.name);
    setNewProviderId(config.provider_id);
    setNewModelName(config.model_name);
    setNewApiKey(config.api_key || '');
  };

  const handleCancelEdit = () => {
    setEditingLLMId(null);
    setNewName('');
    setNewModelName('');
    setNewApiKey('');
  };

  const handleDeleteLLM = async (id: number) => {
    try {
      const res = await fetch(`/api/llm_configs/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchConfigs();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleAgentLLMChange = async (agentName: string, llmId: number) => {
    try {
      const res = await fetch('/api/agent_llms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_name: agentName, llm_id: llmId })
      });
      if (res.ok) {
        setAgentLlms(prev => ({ ...prev, [agentName]: llmId }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleTestGitHub = async () => {
    if (!githubToken) return;
    setIsTesting(true);
    setTestStatus('idle');
    try {
      const res = await fetch('https://api.github.com/user', {
        headers: {
          'Authorization': `Bearer ${githubToken}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });
      if (res.ok) {
        setTestStatus('success');
      } else {
        setTestStatus('error');
      }
    } catch (err) {
      setTestStatus('error');
    } finally {
      setIsTesting(false);
    }
  };

  const handleTestSlack = async () => {
    setIsTesting(true);
    setSlackTestStatus('idle');
    try {
      const res = await fetch('/api/slack/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          webhook_url: slackWebhook,
          token: slackToken || undefined
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setSlackTestStatus('success');
      } else {
        setSlackTestStatus('error');
      }
    } catch (err) {
      setSlackTestStatus('error');
    } finally {
      setIsTesting(false);
    }
  };

  const save = async () => {
    try {
      await fetch('/api/service_integrations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_name: 'github_mcp',
          metadata: {
            github_token: githubToken,
            github_owner: githubOwner
          }
        })
      });
      await fetch('/api/service_integrations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_name: 'slack',
          metadata: {
            webhookUrl: slackWebhook,
            token: slackToken
          }
        })
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleClearMemory = () => {
    /* backend clear memory not implemented yet */
    setMemoryRunCount(0);
  };

  if (!isOpen) return null;

  const inputStyle = {
    width: '100%',
    padding: '9px 12px',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '13px',
    fontFamily: 'var(--font-sans)',
    outline: 'none',
    boxSizing: 'border-box' as const,
  };

  const tabStyle = (active: boolean) => ({
    padding: '7px 16px',
    borderRadius: '8px',
    border: 'none',
    background: active ? 'rgba(99,102,241,0.2)' : 'transparent',
    color: active ? '#818cf8' : 'var(--text-muted)',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    fontFamily: 'var(--font-sans)',
    transition: 'all 0.15s',
    boxShadow: active ? 'inset 0 0 0 1px rgba(99,102,241,0.3)' : 'none',
  });

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 900,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(0,0,0,0.65)',
      backdropFilter: 'blur(6px)',
      padding: '24px',
    }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'linear-gradient(135deg, rgba(12,12,22,0.99), rgba(18,18,32,0.99))',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '16px',
          padding: '28px',
          width: '100%',
          maxWidth: '680px',
          maxHeight: '85vh',
          overflowY: 'auto',
          boxShadow: '0 25px 60px rgba(0,0,0,0.7)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '22px' }}>⚙️</span>
            <div>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#fff' }}>Settings</h2>
              <p style={{ margin: '2px 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
                Providers, Models, Delivery & Memory
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '20px',
            lineHeight: 1,
            padding: '4px',
          }}>✕</button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '24px', padding: '4px', background: 'rgba(0,0,0,0.3)', borderRadius: '10px' }}>
          {(['providers', 'agents', 'connectors', 'memory'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={tabStyle(activeTab === tab)}>
              {{ providers: '🔑 Providers', agents: '🤖 Agent Models', connectors: '🔌 Connectors', memory: '🧠 Memory' }[tab]}
            </button>
          ))}
        </div>

        {/* Tab: Providers */}
        {activeTab === 'providers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                LLM Configurations
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                {llmConfigs.map(config => (
                  <div key={config.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 'bold' }}>{config.name}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{(config as any).provider_name} - {config.model_name}</div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button onClick={() => handleEditLLM(config)} style={{ background: 'transparent', color: '#6366f1', border: '1px solid #6366f1', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }}>Edit</button>
                      <button onClick={() => handleDeleteLLM(config.id)} style={{ background: 'transparent', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer' }}>Delete</button>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ padding: '16px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '10px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff', marginBottom: '12px' }}>Add New LLM</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <select value={newProviderId} onChange={e => setNewProviderId(parseInt(e.target.value))} style={inputStyle}>
                    {llmProviders.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <input type="text" placeholder="Display Name (e.g. Developer Agent)" value={newName} onChange={e => setNewName(e.target.value)} style={inputStyle} />
                  <input type="text" placeholder="Model Name (e.g. gpt-4o)" value={newModelName} onChange={e => setNewModelName(e.target.value)} style={inputStyle} />
                  <input type="password" placeholder="API Key (optional if in env)" value={newApiKey} onChange={e => setNewApiKey(e.target.value)} style={inputStyle} />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    <button onClick={handleAddLLM} style={{ padding: '8px 16px', background: 'rgba(99,102,241,0.2)', border: '1px solid #6366f1', color: '#818cf8', borderRadius: '8px', cursor: 'pointer', flex: 1 }}>
                      {editingLLMId ? '💾 Update LLM' : '+ Add LLM'}
                    </button>
                    {editingLLMId && (
                      <button onClick={handleCancelEdit} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: 'var(--text-muted)', borderRadius: '8px', cursor: 'pointer', flex: 1 }}>
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* Tab: Agent Models */}
        {activeTab === 'agents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <p style={{ margin: '0 0 8px', fontSize: '12px', color: 'var(--text-muted)' }}>
              Map each agent to an LLM configuration created in the Providers tab.
            </p>
            {agents.map((agent) => (
              <div key={agent.name} style={{
                padding: '12px 14px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.07)',
                borderRadius: '10px',
              }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#fff', marginBottom: '10px', textTransform: 'capitalize' }}>
                  {agent.name.replace('-', ' ')}
                </div>
                <select
                  value={agentLlms[agent.name] || ''}
                  onChange={e => handleAgentLLMChange(agent.name, parseInt(e.target.value))}
                  style={inputStyle}
                >
                  <option value="" disabled>Select LLM...</option>
                  {llmConfigs.map(config => (
                    <option key={config.id} value={config.id}>{config.name}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}

        {/* Tab: Connectors */}
        {activeTab === 'connectors' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{
              padding: '16px',
              background: 'rgba(239,68,68,0.06)',
              border: '1px solid rgba(239,68,68,0.15)',
              borderRadius: '10px',
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
                💬 Slack Integration
              </div>
              <p style={{ margin: '0 0 16px', fontSize: '12px', color: 'var(--text-muted)' }}>
                Connect to Slack to receive workflow notifications and Human-in-the-Loop approval requests.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Slack Webhook URL
                  </label>
                  <input
                    type="password"
                    placeholder="https://hooks.slack.com/services/..."
                    value={slackWebhook}
                    onChange={e => setSlackWebhook(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Slack Token (Optional, for Web API)
                  </label>
                  <input
                    type="password"
                    placeholder="xoxb-..."
                    value={slackToken}
                    onChange={e => { setSlackToken(e.target.value); setSlackTestStatus('idle'); }}
                    style={inputStyle}
                  />
                </div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                  <button
                    onClick={handleTestSlack}
                    disabled={isTesting || !slackWebhook}
                    style={{
                      padding: '8px 16px',
                      background: 'rgba(239,68,68,0.2)',
                      border: '1px solid #ef4444',
                      color: '#fca5a5',
                      borderRadius: '8px',
                      cursor: isTesting || !slackWebhook ? 'not-allowed' : 'pointer',
                      opacity: isTesting || !slackWebhook ? 0.6 : 1,
                    }}
                  >
                    {isTesting ? 'Testing...' : 'Test Connection'}
                  </button>
                  {slackTestStatus === 'success' && (
                    <div style={{ display: 'flex', alignItems: 'center', color: '#10b981', fontSize: '13px', fontWeight: 600 }}>
                      ✅ Connection Successful
                    </div>
                  )}
                  {slackTestStatus === 'error' && (
                    <div style={{ display: 'flex', alignItems: 'center', color: '#ef4444', fontSize: '13px', fontWeight: 600 }}>
                      ❌ Invalid Webhook/Token
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div style={{
              padding: '16px',
              background: 'rgba(99,102,241,0.06)',
              border: '1px solid rgba(99,102,241,0.15)',
              borderRadius: '10px',
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
                🐙 GitHub Push (MCP)
              </div>
              <p style={{ margin: '0 0 16px', fontSize: '12px', color: 'var(--text-muted)' }}>
                Automatically push generated code to a new GitHub repository after pipeline completion.
                Token stored in backend database.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    GitHub Personal Access Token (repo scope)
                  </label>
                  <input
                    type="password"
                    placeholder="ghp_..."
                    value={githubToken}
                    onChange={e => { setGithubToken(e.target.value); setTestStatus('idle'); }}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    GitHub Username / Owner
                  </label>
                  <input
                    type="text"
                    placeholder="your-github-username"
                    value={githubOwner}
                    onChange={e => { setGithubOwner(e.target.value); setTestStatus('idle'); }}
                    style={inputStyle}
                  />
                </div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                  <button
                    onClick={handleTestGitHub}
                    disabled={isTesting || !githubToken}
                    style={{
                      padding: '8px 16px',
                      background: 'rgba(99,102,241,0.2)',
                      border: '1px solid #6366f1',
                      color: '#818cf8',
                      borderRadius: '8px',
                      cursor: isTesting || !githubToken ? 'not-allowed' : 'pointer',
                      opacity: isTesting || !githubToken ? 0.6 : 1,
                    }}
                  >
                    {isTesting ? 'Testing...' : 'Test Connection'}
                  </button>
                  {testStatus === 'success' && (
                    <div style={{ display: 'flex', alignItems: 'center', color: '#10b981', fontSize: '13px', fontWeight: 600 }}>
                      ✅ Connection Successful
                    </div>
                  )}
                  {testStatus === 'error' && (
                    <div style={{ display: 'flex', alignItems: 'center', color: '#ef4444', fontSize: '13px', fontWeight: 600 }}>
                      ❌ Invalid Token
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Memory (Gap #8) */}
        {activeTab === 'memory' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{
              padding: '16px',
              background: 'rgba(139,92,246,0.06)',
              border: '1px solid rgba(139,92,246,0.15)',
              borderRadius: '10px',
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
                🧠 Agent Memory
              </div>
              <p style={{ margin: '0 0 16px', fontSize: '12px', color: 'var(--text-muted)' }}>
                The system learns your tech preferences (language, framework, DB) across sessions
                and injects them into agent prompts.
              </p>

              {memoryRunCount > 0 ? (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  background: 'rgba(139,92,246,0.08)',
                  borderRadius: '8px',
                  border: '1px solid rgba(139,92,246,0.2)',
                }}>
                  <div>
                    <div style={{ fontSize: '13px', color: '#a78bfa', fontWeight: 600 }}>
                      Memory Active — {memoryRunCount} previous run{memoryRunCount !== 1 ? 's' : ''} tracked
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Preferences automatically injected into future pipelines
                    </div>
                  </div>
                  <button
                    onClick={handleClearMemory}
                    style={{
                      padding: '7px 14px',
                      borderRadius: '8px',
                      border: '1px solid rgba(239,68,68,0.3)',
                      background: 'rgba(239,68,68,0.08)',
                      color: '#f87171',
                      fontSize: '12px',
                      cursor: 'pointer',
                      fontFamily: 'var(--font-sans)',
                      fontWeight: 600,
                    }}
                  >
                    🗑️ Clear Memory
                  </button>
                </div>
              ) : (
                <div style={{
                  padding: '12px 14px',
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: '8px',
                  fontSize: '13px',
                  color: 'var(--text-muted)',
                }}>
                  No memory yet. Run a pipeline and your preferences will be learned automatically.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '28px', justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{
            padding: '10px 20px',
            borderRadius: '9px',
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'transparent',
            color: 'var(--text-muted)',
            fontSize: '13px',
            cursor: 'pointer',
            fontFamily: 'var(--font-sans)',
          }}>
            Cancel
          </button>
          <button
            onClick={save}
            disabled={githubToken ? testStatus !== 'success' : false}
            style={{
              padding: '10px 24px',
              borderRadius: '9px',
              border: 'none',
              background: saved
                ? 'linear-gradient(135deg, #10b981, #059669)'
                : (githubToken && testStatus !== 'success') 
                  ? 'rgba(255,255,255,0.1)' 
                  : 'linear-gradient(135deg, #6366f1, #4f46e5)',
              color: (githubToken && testStatus !== 'success') ? '#666' : '#fff',
              fontSize: '13px',
              fontWeight: 600,
              cursor: (githubToken && testStatus !== 'success') ? 'not-allowed' : 'pointer',
              fontFamily: 'var(--font-sans)',
              transition: 'all 0.2s',
            }}
          >
            {saved ? '✅ Saved!' : '💾 Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
