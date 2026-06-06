from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime
import sqlite3
import uuid
import json
import os

router = APIRouter()

DATABASE_PATH = os.getenv("DATABASE_PATH", "swe_agent.db")

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
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
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    created_at: str
    updated_at: str

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: Optional[str] = '1.0'
    entry_node_id: Optional[str] = None
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    entry_node_id: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None

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
        nodes=json.loads(row["nodes_json"]),
        edges=json.loads(row["edges_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )

@router.post("/workflows", response_model=WorkflowResponse)
def create_workflow(workflow: WorkflowCreate, db: sqlite3.Connection = Depends(get_db)):
    workflow_id = str(uuid.uuid4())
    cursor = db.cursor()
    
    now = datetime.utcnow().isoformat() + "Z"
    
    cursor.execute(
        """INSERT INTO workflows 
           (id, name, description, version, entry_node_id, nodes_json, edges_json, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            workflow_id, 
            workflow.name, 
            workflow.description, 
            workflow.version,
            workflow.entry_node_id,
            json.dumps(workflow.nodes),
            json.dumps(workflow.edges),
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
    if workflow_update.nodes is not None:
        updates.append("nodes_json = ?")
        params.append(json.dumps(workflow_update.nodes))
    if workflow_update.edges is not None:
        updates.append("edges_json = ?")
        params.append(json.dumps(workflow_update.edges))
        
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
