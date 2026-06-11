import json
import os
import glob
from datetime import datetime
from backend.core.database import get_db_connection
from backend.core.tools_runtime import ToolsRuntimeEngine
from backend.core.providers import LLMProvider
from backend.models.interfaces import AgentConfig, LLMConfig, ToolConfig, AgentInput, AgentOutput

try:
    import jsonschema
except ImportError:
    jsonschema = None

# Base directory for all memory files
MEMORY_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class MemoryManager:
    """
    Manages file-based memory for agents.
    Files are stored at: data/{session_id}/{agent_name}/{memory_type}.txt
    """

    def __init__(self, session_id: str, agent_name: str):
        self.session_id = session_id
        self.agent_name = agent_name
        self.base_dir = os.path.join(MEMORY_DATA_DIR, session_id, agent_name)
        os.makedirs(self.base_dir, exist_ok=True)

    # ─── Buffer Memory ────────────────────────────────────────

    def get_buffer_memory_path(self) -> str:
        """Return path for the next buffer memory version file."""
        existing = sorted(glob.glob(os.path.join(self.base_dir, "buffer_memory_v*.txt")))
        version = len(existing) + 1
        return os.path.join(self.base_dir, f"buffer_memory_v{version}.txt")

    def read_all_buffer_memories(self) -> str:
        """Read and concatenate all buffer memory version files."""
        files = sorted(glob.glob(os.path.join(self.base_dir, "buffer_memory_v*.txt")))
        if not files:
            return ""
        chunks = []
        for f in files:
            with open(f, 'r', encoding='utf-8') as fh:
                chunks.append(f"[{os.path.basename(f)}]\n{fh.read()}")
        return "\n\n".join(chunks)

    def write_buffer_memory(self, content: str) -> str:
        """Write a new buffer memory version file."""
        path = self.get_buffer_memory_path()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    # ─── Summary Memory ───────────────────────────────────────

    def get_summary_memory_path(self) -> str:
        return os.path.join(self.base_dir, "summary_memory.txt")

    def read_summary_memory(self) -> str:
        path = self.get_summary_memory_path()
        if not os.path.exists(path):
            return ""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_summary_memory(self, content: str) -> str:
        path = self.get_summary_memory_path()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def append_summary_memory(self, content: str) -> str:
        path = self.get_summary_memory_path()
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n--- {datetime.utcnow().isoformat()}Z ---\n{content}")
        return path

    # ─── System Prompt Injection ──────────────────────────────

    def build_memory_system_prompt(self, memory_type: str) -> str:
        """
        Build the memory context block to inject into the system prompt.
        Returns an empty string if no memory files exist yet.
        """
        if memory_type == "Buffer Memory":
            content = self.read_all_buffer_memories()
            if not content:
                return (
                    "\n\n## Memory (Buffer)\n"
                    "No prior buffer memories found for this session. "
                    "After you produce your output, a buffer snapshot will be saved automatically.\n"
                )
            return (
                "\n\n## Memory (Buffer)\n"
                "The following is the running conversation buffer from this session. "
                "Use it to maintain continuity across steps.\n"
                f"```\n{content}\n```\n"
            )

        elif memory_type == "Summary Memory":
            content = self.read_summary_memory()
            if not content:
                return (
                    "\n\n## Memory (Summary)\n"
                    "No prior summary memory found for this session. "
                    "After you produce your output, a summary will be saved automatically.\n"
                )
            return (
                "\n\n## Memory (Summary)\n"
                "The following is the accumulated summary of this workflow session. "
                "Use it to stay aligned with the overall progress.\n"
                f"```\n{content}\n```\n"
            )

        elif memory_type == "Vector Store":
            # Vector store memory is read-only context; future: query ChromaDB here
            return (
                "\n\n## Memory (Vector Store / RAG)\n"
                "RAG retrieval is active. Relevant documents will be provided in the input context.\n"
            )

        return ""

    def persist_after_execution(self, memory_type: str, output_text: str):
        """
        Write memory files after the agent finishes executing.
        """
        if memory_type == "Buffer Memory":
            self.write_buffer_memory(output_text)
            print(f"[Memory] Buffer memory saved: {self.get_buffer_memory_path()}")

        elif memory_type == "Summary Memory":
            # Append a timestamped summary
            self.append_summary_memory(output_text)
            print(f"[Memory] Summary memory updated: {self.get_summary_memory_path()}")


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
            
            # Load output_schema from DB
            raw_schema = agent_row["output_schema"] if "output_schema" in agent_row.keys() else None
            output_schema = None
            if raw_schema:
                try:
                    output_schema = json.loads(raw_schema)
                except json.JSONDecodeError:
                    print(f"[Agent Runtime] Warning: invalid output_schema JSON for agent {agent_id}")

            return AgentConfig(
                id=agent_row["id"],
                name=agent_row["name"],
                type=agent_row["type"],
                description=agent_row["description"],
                system_prompt=agent_row["system_prompt"],
                llm=llm_config,
                tools=tools,
                output_schema=output_schema
            )
        finally:
            conn.close()

    async def execute(self, input_data: AgentInput) -> AgentOutput:
        user_prompt = json.dumps(input_data.input_context)
        
        node_config = input_data.node_config or {}
        session_id = input_data.session_id or "default"
        agent_name = node_config.get("agentName") or self.config.name
        
        # ─── 1. LLM Override ─────────────────────────────────
        model_name = self.config.llm.model_name
        provider_name = self.config.llm.provider_name
        
        chat_model = node_config.get("chatModel")
        if chat_model:
            model_name = chat_model
            if "llama" in model_name.lower() or "qwen" in model_name.lower():
                provider_name = "groq"
            elif "gpt" in model_name.lower():
                provider_name = "openai"
            elif "claude" in model_name.lower():
                provider_name = "anthropic"

        print(f"[Agent Runtime] Provider: {provider_name}, Model: {model_name}")
        provider = LLMProvider(
            provider_name=provider_name,
            model_name=model_name,
            api_key=self.config.llm.api_key,
            base_url=self.config.llm.base_url
        )

        # ─── 2. Memory Injection (into System Prompt) ────────
        system_prompt = self.config.system_prompt
        memory_type = node_config.get("memory")
        memory_manager = None

        if memory_type:
            memory_manager = MemoryManager(session_id=session_id, agent_name=agent_name)
            memory_block = memory_manager.build_memory_system_prompt(memory_type)
            system_prompt += memory_block
            print(f"[Agent Runtime] Memory ({memory_type}) injected for {agent_name} in session {session_id}")

        # ─── 3. Tool Schema Injection (into System Prompt) ───
        tools_config = node_config.get("tools") or []
        if tools_config:
            schemas = self.tools_engine.get_schemas_for_tools(tools_config)
            tools_desc = json.dumps(schemas, indent=2)
            system_prompt += (
                f"\n\n## Available Tools\n"
                f"You have the following tools available. To call a tool, respond with a JSON object "
                f'containing "tool_name" (string) and "kwargs" (object).\n'
                f"```json\n{tools_desc}\n```\n"
                f"After you receive a tool result, incorporate it into your final answer.\n"
            )

        # ─── 4. File workspace info ──────────────────────────
        workspace_dir = os.path.join(MEMORY_DATA_DIR, session_id, agent_name)
        system_prompt += (
            f"\n\n## File Workspace\n"
            f"Your file workspace is: {workspace_dir}\n"
            f"You can use create_file, edit_file, delete_file, read_file, and list_files tools "
            f"to manage files in this directory.\n"
        )

        try:
            # Generate the response
            response_text = await provider.generate_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # Clean up markdown fences
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            
            try:
                result_data = json.loads(clean_text)
                
                # Execute tool call if the LLM requested one
                if "tool_name" in result_data and "kwargs" in result_data:
                    tool_output = self.tools_engine.execute_tool(
                        tool_name=result_data["tool_name"],
                        kwargs=result_data["kwargs"],
                        session_id=session_id
                    )
                    result_data["tool_execution_result"] = tool_output
                    print(f"[Agent Runtime] Tool executed: {result_data['tool_name']} → {tool_output[:200] if isinstance(tool_output, str) else tool_output}")
                
                # Validate output against DB-stored JSON Schema
                if self.config.output_schema and jsonschema:
                    try:
                        jsonschema.validate(instance=result_data, schema=self.config.output_schema)
                        print(f"[Agent Runtime] Output validated against DB schema for '{self.config.name}'")
                    except jsonschema.ValidationError as ve:
                        print(f"[Agent Runtime] Schema validation warning for '{self.config.name}': {ve.message}")
                elif self.config.output_schema and not jsonschema:
                    print(f"[Agent Runtime] jsonschema package not installed — skipping validation for '{self.config.name}'")
                    
            except json.JSONDecodeError:
                result_data = {"raw_output": clean_text}

            # ─── 5. Persist Memory After Execution ───────────
            if memory_manager and memory_type:
                output_text = clean_text[:2000]  # Cap memory snapshots
                memory_manager.persist_after_execution(memory_type, output_text)
                
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
