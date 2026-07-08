import json
from backend.core.providers import LLMProvider
from backend.core.database import get_db_connection
from backend.core.flow_architect_prompt import FLOW_ARCHITECT_SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
from backend.core.graph_layout import apply_auto_layout

class FlowArchitectService:
    def __init__(self):
        from backend.core.database import get_db_connection
        conn = get_db_connection()
        try:
            row = conn.execute("SELECT metadata FROM service_integrations WHERE service_name = 'ai_architect'").fetchone()
            if not row:
                raise ValueError("AI Architect model not configured. Please select a model in Settings.")
            import json
            meta = json.loads(row['metadata'])
            llm_id = meta.get('llm_config_id')
            if not llm_id:
                raise ValueError("AI Architect model not configured. Please select a model in Settings.")
                
            llm_row = conn.execute("SELECT * FROM llm_configs WHERE id = ?", (llm_id,)).fetchone()
            if not llm_row:
                raise ValueError("AI Architect model configuration not found. Please reselect in Settings.")
                
            provider_row = conn.execute("SELECT name FROM llm_providers WHERE id = ?", (llm_row['provider_id'],)).fetchone()
            provider_name = provider_row['name'] if provider_row else "groq"
                
            self.provider = LLMProvider(
                provider_name=provider_name,
                model_name=llm_row['model_name'],
                api_key=llm_row.get('api_key'),
                base_url=None
            )
        finally:
            conn.close()
        
    def _get_agent_catalog(self):
        conn = get_db_connection()
        try:
            agents = conn.execute("SELECT id, name, type, description FROM agents").fetchall()
            return json.dumps([dict(a) for a in agents], indent=2)
        finally:
            conn.close()

    async def generate_workflow(self, user_prompt: str, session_id: str):
        """
        Phase 2: One-shot graph generation based on user prompt.
        """
        agents_catalog = self._get_agent_catalog()
        system_prompt = FLOW_ARCHITECT_SYSTEM_PROMPT.replace("{agents_catalog}", agents_catalog)
        system_prompt += f"\n\n## Examples\n{FEW_SHOT_EXAMPLES}"

        if current_workflow:
            system_prompt += f"\n\n## Current Workflow\nThe user is asking you to modify the following workflow. Emit the FULL updated workflow JSON, maintaining existing IDs where possible.\n```json\n{json.dumps(current_workflow)}\n```\n"

        
        try:
            # 1. Ask LLM to generate the JSON representation
            response_text = await self.provider.generate_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            workflow_data = json.loads(clean_text)
            
            # 2. Apply auto-layout for coordinates
            workflow_data = apply_auto_layout(workflow_data)
            
            # 3. Simple ID assignments for frontend
            if "id" not in workflow_data:
                workflow_data["id"] = f"wf-{session_id}"
                
            return {
                "status": "success",
                "workflow": workflow_data,
                "reasoning": workflow_data.get("reasoning", "Generated workflow.")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def generate_workflow_stream(self, user_prompt: str, session_id: str, current_workflow: dict = None):
        agents_catalog = self._get_agent_catalog()
        system_prompt = FLOW_ARCHITECT_SYSTEM_PROMPT.replace("{agents_catalog}", agents_catalog)
        system_prompt += f"\n\n## Examples\n{FEW_SHOT_EXAMPLES}"

        if current_workflow:
            system_prompt += f"\n\n## Current Workflow\nThe user is asking you to modify the following workflow. Emit the FULL updated workflow JSON, maintaining existing IDs where possible.\n```json\n{json.dumps(current_workflow)}\n```\n"

        
        try:
            is_thinking = False
            is_json = False
            json_buffer = ""
            thought_buffer = ""
            
            async for token in self.provider.generate_stream(system_prompt=system_prompt, user_prompt=user_prompt):
                if "<thinking>" in token:
                    is_thinking = True
                    token = token.replace("<thinking>", "")
                if "</thinking>" in token:
                    is_thinking = False
                    token = token.replace("</thinking>", "")
                    yield {"type": "assistant_message_complete"}
                    is_json = True
                    continue
                    
                if is_thinking and token.strip():
                    yield {"type": "assistant_token", "token": token}
                    
                if is_json:
                    json_buffer += token
                    
            if not json_buffer:
                json_buffer = thought_buffer # fallback if LLM didn't use tags
                
            clean_text = json_buffer.replace("```json", "").replace("```", "").strip()
            # find first {
            if "{" in clean_text:
                clean_text = clean_text[clean_text.find("{"):]
            
            import json
            workflow_data = json.loads(clean_text)
            
            # Dynamic Agent Creation
            new_agents = workflow_data.get("new_agents", [])
            if new_agents:
                from backend.core.database import get_db_connection
                conn = get_db_connection()
                try:
                    for agent in new_agents:
                        # Yield a notification to the chat
                        yield {"type": "assistant_token", "token": f"\n\n*Created new agent: {agent.get('name')}*"}
                        
                        conn.execute(
                            "INSERT OR IGNORE INTO agents (name, type, description, system_prompt) VALUES (?, ?, ?, ?)",
                            (agent.get("name"), agent.get("type", "generator"), agent.get("description", ""), agent.get("system_prompt", ""))
                        )
                    conn.commit()
                except Exception as e:
                    print(f"Failed to insert new agents: {e}")
                finally:
                    conn.close()
            
            workflow_data = apply_auto_layout(workflow_data)
            
            if "id" not in workflow_data:
                workflow_data["id"] = f"wf-{session_id}"
                
            import asyncio
            from backend.core.graph_patcher import compute_graph_deltas
            
            if current_workflow:
                deltas = compute_graph_deltas(current_workflow, workflow_data)
                for delta in deltas:
                    yield delta
                    await asyncio.sleep(0.1)
            else:
                for node in workflow_data.get("nodes", []):
                    yield {"type": "graph_delta", "op": "add_node", "payload": node}
                    await asyncio.sleep(0.15)
                for edge in workflow_data.get("edges", []):
                    yield {"type": "graph_delta", "op": "add_edge", "payload": edge}
                    await asyncio.sleep(0.05)
                
            yield {
                "type": "workflow_proposal",
                "workflow": workflow_data,
                "validationStatus": "valid"
            }
            
        except Exception as e:
            yield {
                "type": "validation_result",
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
