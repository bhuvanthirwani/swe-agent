from typing import Dict, Any, List

def compute_graph_deltas(old_workflow: Dict[str, Any], new_workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compares two DAGWorkflows and emits a list of ops:
    add_node, remove_node, update_node, add_edge, remove_edge
    """
    deltas = []
    
    old_nodes = {n['id']: n for n in old_workflow.get('nodes', [])}
    new_nodes = {n['id']: n for n in new_workflow.get('nodes', [])}
    
    old_edges = {e['id']: e for e in old_workflow.get('edges', [])}
    new_edges = {e['id']: e for e in new_workflow.get('edges', [])}
    
    # 1. Removed nodes
    for nid in old_nodes:
        if nid not in new_nodes:
            deltas.append({"type": "graph_delta", "op": "remove_node", "payload": {"id": nid}})
            
    # 2. Added & Updated nodes
    for nid, node in new_nodes.items():
        if nid not in old_nodes:
            deltas.append({"type": "graph_delta", "op": "add_node", "payload": node})
        else:
            # Simple check to see if node changed
            if old_nodes[nid] != node:
                deltas.append({"type": "graph_delta", "op": "update_node", "payload": node})
                
    # 3. Removed edges
    for eid in old_edges:
        if eid not in new_edges:
            deltas.append({"type": "graph_delta", "op": "remove_edge", "payload": {"id": eid}})
            
    # 4. Added edges
    for eid, edge in new_edges.items():
        if eid not in old_edges:
            deltas.append({"type": "graph_delta", "op": "add_edge", "payload": edge})
            
    return deltas
