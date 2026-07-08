import json
import asyncio
from typing import AsyncGenerator
from backend.core.database import get_db_connection
from backend.core.agent_runtime import UniversalAgentRuntime
from backend.models.interfaces import AgentInput
from backend.core.providers import LLMProvider

async def execute_linear_pipeline(requirement: str, hitl_enabled: bool = False) -> AsyncGenerator[str, None]:
    """
    Executes a linear agentic pipeline (Requirements -> Planner -> Developer -> Reviewer),
    yielding SSE events matching the frontend's expectations.
    """
    conn = get_db_connection()
    try:
        # Get all agents
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM agents")
        agents = {row["name"]: row["id"] for row in cursor.fetchall()}
    finally:
        conn.close()

    context = {"requirement": requirement}
    stages = [
        ("requirements", "requirements-analyst"),
        ("planning", "task-planner"),
        ("code", "developer"),
        ("review", "code-reviewer")
    ]

    for stage_name, agent_name in stages:
        agent_id = agents.get(agent_name)
        if not agent_id:
            yield f"data: {json.dumps({'type': 'stage_error', 'stage': stage_name, 'error': f'Agent {agent_name} not found'})}\n\n"
            return
            
        yield f"data: {json.dumps({'type': 'stage_start', 'stage': stage_name, 'agentName': agent_name, 'status': 'running'})}\n\n"
        
        runtime = UniversalAgentRuntime(agent_id=agent_id)
        
        # Inject Resource Overrides
        if model_override:
            runtime.config.llm.model_name = model_override
            # Simple heuristic for provider if needed, assuming standard setup
            if 'qwen' in model_override.lower():
                runtime.config.llm.provider_name = 'together'
            elif 'llama' in model_override.lower():
                runtime.config.llm.provider_name = 'groq'
            elif 'gpt' in model_override.lower():
                runtime.config.llm.provider_name = 'openai'
                
        if connected_tools:
            runtime.config.tools.extend(connected_tools)
            runtime.config.tools = list(set(runtime.config.tools)) # dedup
            
        if memory_override:
            # We can pass memory_override to input_data if needed, but for now we'll set it loosely on config
            setattr(runtime.config, 'memory_config', memory_override)

        print("Provider Details - Pipeline: ", runtime.config.llm.provider_name, runtime.config.llm.model_name, runtime.config.llm.api_key, runtime.config.llm.base_url)
        # If the stage is developer, we stream the output
        if stage_name == 'code':
            provider = LLMProvider(
                provider_name=runtime.config.llm.provider_name,
                model_name=runtime.config.llm.model_name,
                api_key=runtime.config.llm.api_key,
                base_url=runtime.config.llm.base_url
            )
            
            user_prompt = json.dumps(context)
            yield f"data: {json.dumps({'type': 'stage_info', 'stage': stage_name, 'output': 'Starting code generation...'})}\n\n"
            
            output_content = ""
            try:
                async for token in provider.generate_stream(runtime.config.system_prompt, user_prompt):
                    output_content += token
                    yield f"data: {json.dumps({'type': 'stage_token', 'stage': stage_name, 'token': token})}\n\n"
                    await asyncio.sleep(0.01)  # small yield to event loop
            except Exception as e:
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': stage_name, 'error': str(e)})}\n\n"
                return
                
            context[f"{stage_name}_output"] = output_content
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': stage_name, 'output': 'Code generation complete.'})}\n\n"
            
        else:
            # Sync execution for other agents
            input_data = AgentInput(task_id=0, agent_id=agent_id, input_context=context)
            result = await runtime.execute(input_data)
            
            if result.status == 'failed':
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': stage_name, 'error': result.output_result.get('error', 'Unknown error')})}\n\n"
                return
                
            output_text = json.dumps(result.output_result)
            context[f"{stage_name}_output"] = output_text
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': stage_name, 'output': output_text})}\n\n"
            
        # HITL Pause Check
        if hitl_enabled and stage_name == 'review':
            yield f"data: {json.dumps({'type': 'hitl_request', 'stage': stage_name})}\n\n"
            # Here we just wait for a HITL resume which would be handled differently
            # In a real implementation we'd pause and wait for an API call to resume
            pass

    yield f"data: {json.dumps({'type': 'pipeline_complete'})}\n\n"

async def execute_dag_pipeline(requirement: str, workflow_id: str, hitl_enabled: bool = False, session_id: str = None) -> AsyncGenerator[str, None]:
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
            yield f"data: {json.dumps({'type': 'error', 'error': f'Workflow {workflow_id} not found'})}\n\n"
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

    node_map = {n['id']: n for n in nodes}
    
    # Calculate in_degrees based on data/control edges to find initial starting nodes
    # Only count edges from other *agents* (not components/resources like memory)
    in_degree = {n['id']: 0 for n in nodes if n.get('type') == 'agent'}
    
    for e in edges:
        from_node = node_map.get(e['from'])
        to_node = node_map.get(e['to'])
        if from_node and to_node and from_node.get('type') == 'agent' and to_node.get('type') == 'agent':
            in_degree[e['to']] = in_degree.get(e['to'], 0) + 1

    start_nodes = [nid for nid, deg in in_degree.items() if deg == 0]
    if not start_nodes and in_degree:
        # Fallback if there's a pure cycle and no entry point
        start_nodes = [list(in_degree.keys())[0]]

    active_queue = start_nodes.copy()
    node_execution_counts = {n['id']: 0 for n in nodes if n.get('type') == 'agent'}
    MAX_LOOPS = 5

    context = {"requirement": requirement, "global_state": {}}
    global_graph = {"nodes": nodes, "edges": edges}
    
    i = 0
    while active_queue:
        node_id = active_queue.pop(0)
        node = node_map.get(node_id)
        if not node:
            continue
            
        node_execution_counts[node_id] += 1
        if node_execution_counts[node_id] > MAX_LOOPS:
            yield f"data: {json.dumps({'type': 'stage_error', 'stage': node.get('agentName', node_id), 'error': f'Max loops ({MAX_LOOPS}) exceeded'})}\n\n"
            break
            
        i += 1
        if node.get('type') not in ['agent', 'subworkflow', 'condition']:
            continue
            
        if node.get('type') == 'subworkflow':
            target_workflow_id = node.get('config', {}).get('targetWorkflowId')
            node_name = f"subworkflow_{node['id']}"
            if not target_workflow_id:
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': node_name, 'error': 'No target workflow ID specified'})}\n\n"
                continue
                
            db = get_db_connection()
            target_wf = db.execute("SELECT nodes_json, edges_json FROM workflows WHERE id = ?", (target_workflow_id,)).fetchone()
            db.close()
            
            if not target_wf:
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': node_name, 'error': f'Target workflow {target_workflow_id} not found'})}\n\n"
                continue
                
            yield f"data: {json.dumps({'type': 'stage_info', 'stage': node_name, 'output': f'Executing Sub-Workflow {target_workflow_id}...'})}\n\n"
            
            sub_nodes = json.loads(target_wf['nodes_json'])
            sub_edges = json.loads(target_wf['edges_json'])
            
            # Subworkflows run completely independently right now and we capture their output
            # For a proper subworkflow we'd wait for it to finish and get the last agent's output
            # To keep it simple, we just yield info.
            context[f"{node_name}_output"] = {"status": "subworkflow_executed", "workflow_id": target_workflow_id}
            
            # Push connected edges
            for edge in edges:
                if edge['from'] == node['id']:
                    target_node = node_map.get(edge['to'])
                    if target_node and target_node.get('type') in ['agent', 'subworkflow', 'condition']:
                        if target_node['id'] not in active_queue:
                            active_queue.append(target_node['id'])
            continue
            
        if node.get('type') == 'condition':
            node_name = f"condition_{node['id']}"
            config = node.get('config', {})
            expression = config.get('expression', 'false')
            
            # Simple eval sandbox
            # Inject context
            eval_env = {"context": context}
            
            yield f"data: {json.dumps({'type': 'stage_info', 'stage': node_name, 'output': f'Evaluating Condition...'})}\n\n"
            
            try:
                # DANGEROUS but this is a local IDE / trusted execution context
                result = eval(expression, {"__builtins__": {}}, eval_env)
            except Exception as e:
                result = False
                
            context[f"{node_name}_output"] = {"condition_result": bool(result)}
            
            # Push edges ONLY if they match the result boolean path
            for edge in edges:
                if edge['from'] == node['id']:
                    target_node = node_map.get(edge['to'])
                    if target_node and target_node.get('type') in ['agent', 'subworkflow', 'condition']:
                        # Conditional edge routing based on label
                        if (result and edge.get('label') == 'True') or (not result and edge.get('label') == 'False'):
                            if target_node['id'] not in active_queue:
                                active_queue.append(target_node['id'])
            continue
        agent_name = node.get('agentName')
        agent_info = agents.get(agent_name)
        
        if not agent_info:
            yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'error': f'Agent {agent_name} not found'})}\n\n"
            return
            
        agent_id = agent_info["id"]
        agent_type = agent_info["type"]
        

        # Check for connected resources (models, tools, memory)
        connected_tools = []
        model_override = None
        memory_override = None

        for edge in edges:
            if edge['to'] == node['id']:
                src_node = node_map.get(edge['from'])
                if not src_node: continue
                if edge.get('type') == 'model':
                    model_override = src_node.get('config', {}).get('modelName')
                elif edge.get('type') == 'tool':
                    tool_name = src_node.get('config', {}).get('toolName')
                    if tool_name: connected_tools.append(tool_name)
                elif edge.get('type') == 'memory':
                    memory_override = src_node.get('config', {})

        # Collect dynamic inputs for this agent based on incoming edges
        dynamic_inputs = {}
        for edge in edges:
            if edge['to'] == node['id'] and edge.get('targetHandle', '').startswith('custom.input.'):
                source_node = node_map[edge['from']]
                source_agent_name = source_node.get('agentName', source_node.get('id'))
                source_data = context.get(f"{source_agent_name}_output", "")
                
                input_name = edge['targetHandle'].split('custom.input.')[-1]
                
                if edge.get('sourceHandle', '').startswith('custom.output.'):
                    output_name = edge['sourceHandle'].split('custom.output.')[-1]
                    if isinstance(source_data, dict):
                        dynamic_inputs[input_name] = source_data.get(output_name)
                    else:
                        try:
                            parsed_data = json.loads(source_data)
                            dynamic_inputs[input_name] = parsed_data.get(output_name)
                        except (json.JSONDecodeError, TypeError):
                            dynamic_inputs[input_name] = source_data
                else:
                    dynamic_inputs[input_name] = source_data

        agent_context = {
            **context,
            **dynamic_inputs
        }
        
db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("INSERT INTO agent_runs (session_id, agent_id, step_order, status, input_context) VALUES (?, ?, ?, 'running', ?)", (session_id, agent_id, i, json.dumps(agent_context)))
        agent_run_id = cursor.lastrowid
        db.commit()
        db.close()

        yield f"data: {json.dumps({'type': 'stage_start', 'stage': agent_name, 'agentName': agent_name, 'status': 'running'})}\n\n"
        
        start_time = time.time()
        runtime = UniversalAgentRuntime(agent_id=agent_id)
        
        # Inject Resource Overrides
        if model_override:
            runtime.config.llm.model_name = model_override
            # Simple heuristic for provider if needed, assuming standard setup
            if 'qwen' in model_override.lower():
                runtime.config.llm.provider_name = 'together'
            elif 'llama' in model_override.lower():
                runtime.config.llm.provider_name = 'groq'
            elif 'gpt' in model_override.lower():
                runtime.config.llm.provider_name = 'openai'
                
        if connected_tools:
            runtime.config.tools.extend(connected_tools)
            runtime.config.tools = list(set(runtime.config.tools)) # dedup
            
        if memory_override:
            # We can pass memory_override to input_data if needed, but for now we'll set it loosely on config
            setattr(runtime.config, 'memory_config', memory_override)

        
        # If the stage is generator, we stream the output
        if agent_type == 'generator' or agent_name == 'developer':
            print("Provider Details - Pipeline:", runtime.config.llm.provider_name, runtime.config.llm.model_name, runtime.config.llm.api_key, runtime.config.llm.base_url)
            provider = LLMProvider(
                provider_name=runtime.config.llm.provider_name,
                model_name=runtime.config.llm.model_name,
                api_key=runtime.config.llm.api_key,
                base_url=runtime.config.llm.base_url
            )
            system_prompt = runtime.config.system_prompt
            system_prompt += f"\n\n## Workflow Architecture\nHere is the full architecture of the workflow you are part of:\n```json\n{json.dumps(global_graph, indent=2)}\n```\n"
            system_prompt += f"You are currently executing as Node `{agent_name}`.\n"
            if dynamic_inputs:
                system_prompt += f"You are receiving the following dynamic inputs: {list(dynamic_inputs.keys())}.\n"
            
            user_prompt = json.dumps(agent_context)
            yield f"data: {json.dumps({'type': 'stage_info', 'stage': agent_name, 'output': f'Starting generation for {agent_name}...'})}\n\n"
            
            output_content = ""
            try:
                async for token in provider.generate_stream(system_prompt, user_prompt):
                    output_content += token
                    yield f"data: {json.dumps({'type': 'stage_token', 'stage': agent_name, 'token': token})}\n\n"
                    import asyncio
                    await asyncio.sleep(0.01)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'agentName': agent_name, 'error': str(e)})}\n\n"
                return
                
            latency_ms = int((time.time() - start_time) * 1000)
            context[f"{agent_name}_output"] = output_content
            
            # Log to db
            db = get_db_connection()
            db.execute("INSERT INTO audit_logs (session_id, event_type, agent_name, input, output, tokens, latency) VALUES (?, ?, ?, ?, ?, ?, ?)", (session_id, 'stage_complete', agent_name, user_prompt, output_content, 0, latency_ms))
            db.execute("UPDATE agent_runs SET status = 'success', output_result = ? WHERE id = ?", (output_content, agent_run_id))
            db.commit()
            db.close()
            
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': agent_name, 'agentName': agent_name, 'output': output_content})}\n\n"
            
        else:
            # Sync execution for other agents
            run_per_item = node.get('config', {}).get('runPerItem', False)
            list_keys = [k for k, v in dynamic_inputs.items() if isinstance(v, list)]
            
            if run_per_item and list_keys:
                list_key = list_keys[0]
                items = dynamic_inputs[list_key]
                yield f"data: {json.dumps({'type': 'stage_info', 'stage': agent_name, 'output': f'Starting Map-Reduce for {len(items)} items on {list_key}...'})}\n\n"
                
                aggregated_results = []
                for item in items:
                    item_dynamic_inputs = dynamic_inputs.copy()
                    item_dynamic_inputs[list_key] = item
                    item_agent_context = {**context, **item_dynamic_inputs}
                    
                    input_data = AgentInput(
                        task_id=0, agent_id=agent_id, input_context=item_agent_context, agent_run_id=agent_run_id,
                        node_config=node, session_id=session_id, global_graph=global_graph,
                        dynamic_inputs=item_dynamic_inputs
                    )
                    result = await runtime.execute(input_data)
                    if result.status == 'success':
                        aggregated_results.append(result.output_result)
                    else:
                        aggregated_results.append({"error": result.output_result.get('error', 'Unknown error')})
                        
                latency_ms = int((time.time() - start_time) * 1000)
                output_text = json.dumps({"map_results": aggregated_results})
            else:
                input_data = AgentInput(
                    task_id=0, agent_id=agent_id, input_context=agent_context, agent_run_id=agent_run_id,
                    node_config=node, session_id=session_id, global_graph=global_graph,
                    dynamic_inputs=dynamic_inputs
                )
                result = await runtime.execute(input_data)
                latency_ms = int((time.time() - start_time) * 1000)
                
                if result.status == 'failed':
                    yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'agentName': agent_name, 'error': result.output_result.get('error', 'Unknown error')})}\n\n"
                    return
                output_text = json.dumps(result.output_result)

            context[f"{agent_name}_output"] = output_text
            
            # Log to db
            db = get_db_connection()
            db.execute("INSERT INTO audit_logs (session_id, event_type, agent_name, input, output, tokens, latency) VALUES (?, ?, ?, ?, ?, ?, ?)", (session_id, 'stage_complete', agent_name, json.dumps(context), output_text, 0, latency_ms))
            db.execute("UPDATE agent_runs SET status = 'success', output_result = ? WHERE id = ?", (output_text, agent_run_id))
            db.commit()
            db.close()
            
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': agent_name, 'agentName': agent_name, 'output': output_text})}\n\n"
            
        # --- Active Edge Resolution ---
        output_result = None
        output_text_for_parsing = context.get(f"{agent_name}_output", "")
        if agent_type == 'generator' or agent_name == 'developer':
            try:
                output_result = json.loads(output_text_for_parsing)
            except:
                output_result = {"raw": output_text_for_parsing}
        else:
            try:
                output_result = json.loads(output_text_for_parsing)
            except:
                output_result = {"raw": output_text_for_parsing}

        # --- Global State Updates ---
        if isinstance(output_result, dict) and "_global_state_updates" in output_result:
            if isinstance(output_result["_global_state_updates"], dict):
                context["global_state"].update(output_result["_global_state_updates"])

        for edge in edges:
            if edge['from'] == node['id']:
                target_node = node_map.get(edge['to'])
                if not target_node or target_node.get('type') not in ['agent', 'subworkflow', 'condition']:
                    continue
                
                # If it's a standard control flow edge, activate unconditionally
                if not edge.get('sourceHandle', '').startswith('custom.output.'):
                    active_queue.append(target_node['id'])
                else:
                    # Dynamic output edge: check if the key exists in output JSON and is not false/null
                    output_key = edge['sourceHandle'].split('custom.output.')[-1]
                    if isinstance(output_result, dict):
                        val = output_result.get(output_key)
                        if val is not None and val is not False and val != "":
                            active_queue.append(target_node['id'])
            
        require_human_approval = node.get('config', {}).get('requireHumanApproval', False)
        if require_human_approval or (hitl_enabled and agent_type == 'reviewer'):
            checkpoint_id = str(uuid.uuid4())
            state_json = json.dumps({"context": context})
            db = get_db_connection()
            db.execute("INSERT INTO checkpoints (id, session_id, state_json) VALUES (?, ?, ?)", (checkpoint_id, session_id, state_json))
            try:
                db.execute("INSERT INTO hitl_requests (session_id, checkpoint_id, stage, status) VALUES (?, ?, ?, 'pending')", (session_id, checkpoint_id, agent_name))
            except Exception as e:
                pass # schema variation safe-guard
            db.commit()
            db.close()
            yield f"data: {json.dumps({'type': 'hitl_request', 'stage': agent_name, 'checkpointId': checkpoint_id})}\n\n"
            # Pause execution, frontend will have to call resume endpoint
            return

    db = get_db_connection()
    db.execute("UPDATE sessions SET status = 'complete', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    db.commit()
    db.close()
    yield f"data: {json.dumps({'type': 'pipeline_complete'})}\n\n"
