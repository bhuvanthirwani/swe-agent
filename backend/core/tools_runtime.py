from typing import Callable, Dict, Any
from backend.core.database import get_db_connection

class ToolsRuntimeEngine:
    def __init__(self):
        self.registry: Dict[str, Callable] = {}
        # Register default tools here
        self._register_default_tools()

    def register_tool(self, name: str, func: Callable):
        self.registry[name] = func

    def _register_default_tools(self):
        # Example: sandbox code runner
        self.register_tool("run_code", self._run_code)
        # Example: read file
        self.register_tool("read_file", self._read_file)

    def execute_tool(self, tool_name: str, kwargs: Dict[str, Any], session_id: str = None, agent_run_id: int = None) -> Any:
        if tool_name not in self.registry:
            raise ValueError(f"Tool {tool_name} is not registered or not permitted for this agent.")
        output = None
        try:
            output = self.registry[tool_name](**kwargs)
            return output
        except Exception as e:
            output = f"Error executing tool {tool_name}: {str(e)}"
            return output
        finally:
            if session_id and agent_run_id:
                try:
                    conn = get_db_connection()
                    import json
                    conn.execute("INSERT INTO connector_executions (session_id, agent_run_id, connector_name, payload, output) VALUES (?, ?, ?, ?, ?)",
                        (session_id, agent_run_id, tool_name, json.dumps(kwargs), json.dumps(output))
                    )
                    conn.commit()
                    conn.close()
                except Exception as db_err:
                    print(f"Failed to log connector execution: {db_err}")

    def _run_code(self, code: str, language: str = "python") -> str:
        # Placeholder for sandboxed execution
        return f"Simulated output for running {language} code."

    def _read_file(self, filepath: str) -> str:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return str(e)
