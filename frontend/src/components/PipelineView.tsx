'use client';

import { useMemo } from 'react';
import { AgentName, AgentStatus, AgentResult, AGENT_CONFIGS } from '@/lib/types';
import AgentCard from './AgentCard';

interface PipelineViewProps {
    agentStatuses: Record<AgentName, AgentStatus>;
    agentResults: Record<string, AgentResult | null>;
    selectedAgent: AgentName | null;
    onSelectAgent: (agent: AgentName) => void;
    currentIteration: number;
    maxIterations: number;
    isRunning: boolean;
    parallelGroup?: string[] | null;
    activeWorkflowConfig?: any;
}

// Router runs first, then the standard pipeline agents (now includes security-reviewer)
const ROUTER_AGENT: AgentName = 'router-agent';

const PIPELINE_ORDER: AgentName[] = [
    'requirements-analyst',
    'task-planner',
    'developer',
    'code-reviewer',
    'security-reviewer',
    'testing-agent',
    'deployment-agent',
];

// Agents that run in parallel (Gap #6)
const PARALLEL_AGENTS = new Set(['testing-agent']);

export default function PipelineView({
    agentStatuses,
    agentResults,
    selectedAgent,
    onSelectAgent,
    currentIteration,
    maxIterations,
    isRunning,
    parallelGroup,
    activeWorkflowConfig,
}: PipelineViewProps) {
    // Dynamic Pipeline computation
    const { dynamicOrder, dynamicParallel } = useMemo(() => {
        if (!activeWorkflowConfig || !activeWorkflowConfig.nodes) {
            return { dynamicOrder: PIPELINE_ORDER, dynamicParallel: PARALLEL_AGENTS };
        }
        
        const nodes = activeWorkflowConfig.nodes || [];
        const edges = activeWorkflowConfig.edges || [];
        
        const inDegree: Record<string, number> = {};
        const adjList: Record<string, string[]> = {};
        const nodeMap: Record<string, any> = {};
        
        nodes.forEach((n: any) => {
            inDegree[n.id] = 0;
            adjList[n.id] = [];
            nodeMap[n.id] = n;
        });
        
        edges.forEach((e: any) => {
            if (adjList[e.from] && inDegree[e.to] !== undefined) {
                adjList[e.from].push(e.to);
                inDegree[e.to]++;
            }
        });
        
        const queue: string[] = [];
        Object.keys(inDegree).forEach(id => {
            if (inDegree[id] === 0) queue.push(id);
        });
        
        const sortedAgents: string[] = [];
        const parallelAgents = new Set<string>();
        
        while (queue.length > 0) {
            // Group nodes that can be processed in parallel
            const level = [...queue];
            queue.length = 0;
            
            const agentLevel: string[] = [];
            level.forEach(id => {
                const node = nodeMap[id];
                if (node.type === 'agent' && node.agentName) {
                    agentLevel.push(node.agentName);
                }
                
                adjList[id].forEach(neighbor => {
                    inDegree[neighbor]--;
                    if (inDegree[neighbor] === 0) {
                        queue.push(neighbor);
                    }
                });
            });
            
            if (agentLevel.length > 1) {
                agentLevel.forEach(a => parallelAgents.add(a));
            }
            sortedAgents.push(...agentLevel);
        }
        
        // Remove duplicates just in case
        const uniqueAgents = Array.from(new Set(sortedAgents));
        
        return { dynamicOrder: uniqueAgents, dynamicParallel: parallelAgents };
    }, [activeWorkflowConfig]);

    const displayOrder = activeWorkflowConfig ? dynamicOrder : PIPELINE_ORDER;
    const currentRouterAgent = displayOrder.length > 0 ? displayOrder[0] : ROUTER_AGENT;
    const remainingOrder = activeWorkflowConfig ? displayOrder.slice(1) : PIPELINE_ORDER;

    const getConnectorStatus = (index: number): string => {
        const currentAgent = remainingOrder[index];
        const nextAgent = remainingOrder[index + 1];

        if (agentStatuses[currentAgent] === 'complete') {
            if (agentStatuses[nextAgent] === 'running') return 'active';
            if (agentStatuses[nextAgent] === 'complete') return 'complete';
        }
        return '';
    };

    // Loop is between Developer (index 2) and Code Reviewer (index 3)
    const isInLoop = (
        agentStatuses['developer'] === 'running' ||
        agentStatuses['code-reviewer'] === 'running' ||
        (agentStatuses['developer'] === 'complete' && agentStatuses['code-reviewer'] === 'complete' &&
            agentStatuses['testing-agent'] === 'idle' && currentIteration > 1)
    );

    const isWaitingHITL = agentStatuses['developer'] === 'waiting_hitl';

    const routerStatus = agentStatuses[currentRouterAgent] ?? 'idle';
    const routerResult = agentResults[currentRouterAgent] ?? null;

    return (
        <div className="pipeline-section">
            <div className="pipeline-header">
                <div className="pipeline-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="16 3 21 3 21 8" />
                        <line x1="4" y1="20" x2="21" y2="3" />
                        <polyline points="21 16 21 21 16 21" />
                        <line x1="15" y1="15" x2="21" y2="21" />
                        <line x1="4" y1="4" x2="9" y2="9" />
                    </svg>
                    Agent Pipeline
                    {isRunning && (
                        <span style={{
                            fontSize: '12px',
                            color: 'var(--accent-indigo)',
                            fontWeight: 500,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                        }}>
                            <div className="spinner" style={{ width: '12px', height: '12px' }} />
                            Processing
                        </span>
                    )}
                </div>

                {currentIteration > 0 && (
                    <span className="pipeline-iteration-badge">
                        Iteration {currentIteration}/{maxIterations}
                    </span>
                )}
            </div>

            {/* HITL waiting banner */}
            {isWaitingHITL && (
                <div style={{
                    margin: '8px 0',
                    padding: '10px 14px',
                    background: 'rgba(245,158,11,0.08)',
                    border: '1px solid rgba(245,158,11,0.25)',
                    borderRadius: '10px',
                    fontSize: '12px',
                    color: '#fbbf24',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontWeight: 600,
                }}>
                    ⏸️ Pipeline paused — awaiting human review decision
                </div>
            )}

            {/* First Agent — shown at top of pipeline */}
            {(routerStatus !== 'idle') && (
                <div>
                    <AgentCard
                        agentName={currentRouterAgent}
                        status={routerStatus}
                        result={routerResult}
                        isSelected={selectedAgent === currentRouterAgent}
                        onClick={() => onSelectAgent(currentRouterAgent)}
                    />
                    <div className={`pipeline-connector ${routerStatus === 'complete' ? 'complete' : ''}`} />
                </div>
            )}

            {remainingOrder.map((agentName, index) => {
                const status = agentStatuses[agentName];
                const isSkipped = status === 'skipped';
                const isParallel = parallelGroup?.includes(agentName) || (dynamicParallel.has(agentName) && status === 'running');

                return (
                    <div key={agentName} style={isSkipped ? { opacity: 0.35, filter: 'grayscale(0.7)' } : undefined}>
                        {/* Gap #6: Parallel indicator */}
                        {isParallel && (
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                padding: '4px 12px',
                                fontSize: '11px',
                                fontWeight: 600,
                                color: 'var(--accent-indigo)',
                                marginBottom: '4px',
                            }}>
                                ⚡ Running in parallel
                            </div>
                        )}

                        <AgentCard
                            agentName={agentName}
                            status={status}
                            result={agentResults[agentName.replace(/-/g, '')] || agentResults[agentName]}
                            isSelected={selectedAgent === agentName}
                            onClick={() => !isSkipped && onSelectAgent(agentName)}
                            iteration={
                                (agentName === 'developer' || agentName === 'code-reviewer') ? currentIteration : undefined
                            }
                            maxIterations={
                                (agentName === 'developer' || agentName === 'code-reviewer') ? maxIterations : undefined
                            }
                        />

                        {/* Skipped label */}
                        {isSkipped && (
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                padding: '2px 12px',
                                fontSize: '11px',
                                color: 'var(--text-muted)',
                                fontStyle: 'italic',
                            }}>
                                ⏭ Skipped by router
                            </div>
                        )}

                        {/* Connector line between agents */}
                        {index < remainingOrder.length - 1 && (
                            <>
                                {/* Dev ↔ Reviewer loop indicator */}
                                {remainingOrder[index] === 'developer' && remainingOrder[index + 1] === 'code-reviewer' && isInLoop && (
                                    <div className="loop-indicator">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <polyline points="23 4 23 10 17 10" />
                                            <polyline points="1 20 1 14 7 14" />
                                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                                        </svg>
                                        Feedback Loop — Revision {currentIteration}/{maxIterations}
                                    </div>
                                )}
                                <div className={`pipeline-connector ${getConnectorStatus(index)}`} />
                            </>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
