from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class LLMConfig(BaseModel):
    id: int
    provider: str
    model_name: str
    api_key: Optional[str]
    base_url: Optional[str]

class ToolConfig(BaseModel):
    id: int
    name: str
    description: str
    code_reference: Optional[str]

class AgentConfig(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str]
    system_prompt: str
    llm: LLMConfig
    tools: List[ToolConfig] = []

class AgentInput(BaseModel):
    task_id: int
    agent_id: int
    input_context: Dict[str, Any]

class AgentOutput(BaseModel):
    status: str = "success"
    output_result: Dict[str, Any]
    error_logs: Optional[str] = None

class SuggestionResult(BaseModel):
    project_name: str
    title: str
    impact_level: str
    description: str
    files_affected: List[str]
