from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any

class TechStack(BaseModel):
    language: str
    framework: Optional[str] = None
    database: Optional[str] = None
    testing: Optional[str] = None

class AnalystOutputSchema(BaseModel):
    functionalRequirements: Optional[List[str]] = None
    nonFunctionalRequirements: Optional[List[str]] = None
    acceptanceCriteria: Optional[List[str]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None
    tech_stack: Optional[Union[List[str], Dict[str, str]]] = None
    techStack: Optional[Union[TechStack, Dict[str, str]]] = None
    complexity: Optional[str] = None  # 'low', 'medium', 'high'
    constraints: Optional[List[str]] = None
    assumptions: Optional[List[str]] = None

class TaskSchema(BaseModel):
    id: str
    title: str
    priority: str  # 'critical', 'high', 'medium', 'low', 'P0', 'P1', 'P2'
    dependencies: List[str]
    estimatedSize: Optional[str] = None  # 'XS', 'S', 'M', 'L', 'XL'
    size: Optional[str] = None  # 'S', 'M', 'L', 'XL'
    description: str

class PlannerOutputSchema(BaseModel):
    tasks: List[TaskSchema]
    totalEstimate: Optional[str] = None
    total_complexity: Optional[str] = None
    estimated_effort: Optional[str] = None

class IssueSchema(BaseModel):
    severity: str  # 'critical', 'high', 'medium', 'low', 'major', 'minor', 'suggestion'
    description: str
    suggestion: Optional[str] = None
    location: Optional[str] = None

class ReviewerOutputSchema(BaseModel):
    status: Optional[str] = None  # 'APPROVED', 'CHANGES_REQUESTED'
    decision: Optional[str] = None  # 'APPROVED', 'CHANGES_REQUESTED'
    score: Optional[int] = Field(None, ge=1, le=10)
    issues: Optional[List[IssueSchema]] = None
    summary: Optional[str] = None

class VulnerabilitySchema(BaseModel):
    type: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    location: Optional[str] = None
    evidence: Optional[str] = None
    recommendation: str

class SecurityOutputSchema(BaseModel):
    passed: bool
    severity: str  # 'critical', 'high', 'medium', 'low', 'none'
    vulnerabilities: List[VulnerabilitySchema]
    summary: str
    owasp_categories: Optional[List[str]] = None


# ─── DAG Workflow Schemas (Visual Editor) ─────────────────────

class DAGPortSchema(BaseModel):
    """Schema for a connection port on a workflow node."""
    id: str
    label: str
    direction: str  # "input" | "output"
    kind: str       # "control" | "data" | "model" | "tool" | "memory" | "rag" | "guardrail" | "vector" | "connector" | "error"
    position: Optional[str] = None  # "left" | "right" | "top" | "bottom"
    accepts: Optional[List[str]] = None
    required: Optional[bool] = None
    maxConnections: Optional[int] = None
    description: Optional[str] = None


class NodeConfigSchema(BaseModel):
    """Flexible config for component nodes (model, tool, memory, rag, guardrail).
    Uses extra='allow' so unknown fields are preserved for extensibility."""
    provider: Optional[str] = None
    modelName: Optional[str] = None
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    toolName: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    filePath: Optional[str] = None
    collectionName: Optional[str] = None
    topK: Optional[int] = None
    scoreThreshold: Optional[float] = None
    queryMode: Optional[str] = None
    policies: Optional[List[str]] = None
    phase: Optional[str] = None
    action: Optional[str] = None
    allowRetry: Optional[bool] = None
    maxSummaryTokens: Optional[int] = None
    importanceThreshold: Optional[float] = None
    allowWrites: Optional[bool] = None
    allowAgentWrites: Optional[bool] = None
    persistDirectory: Optional[str] = None
    ingestAgentOutputs: Optional[bool] = None
    clearOnRunStart: Optional[bool] = None
    writable: Optional[bool] = None
    updateOnComplete: Optional[bool] = None
    updateOnFailure: Optional[bool] = None

    class Config:
        extra = "allow"


class DAGNodeSchema(BaseModel):
    """Schema for a node in the workflow DAG, used for backend validation."""
    id: str
    type: str
    label: str
    x: float
    y: float
    agentName: Optional[str] = None
    description: Optional[str] = None
    ports: Optional[List[DAGPortSchema]] = None
    chatModel: Optional[str] = None
    memory: Optional[str] = None
    memoryConfig: Optional[str] = None
    tools: Optional[List[str]] = None
    useCompaction: Optional[bool] = None
    compactionStrategy: Optional[str] = None  # "off" | "auto" | "aggressive" | "memory_first" | "rag_first"
    maxContextTokens: Optional[int] = None
    config: Optional[NodeConfigSchema] = None
    connectorId: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    parallelBranches: Optional[List[List[str]]] = None
    checkpointConfig: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class DAGEdgeSchema(BaseModel):
    """Schema for an edge in the workflow DAG."""
    id: str
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    edgeType: Optional[str] = None  # "control" | "data" | "model" | "tool" | "memory" | "rag" | "guardrail" | "vector" | "error"
    label: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[str] = None
    mapping: Optional[Dict[str, str]] = None

    class Config:
        populate_by_name = True

