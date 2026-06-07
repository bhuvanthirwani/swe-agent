import re
import os

with open('backend/core/pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_dag_func = '''async def execute_dag_pipeline(requirement: str, workflow_id: str, hitl_enabled: bool = False, session_id: str = None) -> AsyncGenerator[str, None]:
    """
    Executes a DAG pipeline by topologically sorting the nodes and yielding SSE events.
    """
    import uuid
    import time
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT nodes_json, edges_json FROM workflows WHERE id = ?", (workflow_id,))
        row = cursor.fetchone()
        if not row:
            yield f"data: {json.dumps({'type': 'error', 'error': f'Workflow {workflow_id} not found'})}\\n\\n"
            return
            
        nodes = json.loads(row['nodes_json'])
        edges = json.loads(row['edges_json'])
        
        cursor.execute("SELECT id, name, type FROM agents")
        agents = {r["name"]: {"id": r["id"], "type": r["type"]} for r in cursor.fetchall()}
        
        if not session_id:
            session_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO sessions (id, workflow_id, status) VALUES (?, ?, ?)", (session_id, workflow_id, 'running'))
            conn.commit()
            
    finally:
        conn.close()

    # Simple topological sort
    in_degree = {n['id']: 0 for n in nodes}
    adj = {n['id']: [] for n in nodes}
    node_map = {n['id']: n for n in nodes}
    
    for e in edges:
        if e['from'] in adj and e['to'] in in_degree:
            adj[e['from']].append(e['to'])
            in_degree[e['to']] += 1
            
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    sorted_nodes = []
    while queue:
        curr = queue.pop(0)
        sorted_nodes.append(node_map[curr])
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    context = {"requirement": requirement}
    
    for i, node in enumerate(sorted_nodes):
        if node.get('type') != 'agent':
            continue
            
        agent_name = node.get('agentName')
        agent_info = agents.get(agent_name)
        
        if not agent_info:
            yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'error': f'Agent {agent_name} not found'})}\\n\\n"
            return
            
        agent_id = agent_info["id"]
        agent_type = agent_info["type"]
        
        yield f"data: {json.dumps({'type': 'stage_start', 'stage': agent_name, 'agentName': agent_name, 'status': 'running'})}\\n\\n"
        
        start_time = time.time()
        runtime = UniversalAgentRuntime(agent_id=agent_id)
        
        # If the stage is generator, we stream the output
        if agent_type == 'generator' or agent_name == 'developer':
            print("Provider Details - Pipeline:", runtime.config.llm.provider_name, runtime.config.llm.model_name, runtime.config.llm.api_key, runtime.config.llm.base_url)
            provider = LLMProvider(
                provider_name=runtime.config.llm.provider_name,
                model_name=runtime.config.llm.model_name,
                api_key=runtime.config.llm.api_key,
                base_url=runtime.config.llm.base_url
            )
            
            user_prompt = json.dumps(context)
            yield f"data: {json.dumps({'type': 'stage_info', 'stage': agent_name, 'output': f'Starting generation for {agent_name}...'})}\\n\\n"
            
            output_content = ""
            try:
                async for token in provider.generate_stream(runtime.config.system_prompt, user_prompt):
                    output_content += token
                    yield f"data: {json.dumps({'type': 'stage_token', 'stage': agent_name, 'token': token})}\\n\\n"
                    import asyncio
                    await asyncio.sleep(0.01)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'agentName': agent_name, 'error': str(e)})}\\n\\n"
                return
                
            latency_ms = int((time.time() - start_time) * 1000)
            context[f"{agent_name}_output"] = output_content
            
            # Log to db
            db = get_db_connection()
            db.execute("INSERT INTO audit_logs (session_id, event_type, agent_name, input, output, tokens, latency) VALUES (?, ?, ?, ?, ?, ?, ?)", (session_id, 'stage_complete', agent_name, user_prompt, output_content, 0, latency_ms))
            db.execute("INSERT INTO agent_runs (session_id, agent_id, step_order, status, input_context, output_result) VALUES (?, ?, ?, ?, ?, ?)", (session_id, agent_id, i, 'success', user_prompt, output_content))
            db.commit()
            db.close()
            
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': agent_name, 'agentName': agent_name, 'output': output_content})}\\n\\n"
            
        else:
            # Sync execution for other agents
            input_data = AgentInput(task_id=0, agent_id=agent_id, input_context=context)
            result = await runtime.execute(input_data)
            latency_ms = int((time.time() - start_time) * 1000)
            
            if result.status == 'failed':
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'agentName': agent_name, 'error': result.output_result.get('error', 'Unknown error')})}\\n\\n"
                return
                
            output_text = json.dumps(result.output_result)
            context[f"{agent_name}_output"] = output_text
            
            # Log to db
            db = get_db_connection()
            db.execute("INSERT INTO audit_logs (session_id, event_type, agent_name, input, output, tokens, latency) VALUES (?, ?, ?, ?, ?, ?, ?)", (session_id, 'stage_complete', agent_name, json.dumps(context), output_text, 0, latency_ms))
            db.execute("INSERT INTO agent_runs (session_id, agent_id, step_order, status, input_context, output_result) VALUES (?, ?, ?, ?, ?, ?)", (session_id, agent_id, i, 'success', json.dumps(context), output_text))
            db.commit()
            db.close()
            
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': agent_name, 'agentName': agent_name, 'output': output_text})}\\n\\n"
            
        if hitl_enabled and agent_type == 'reviewer':
            checkpoint_id = str(uuid.uuid4())
            state_json = json.dumps({"context": context})
            db = get_db_connection()
            db.execute("INSERT INTO checkpoints (id, session_id, state_json) VALUES (?, ?, ?)", (checkpoint_id, session_id, state_json))
            db.execute("INSERT INTO hitl_requests (session_id, checkpoint_id, stage, status) VALUES (?, ?, ?, 'pending')", (session_id, checkpoint_id, agent_name))
            db.commit()
            db.close()
            yield f"data: {json.dumps({'type': 'hitl_request', 'stage': agent_name, 'checkpointId': checkpoint_id})}\\n\\n"
            # Pause execution, frontend will have to call resume endpoint
            return

    db = get_db_connection()
    db.execute("UPDATE sessions SET status = 'complete', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    db.commit()
    db.close()
    yield f"data: {json.dumps({'type': 'pipeline_complete'})}\\n\\n"
'''

import re
# Replace the old execute_dag_pipeline function with the new one
start_idx = content.find("async def execute_dag_pipeline")
if start_idx != -1:
    content = content[:start_idx] + new_dag_func
else:
    content += "\n" + new_dag_func

with open('backend/core/pipeline.py', 'w', encoding='utf-8') as f:
    f.write(content)
