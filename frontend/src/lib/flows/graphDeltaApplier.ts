import { DAGWorkflow, DAGNode, DAGEdge } from './dagExecutor';

export function applyGraphDelta(
  workflow: DAGWorkflow | null,
  delta: { op: string; payload: any },
  sessionId: string
): DAGWorkflow {
  // If no workflow exists, create a shell
  const current = workflow || {
    id: `wf-${sessionId}`,
    name: 'Generated Workflow',
    description: '',
    nodes: [],
    edges: [],
  };

  switch (delta.op) {
    case 'add_node': {
      const newNode = delta.payload as DAGNode;
      // Prevent duplicates
      if (current.nodes.some(n => n.id === newNode.id)) {
        return current;
      }
      return {
        ...current,
        nodes: [...current.nodes, newNode],
      };
    }
    case 'add_edge': {
      const newEdge = delta.payload as DAGEdge;
      if (current.edges.some(e => e.id === newEdge.id)) {
        return current;
      }
      return {
        ...current,
        edges: [...current.edges, newEdge],
      };
    }
    case 'remove_node': {
      return {
        ...current,
        nodes: current.nodes.filter(n => n.id !== delta.payload.id),
        edges: current.edges.filter(e => e.source !== delta.payload.id && e.target !== delta.payload.id),
      };
    }
    case 'remove_edge': {
      return {
        ...current,
        edges: current.edges.filter(e => e.id !== delta.payload.id),
      };
    }
    case 'update_node': {
      return {
        ...current,
        nodes: current.nodes.map(n => n.id === delta.payload.id ? delta.payload : n),
      };
    }
    default:
      return current;
  }
}
