import json
from backend.core.database import get_db_connection
from backend.core.tools_runtime import ToolsRuntimeEngine
from backend.core.providers import LLMProvider
from backend.models.interfaces import AgentConfig, LLMConfig, ToolConfig, AgentInput, AgentOutput

class UniversalAgentRuntime:
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.config = self._load_agent_config(agent_id)
        self.tools_engine = ToolsRuntimeEngine()
        
    def _load_agent_config(self, agent_id: int) -> AgentConfig:
        conn = get_db_connection()
        try:
            # Load agent details
            agent_row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
            if not agent_row:
                raise ValueError(f"Agent with ID {agent_id} not found.")
                
            # Load primary LLM
            llm_row = conn.execute('''
                SELECT l.id, l.model_name, l.api_key, p.name as provider_name, p.base_url 
                FROM llm_configs l
                JOIN agent_llms al ON l.id = al.llm_id
                JOIN llm_providers p ON l.provider_id = p.id
                WHERE al.agent_id = ? AND al.is_primary = 1
                LIMIT 1
            ''', (agent_id,)).fetchone()
            
            if not llm_row:
                raise ValueError(f"No primary LLM configured for agent {agent_id}.")
                
            # Load assigned tools
            tools_rows = conn.execute('''
                SELECT t.* FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = ?
            ''', (agent_id,)).fetchall()
            
            llm_config = LLMConfig(**dict(llm_row))
            tools = [ToolConfig(**dict(t)) for t in tools_rows]
            
            return AgentConfig(
                id=agent_row["id"],
                name=agent_row["name"],
                type=agent_row["type"],
                description=agent_row["description"],
                system_prompt=agent_row["system_prompt"],
                llm=llm_config,
                tools=tools
            )
        finally:
            conn.close()

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        user_prompt = json.dumps(input_data.input_context)
        print("Provider Details: ", self.config.llm.provider_name, self.config.llm.model_name, self.config.llm.api_key, self.config.llm.base_url)
        provider = LLMProvider(
            provider_name=self.config.llm.provider_name,
            model_name=self.config.llm.model_name,
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url
        )

        try:
            # Generate the response
            response_text = await provider.generate_sync(
                system_prompt=self.config.system_prompt,
                user_prompt=user_prompt
            )
            
            # The agent system_prompt typically requests JSON output
            # Clean up the markdown fences if any
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            
            try:
                result_data = json.loads(clean_text)
            except json.JSONDecodeError:
                result_data = {"raw_output": clean_text}
                
            return AgentOutput(
                status="success",
                output_result=result_data
            )
        except Exception as e:
            return AgentOutput(
                status="failed",
                output_result={"error": str(e)},
                error_logs=str(e)
            )
