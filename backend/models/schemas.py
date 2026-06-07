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

