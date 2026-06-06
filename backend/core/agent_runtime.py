import json
from backend.core.database import get_db_connection
from backend.core.tools_runtime import ToolsRuntimeEngine
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
                SELECT l.* FROM llm_configs l
                JOIN agent_llms al ON l.id = al.llm_id
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
        # Construct the prompt with the system_prompt and input context
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": json.dumps(input_data.input_context)}
        ]
        
        # In a real implementation, you would dynamically call the LLM based on self.config.llm
        # using httpx to self.config.llm.base_url with self.config.llm.api_key.
        
        # Simulated LLM response
        simulated_response = {
            "thought": f"I am {self.config.name}. Executing task {input_data.task_id}.",
            "action": "completed",
            "result": {"status": "ok"}
        }
        
        return AgentOutput(
            status="success",
            output_result=simulated_response
        )
