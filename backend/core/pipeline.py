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

async def execute_dag_pipeline(requirement: str, workflow_id: str, hitl_enabled: bool = False) -> AsyncGenerator[str, None]:
    """
    Executes a DAG pipeline by topologically sorting the nodes and yielding SSE events.
    """
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
    
    for node in sorted_nodes:
        if node.get('type') != 'agent':
            continue
            
        agent_name = node.get('agentName')
        agent_info = agents.get(agent_name)
        
        if not agent_info:
            yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'error': f'Agent {agent_name} not found'})}\n\n"
            return
            
        agent_id = agent_info["id"]
        agent_type = agent_info["type"]
        
        yield f"data: {json.dumps({'type': 'stage_start', 'stage': agent_name, 'agentName': agent_name, 'status': 'running'})}\n\n"
        
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
            yield f"data: {json.dumps({'type': 'stage_info', 'stage': agent_name, 'output': f'Starting generation for {agent_name}...'})}\n\n"
            
            output_content = ""
            try:
                async for token in provider.generate_stream(runtime.config.system_prompt, user_prompt):
                    output_content += token
                    yield f"data: {json.dumps({'type': 'stage_token', 'stage': agent_name, 'token': token})}\n\n"
                    await asyncio.sleep(0.01)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'error': str(e)})}\n\n"
                return
                
            context[f"{agent_name}_output"] = output_content
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': agent_name, 'output': 'Generation complete.'})}\n\n"
            
        else:
            # Sync execution for other agents
            input_data = AgentInput(task_id=0, agent_id=agent_id, input_context=context)
            result = await runtime.execute(input_data)
            
            if result.status == 'failed':
                yield f"data: {json.dumps({'type': 'stage_error', 'stage': agent_name, 'error': result.output_result.get('error', 'Unknown error')})}\n\n"
                return
                
            output_text = json.dumps(result.output_result)
            context[f"{agent_name}_output"] = output_text
            yield f"data: {json.dumps({'type': 'stage_complete', 'stage': agent_name, 'output': output_text})}\n\n"
            
        if hitl_enabled and agent_type == 'reviewer':
            yield f"data: {json.dumps({'type': 'hitl_request', 'stage': agent_name})}\n\n"

    yield f"data: {json.dumps({'type': 'pipeline_complete'})}\n\n"
