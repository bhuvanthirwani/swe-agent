import os
import glob
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
        self.register_tool("run_code", self._run_code)
        self.register_tool("read_file", self._read_file)
        self.register_tool("create_file", self._create_file)
        self.register_tool("edit_file", self._edit_file)
        self.register_tool("delete_file", self._delete_file)
        self.register_tool("list_files", self._list_files)

    def get_tool_schemas(self) -> list:
        """Return OpenAI-style function schemas for all registered tools."""
        schemas = {
            "run_code": {
                "name": "run_code",
                "description": "Execute code in a sandboxed environment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "The code to execute."},
                        "language": {"type": "string", "description": "Programming language (default: python)."}
                    },
                    "required": ["code"]
                }
            },
            "read_file": {
                "name": "read_file",
                "description": "Read the contents of a file at the given filepath.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Path to the file to read."}
                    },
                    "required": ["filepath"]
                }
            },
            "create_file": {
                "name": "create_file",
                "description": "Create a new file with the given content. Parent directories are created automatically.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Path where the file should be created."},
                        "content": {"type": "string", "description": "Content to write into the file."}
                    },
                    "required": ["filepath", "content"]
                }
            },
            "edit_file": {
                "name": "edit_file",
                "description": "Overwrite or append content to an existing file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Path to the file to edit."},
                        "content": {"type": "string", "description": "New content to write."},
                        "mode": {"type": "string", "description": "'overwrite' to replace contents, 'append' to add to end. Default: overwrite."}
                    },
                    "required": ["filepath", "content"]
                }
            },
            "delete_file": {
                "name": "delete_file",
                "description": "Delete a file at the given filepath.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Path to the file to delete."}
                    },
                    "required": ["filepath"]
                }
            },
            "list_files": {
                "name": "list_files",
                "description": "List all files in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Path to the directory to list."}
                    },
                    "required": ["directory"]
                }
            },
        }
        return [schemas[name] for name in self.registry if name in schemas]

    def get_schemas_for_tools(self, tool_names: list) -> list:
        """Return schemas only for the specified tool names."""
        all_schemas = {s["name"]: s for s in self.get_tool_schemas()}
        return [all_schemas[name] for name in tool_names if name in all_schemas]

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

    # ─── Tool Implementations ─────────────────────────────────

    def _run_code(self, code: str, language: str = "python") -> str:
        # Placeholder for sandboxed execution
        return f"Simulated output for running {language} code."

    def _read_file(self, filepath: str) -> str:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _create_file(self, filepath: str, content: str) -> str:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File created: {filepath}"
        except Exception as e:
            return f"Error creating file: {str(e)}"

    def _edit_file(self, filepath: str, content: str, mode: str = "overwrite") -> str:
        try:
            if not os.path.exists(filepath):
                return f"Error: File does not exist: {filepath}"
            write_mode = 'a' if mode == 'append' else 'w'
            with open(filepath, write_mode, encoding='utf-8') as f:
                f.write(content)
            return f"File edited ({mode}): {filepath}"
        except Exception as e:
            return f"Error editing file: {str(e)}"

    def _delete_file(self, filepath: str) -> str:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return f"File deleted: {filepath}"
            else:
                return f"File not found: {filepath}"
        except Exception as e:
            return f"Error deleting file: {str(e)}"

    def _list_files(self, directory: str) -> str:
        try:
            if not os.path.isdir(directory):
                return f"Not a directory: {directory}"
            entries = os.listdir(directory)
            if not entries:
                return "(empty directory)"
            return "\n".join(entries)
        except Exception as e:
            return f"Error listing directory: {str(e)}"
