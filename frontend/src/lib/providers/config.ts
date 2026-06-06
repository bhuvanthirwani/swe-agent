import { ProviderName, AgentModelConfig } from '@/lib/types';

export const DEFAULT_AGENT_MODELS: Record<string, AgentModelConfig> = {
  'requirements-analyst': { provider: 'groq', model: 'llama-3.1-8b-instant' },
  'task-planner':         { provider: 'groq', model: 'meta-llama/llama-4-scout-17b-16e-instruct' },
  'developer':            { provider: 'groq', model: 'qwen/qwen3-32b' },
  'code-reviewer':        { provider: 'groq', model: 'llama-3.3-70b-versatile' },
  'security-reviewer':    { provider: 'groq', model: 'llama-3.3-70b-versatile' },
  'testing-agent':        { provider: 'groq', model: 'llama-3.3-70b-versatile' },
  'deployment-agent':     { provider: 'groq', model: 'llama-3.1-8b-instant' },
  'router-agent':         { provider: 'groq', model: 'llama-3.1-8b-instant' },
};

export const PROVIDER_MODELS: Record<ProviderName, string[]> = {
  groq: [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'qwen/qwen3-32b',
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'llama3-70b-8192',
  ],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o3-mini'],
  anthropic: ['claude-opus-4-5', 'claude-sonnet-4-5', 'claude-haiku-4-5-20251001'],
  ollama: ['llama3', 'mistral', 'codellama', 'deepseek-coder', 'phi3'],
  google: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-pro'],
  'aws-bedrock': ['anthropic.claude-v2', 'meta.llama3'],
  'azure-openai': ['gpt-4o', 'gpt-4o-mini', 'gpt-35-turbo'],
};

export function getModelForAgent(
  agentName: string,
  customModels?: Partial<Record<string, AgentModelConfig>>
): AgentModelConfig {
  return customModels?.[agentName] ?? DEFAULT_AGENT_MODELS[agentName] ?? { provider: 'groq', model: 'llama-3.1-8b-instant' };
}
