// ============================================================
// Gap #2 — Multi-Provider LLM Registry
// Supports Groq, OpenAI, Anthropic, and Ollama.
// Each agent can independently use a different provider + model.
// ============================================================

import { createGroq } from '@ai-sdk/groq';
export * from './config';

export interface ProviderConfig {
  name: ProviderName;
  apiKey?: string;
  baseUrl?: string;
}

/**
 * Builds a provider instance from a config.
 * Falls back to Groq if the requested provider packages are not installed.
 */
export function buildProvider(config: ProviderConfig) {
  switch (config.name) {
    case 'groq':
      return createGroq({ apiKey: config.apiKey ?? process.env.GROQ_API_KEY! });

    case 'openai': {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { createOpenAI } = require('@ai-sdk/openai');
        return createOpenAI({ apiKey: config.apiKey ?? process.env.OPENAI_API_KEY });
      } catch {
        console.warn('[providers] @ai-sdk/openai not installed, falling back to Groq');
        return createGroq({ apiKey: process.env.GROQ_API_KEY! });
      }
    }

    case 'anthropic': {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { createAnthropic } = require('@ai-sdk/anthropic');
        return createAnthropic({ apiKey: config.apiKey ?? process.env.ANTHROPIC_API_KEY });
      } catch {
        console.warn('[providers] @ai-sdk/anthropic not installed, falling back to Groq');
        return createGroq({ apiKey: process.env.GROQ_API_KEY! });
      }
    }

    case 'ollama': {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { createOllama } = require('ollama-ai-provider');
        return createOllama({ baseURL: config.baseUrl ?? 'http://localhost:11434/api' });
      } catch {
        console.warn('[providers] ollama-ai-provider not installed, falling back to Groq');
        return createGroq({ apiKey: process.env.GROQ_API_KEY! });
      }
    }

    case 'google': {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { createGoogleGenerativeAI } = require('@ai-sdk/google');
        return createGoogleGenerativeAI({ apiKey: config.apiKey ?? process.env.GOOGLE_API_KEY });
      } catch {
        console.warn('[providers] @ai-sdk/google not installed, falling back to Groq');
        return createGroq({ apiKey: process.env.GROQ_API_KEY! });
      }
    }

    case 'aws-bedrock':
    case 'azure-openai':
      console.warn(`[providers] ${config.name} provider stub, falling back to Groq`);
      return createGroq({ apiKey: process.env.GROQ_API_KEY! });

    default:
      return createGroq({ apiKey: process.env.GROQ_API_KEY! });
  }
}

