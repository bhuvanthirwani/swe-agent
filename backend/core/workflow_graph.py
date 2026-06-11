import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

RESOURCE_EDGE_TYPES: Set[str] = {
    "model",
    "tool",
    "memory",
    "rag",
    "vector",
    "guardrail",
    "connector",
}

EXECUTION_EDGE_TYPES: Set[str] = {
    "control",
    "data",
    "context",
    "error",
    "vector_write",
}

DEFAULT_EXECUTION_TYPES: Set[str] = {
    "agent",
    "condition",
    "parallel",
    "human_checkpoint",
    "merge",
    "trigger",
    "action",
}


def edge_type(edge: Dict[str, Any]) -> str:
    return str(edge.get("edgeType") or edge.get("type") or "control")


def is_resource_edge(edge: Dict[str, Any]) -> bool:
    return edge_type(edge) in RESOURCE_EDGE_TYPES


def is_execution_edge(edge: Dict[str, Any]) -> bool:
    # Older workflows do not have edgeType; keep them executable.
    return edge_type(edge) in EXECUTION_EDGE_TYPES


@dataclass
class WorkflowGraph:
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

    def __post_init__(self) -> None:
        self.node_map: Dict[str, Dict[str, Any]] = {
            str(node.get("id")): node for node in self.nodes if node.get("id")
        }

    @classmethod
    def from_json(cls, nodes_json: str, edges_json: str) -> "WorkflowGraph":
        return cls(json.loads(nodes_json or "[]"), json.loads(edges_json or "[]"))

    def node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.node_map.get(node_id)

    def incoming_edges(
        self, node_id: str, include_resources: bool = True
    ) -> List[Dict[str, Any]]:
        edges = [edge for edge in self.edges if edge.get("to") == node_id]
        if include_resources:
            return edges
        return [edge for edge in edges if is_execution_edge(edge)]

    def outgoing_edges(
        self, node_id: str, include_resources: bool = True
    ) -> List[Dict[str, Any]]:
        edges = [edge for edge in self.edges if edge.get("from") == node_id]
        if include_resources:
            return edges
        return [edge for edge in edges if is_execution_edge(edge)]

    def connected_resource_nodes(
        self, node_id: str, resource_type: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        resources: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for edge in self.incoming_edges(node_id):
            if not is_resource_edge(edge):
                continue
            if resource_type and edge_type(edge) != resource_type:
                continue
            source = self.node(str(edge.get("from")))
            if source:
                resources.append((source, edge))
        return resources

    def execution_edges(self) -> List[Dict[str, Any]]:
        return [edge for edge in self.edges if is_execution_edge(edge)]

    def topological_sort(self) -> List[Dict[str, Any]]:
        in_degree: Dict[str, int] = {node_id: 0 for node_id in self.node_map}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in self.node_map}

        for edge in self.execution_edges():
            source = str(edge.get("from"))
            target = str(edge.get("to"))
            if source in adjacency and target in in_degree:
                adjacency[source].append(target)
                in_degree[target] += 1

        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        sorted_ids: List[str] = []
        while queue:
            current = queue.pop(0)
            sorted_ids.append(current)
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_ids) != len(self.node_map):
            raise ValueError("Cycle detected in workflow execution graph")
        return [self.node_map[node_id] for node_id in sorted_ids]

    def validate(self) -> List[str]:
        errors: List[str] = []
        for node in self.nodes:
            if not node.get("id"):
                errors.append("Node missing id")
            if not node.get("type"):
                errors.append(f"Node {node.get('id', '<unknown>')} missing type")
            if node.get("type") == "agent" and not node.get("agentName"):
                errors.append(
                    f"Agent node {node.get('label') or node.get('id')} has no bound agent"
                )

        for edge in self.edges:
            source = edge.get("from")
            target = edge.get("to")
            if source not in self.node_map:
                errors.append(
                    f"Edge {edge.get('id')} references missing source node {source}"
                )
            if target not in self.node_map:
                errors.append(
                    f"Edge {edge.get('id')} references missing target node {target}"
                )
            if not edge.get("sourceHandle"):
                # Legacy edge; warning-like validation but not fatal.
                pass
            if not edge.get("targetHandle"):
                pass

        try:
            self.topological_sort()
        except ValueError as exc:
            errors.append(str(exc))
        return errors

    def predecessor_context_keys(self, node_id: str) -> List[str]:
        keys: List[str] = []
        for edge in self.incoming_edges(node_id, include_resources=False):
            source = self.node(str(edge.get("from")))
            if not source:
                continue
            source_name = (
                source.get("agentName") or source.get("label") or source.get("id")
            )
            keys.append(f"{source_name}_output")
        return keys
