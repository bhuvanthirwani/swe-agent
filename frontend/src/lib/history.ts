// ============================================================
// History — Pipeline analytics helper
// Re-exported from here to satisfy @/lib/history imports.
// ============================================================

import { AgentResult, PipelineAnalytics } from '@/lib/types';

/**
 * Compute per-agent and aggregate analytics from a completed pipeline run.
 */
export function computeAnalytics(
  agentResults: Record<string, AgentResult>
): PipelineAnalytics {
  let totalTokens = 0;
  let totalLatencyMs = 0;
  let estimatedCostUsd = 0;
  const agentBreakdown: PipelineAnalytics['agentBreakdown'] = [];

  for (const [agentName, result] of Object.entries(agentResults)) {
    if (!result) continue;
    const tokens = result.tokensUsed ?? Math.round((result.output || '').length * 0.25);
    const latencyMs = result.latencyMs ?? 100;
    const cost = (tokens / 1_000_000) * 0.15;

    totalTokens += tokens;
    totalLatencyMs += latencyMs;
    estimatedCostUsd += cost;

    agentBreakdown.push({ agentName, tokens, latencyMs, cost });
  }

  return { totalTokens, totalLatencyMs, estimatedCostUsd, agentBreakdown };
}
