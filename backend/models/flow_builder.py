from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class FlowBuilderMessage(BaseModel):
    type: str
    session_id: str
    
class UserMessage(BaseModel):
    type: str = "user_message"
    content: str
    sessionId: str
    workflowId: Optional[str] = None
    mode: Optional[str] = "create"
    currentWorkflow: Optional[Dict[str, Any]] = None

class ConfirmWorkflowMessage(BaseModel):
    type: str = "confirm_workflow"
    sessionId: str
    workflow: Dict[str, Any]

class CancelMessage(BaseModel):
    type: str = "cancel"
    sessionId: str

# Server -> Client

class AssistantToken(BaseModel):
    type: str = "assistant_token"
    token: str

class GraphDelta(BaseModel):
    type: str = "graph_delta"
    op: str # "add_node", "add_edge"
    payload: Dict[str, Any]

class WorkflowProposal(BaseModel):
    type: str = "workflow_proposal"
    workflow: Dict[str, Any]
    validationStatus: str # "valid", "warnings", "invalid"

class ValidationResult(BaseModel):
    type: str = "validation_result"
    valid: bool
    errors: List[str]
    warnings: List[str]

class ResourceCreated(BaseModel):
    type: str = "resource_created"
    resourceType: str
    resource: Dict[str, Any]
