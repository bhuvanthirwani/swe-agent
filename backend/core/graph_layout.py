from typing import Dict, List, Any
from collections import defaultdict, deque

def apply_auto_layout(workflow: Dict[str, Any]) -> Dict[str, Any]:
    nodes = workflow.get("nodes", [])
    edges = workflow.get("edges", [])
    
    if not nodes:
        return workflow

    # Build adjacency lists for execution edges only
    parents = defaultdict(list)
    children = defaultdict(list)
    
    for e in edges:
        if e.get('type') == 'control':
            src = e['source']
            tgt = e['target']
            parents[tgt].append(src)
            children[src].append(tgt)
            
    # Find roots
    entry_id = workflow.get("entry_node_id")
    roots = [n['id'] for n in nodes if not parents[n['id']]]
    if entry_id and entry_id in [n['id'] for n in nodes]:
        if entry_id not in roots:
            roots.append(entry_id)
    if not roots:
        roots = [nodes[0]['id']]
        
    layer_map = {}
    
    # Topological sort via Kahn's algorithm or longest path to root
    # To handle cycles (e.g. from condition back to loop), we need to ignore back edges.
    
    visited = set()
    def get_longest_path(node_id, path_set):
        if node_id in layer_map:
            return layer_map[node_id]
        if not parents[node_id]:
            return 0
            
        max_depth = 0
        for p in parents[node_id]:
            if p in path_set: # Cycle detected, ignore this back-edge
                continue
            depth = get_longest_path(p, path_set | {node_id})
            if depth > max_depth:
                max_depth = depth
                
        return max_depth + 1
        
    # Calculate layer for all nodes
    for n in nodes:
        nid = n['id']
        layer_map[nid] = get_longest_path(nid, {nid})
        
    # Handle resource nodes
    for e in edges:
        if e.get('type') != 'control':
            src = e['source']
            tgt = e['target']
            if tgt in layer_map and src not in layer_map:
                layer_map[src] = layer_map[tgt] + 0.5
                
    nodes_by_layer = defaultdict(list)
    for node_id, layer in layer_map.items():
        nodes_by_layer[layer].append(node_id)
        
    # Assign coordinates
    for layer, n_ids in nodes_by_layer.items():
        base_y = 50 + (layer * 180)
        width_per_node = 300
        total_width = len(n_ids) * width_per_node
        start_x = 400 - (total_width / 2) + (width_per_node / 2)
        
        for idx, n_id in enumerate(n_ids):
            node = next((n for n in nodes if n['id'] == n_id), None)
            if node:
                node['y'] = base_y
                node['x'] = start_x + (idx * width_per_node)
                
                if node.get('type') in ['model', 'tool', 'buffer_memory']:
                    node['x'] += 250
                    node['y'] -= 40
                    
    workflow['nodes'] = nodes
    return workflow
