// ============================================================
// DAG-Based Workflow Executor (Competitor Feature: Flexible Workflow Graphs)
// Supports branching, conditional routing, parallel groups,
// and human checkpoints — similar to Microsoft Agent Framework.
// ============================================================

import { AgentName } from '@/lib/types';

// ─── DAG Node Types ──────────────────────────────────────────

export type DAGNodeType = 'agent' | 'condition' | 'parallel' | 'human_checkpoint' | 'merge' | 'trigger' | 'action';

export interface DAGNode {
  id: string;
  type: DAGNodeType;
  agentName?: AgentName;
  label: string;
  description?: string;
  // Position for visual editor
  x: number;
  y: number;
  // Connector configuration
  connectorId?: string;
  // Condition node config
  condition?: {
    field: string;       // e.g., 'review.decision'
    operator: '==' | '!=' | '>' | '<' | 'contains';
    value: string;
    trueBranch: string;   // target node id
    falseBranch: string;  // target node id
  };
  // Parallel node config
  parallelBranches?: string[][]; // arrays of node IDs per branch
  // Human checkpoint config
  checkpointConfig?: {
    timeoutMs: number;
    autoApprove: boolean;
    instructions: string;
  };
}

export interface DAGEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  condition?: string; // e.g., 'approved', 'rejected'
}

export interface DAGWorkflow {
  id: string;
  name: string;
  description: string;
  version: string;
  nodes: DAGNode[];
  edges: DAGEdge[];
  entryNodeId: string;
  createdAt: string;
  updatedAt: string;
}

// ─── Execution State ─────────────────────────────────────────

export type NodeExecutionStatus = 'pending' | 'running' | 'complete' | 'error' | 'skipped' | 'waiting';

export interface NodeExecution {
  nodeId: string;
  status: NodeExecutionStatus;
  startedAt?: number;
  completedAt?: number;
  output?: string;
  error?: string;
}

export interface DAGExecutionState {
  workflowId: string;
  runId: string;
  nodeExecutions: Record<string, NodeExecution>;
  currentNodes: string[]; // nodes currently executing (can be parallel)
  completedNodes: string[];
  isComplete: boolean;
  startedAt: number;
}

// ─── Graph Utilities ─────────────────────────────────────────

/**
 * Topological sort of a DAG. Returns ordered node IDs.
 * Throws if a cycle is detected.
 */
export function topologicalSort(nodes: DAGNode[], edges: DAGEdge[]): string[] {
  const adjacency: Record<string, string[]> = {};
  const inDegree: Record<string, number> = {};

  nodes.forEach(n => {
    adjacency[n.id] = [];
    inDegree[n.id] = 0;
  });

  edges.forEach(e => {
    if (adjacency[e.from]) {
      adjacency[e.from].push(e.to);
      inDegree[e.to] = (inDegree[e.to] || 0) + 1;
    }
  });

  const queue: string[] = [];
  Object.entries(inDegree).forEach(([id, deg]) => {
    if (deg === 0) queue.push(id);
  });

  const sorted: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    sorted.push(current);
    for (const neighbor of adjacency[current] || []) {
      inDegree[neighbor]--;
      if (inDegree[neighbor] === 0) queue.push(neighbor);
    }
  }

  if (sorted.length !== nodes.length) {
    throw new Error('Cycle detected in workflow DAG');
  }
  return sorted;
}

/**
 * Get the immediate successors of a node.
 */
export function getSuccessors(nodeId: string, edges: DAGEdge[]): string[] {
  return edges.filter(e => e.from === nodeId).map(e => e.to);
}

/**
 * Get the immediate predecessors of a node.
 */
export function getPredecessors(nodeId: string, edges: DAGEdge[]): string[] {
  return edges.filter(e => e.to === nodeId).map(e => e.from);
}

/**
 * Check if all predecessors are complete.
 */
export function allPredecessorsComplete(
  nodeId: string,
  edges: DAGEdge[],
  completedNodes: Set<string>
): boolean {
  const preds = getPredecessors(nodeId, edges);
  return preds.every(p => completedNodes.has(p));
}

/**
 * Get the next executable nodes given current state.
 */
export function getNextExecutableNodes(
  workflow: DAGWorkflow,
  completedNodes: Set<string>,
  runningNodes: Set<string>
): string[] {
  return workflow.nodes
    .filter(n =>
      !completedNodes.has(n.id) &&
      !runningNodes.has(n.id) &&
      allPredecessorsComplete(n.id, workflow.edges, completedNodes)
    )
    .map(n => n.id);
}

// ─── Built-in DAG Workflows moved to Database Backend ─────────────────────────────────
