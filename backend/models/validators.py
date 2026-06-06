from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class WorkspaceAnalysisRequest(BaseModel):
    repo_url: str
    branch: str = "main"

class OrchestrationRequest(BaseModel):
    requirement: str
    resume_checkpoint_id: Optional[str] = None
    hitl_enabled: bool = False

class HITLResponse(BaseModel):
    request_id: str
    decision: str  # 'approved' or 'rejected'
    feedback: Optional[str] = None
    
class DeliveryRequest(BaseModel):
    target: str
    config: Dict[str, Any]
    files: List[Dict[str, str]]
