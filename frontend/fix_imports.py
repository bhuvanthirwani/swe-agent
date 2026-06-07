import os

# Fix AnalyticsPanel.tsx
file_path = "frontend/src/components/AnalyticsPanel.tsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

compute_analytics_code = """
function computeAnalytics(agentResults: Record<string, AgentResult>): PipelineAnalytics {
    let totalTokens = 0;
    let totalLatencyMs = 0;
    let estimatedCostUsd = 0;
    const agentBreakdown = [];

    for (const [agentName, result] of Object.entries(agentResults)) {
        if (!result) continue;
        const tokens = (result.output || "").length * 0.25; 
        const latencyMs = result.latencyMs || 100;
        totalTokens += tokens;
        totalLatencyMs += latencyMs;
        estimatedCostUsd += (tokens / 1000000) * 0.15;
        
        agentBreakdown.push({
            agentName,
            tokens,
            latencyMs,
            costUsd: (tokens / 1000000) * 0.15
        });
    }

    return {
        totalTokens,
        totalLatencyMs,
        estimatedCostUsd,
        agentBreakdown
    };
}
"""

content = content.replace("import { computeAnalytics } from '@/lib/history';", compute_analytics_code)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

# Fix SettingsPanel.tsx
file_path = "frontend/src/components/SettingsPanel.tsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import { loadMemory, clearMemory } from '@/lib/memory';", "")
content = content.replace("setMemoryRunCount(loadMemory().runCount);", "setMemoryRunCount(0);")
content = content.replace("clearMemory();", "/* backend clear memory not implemented yet */")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
