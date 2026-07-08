from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Any, Dict
from datetime import datetime
from backend.models.schemas import DAGNodeSchema, DAGEdgeSchema
import sqlite3
import uuid
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

DATABASE_PATH = os.getenv("DATABASE_PATH", "swe_agent.db")

def get_db():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    version: str
    entry_node_id: Optional[str] = None
    cron_schedule: Optional[str] = None
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    created_at: str
    updated_at: str

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: Optional[str] = '1.0'
    entry_node_id: Optional[str] = None
    cron_schedule: Optional[str] = None
    nodes: List[DAGNodeSchema] = []
    edges: List[DAGEdgeSchema] = []

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    entry_node_id: Optional[str] = None
    cron_schedule: Optional[str] = None
    nodes: Optional[List[DAGNodeSchema]] = None
    edges: Optional[List[DAGEdgeSchema]] = None

@router.get("/workflows", response_model=List[WorkflowResponse])
def get_workflows(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM workflows ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    workflows = []
    for row in rows:
        try:
            workflows.append(WorkflowResponse(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                version=row["version"],
                entry_node_id=row["entry_node_id"],
                cron_schedule=dict(row).get("cron_schedule"),
                nodes=json.loads(row["nodes_json"]),
                edges=json.loads(row["edges_json"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            ))
        except Exception:
            pass
            
    return workflows

@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    return WorkflowResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        version=row["version"],
        entry_node_id=row["entry_node_id"],
        cron_schedule=dict(row).get("cron_schedule"),
        nodes=json.loads(row["nodes_json"]),
        edges=json.loads(row["edges_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

def _validate_nodes_edges(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
    """Validate nodes and edges through Pydantic schemas.
    Returns (validated_nodes, validated_edges) as plain dicts for JSON storage.
    Logs warnings for validation issues but does not block saves."""
    validated_nodes = []
    for raw_node in nodes:
        try:
            parsed = DAGNodeSchema.model_validate(raw_node)
            validated_nodes.append(raw_node)  # Keep original dict to preserve unknown fields
        except ValidationError as e:
            logger.warning(f"Node validation warning for '{raw_node.get('id', '?')}': {e}")
            validated_nodes.append(raw_node)  # Still accept it — graceful degradation

    validated_edges = []
    for raw_edge in edges:
        try:
            parsed = DAGEdgeSchema.model_validate(raw_edge)
            validated_edges.append(raw_edge)
        except ValidationError as e:
            logger.warning(f"Edge validation warning for '{raw_edge.get('id', '?')}': {e}")
            validated_edges.append(raw_edge)

    return validated_nodes, validated_edges


@router.post("/workflows", response_model=WorkflowResponse)
def create_workflow(workflow: WorkflowCreate, db: sqlite3.Connection = Depends(get_db)):
    workflow_id = str(uuid.uuid4())
    cursor = db.cursor()
    
    now = datetime.utcnow().isoformat() + "Z"
    
    # Dump Pydantic schemas back to dicts before validation (to preserve extra fields if any)
    raw_nodes = [n.model_dump(by_alias=True) for n in workflow.nodes]
    raw_edges = [e.model_dump(by_alias=True) for e in workflow.edges]
    
    # Validate nodes and edges through DAG schemas
    validated_nodes, validated_edges = _validate_nodes_edges(raw_nodes, raw_edges)
    
    cursor.execute(
        """INSERT INTO workflows 
           (id, name, description, version, entry_node_id, cron_schedule, nodes_json, edges_json, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            workflow_id, 
            workflow.name, 
            workflow.description, 
            workflow.version,
            workflow.entry_node_id,
            workflow.cron_schedule,
            json.dumps(validated_nodes),
            json.dumps(validated_edges),
            now,
            now
        )
    )
    db.commit()
    
    return get_workflow(workflow_id, db)

@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(workflow_id: str, workflow_update: WorkflowUpdate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    now = datetime.utcnow().isoformat() + "Z"
    
    updates = []
    params = []
    
    if workflow_update.name is not None:
        updates.append("name = ?")
        params.append(workflow_update.name)
    if workflow_update.description is not None:
        updates.append("description = ?")
        params.append(workflow_update.description)
    if workflow_update.version is not None:
        updates.append("version = ?")
        params.append(workflow_update.version)
    if workflow_update.entry_node_id is not None:
        updates.append("entry_node_id = ?")
        params.append(workflow_update.entry_node_id)
    if workflow_update.cron_schedule is not None:
        updates.append("cron_schedule = ?")
        params.append(workflow_update.cron_schedule if workflow_update.cron_schedule else None)
    if workflow_update.nodes is not None:
        raw_nodes = [n.model_dump(by_alias=True) for n in workflow_update.nodes]
        validated_nodes, _ = _validate_nodes_edges(raw_nodes, [])
        updates.append("nodes_json = ?")
        params.append(json.dumps(validated_nodes))
    if workflow_update.edges is not None:
        raw_edges = [e.model_dump(by_alias=True) for e in workflow_update.edges]
        _, validated_edges = _validate_nodes_edges([], raw_edges)
        updates.append("edges_json = ?")
        params.append(json.dumps(validated_edges))
        
    updates.append("updated_at = ?")
    params.append(now)
    params.append(workflow_id)
    
    if updates:
        query = f"UPDATE workflows SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        db.commit()
        
    return get_workflow(workflow_id, db)

@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    db.commit()
    return {"status": "success", "message": "Workflow deleted"}
