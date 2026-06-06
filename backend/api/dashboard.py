from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.core.database import get_db_connection
import sqlite3

router = APIRouter()

# --- System Helper ---
def is_system_locked(conn: sqlite3.Connection) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tasks WHERE status IN ('in_progress', 'paused') LIMIT 1")
    return cursor.fetchone() is not None

@router.get("/system/lock")
def get_system_lock():
    conn = get_db_connection()
    locked = is_system_locked(conn)
    conn.close()
    return {"locked": locked}

# --- Tools API ---
class ToolCreate(BaseModel):
    name: str
    description: str
    code_reference: Optional[str] = None

@router.get("/tools")
def get_tools():
    conn = get_db_connection()
    tools = conn.execute("SELECT * FROM tools").fetchall()
    conn.close()
    return [dict(t) for t in tools]

@router.post("/tools")
def create_tool(tool: ToolCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tools (name, description, code_reference) VALUES (?, ?, ?)",
            (tool.name, tool.description, tool.code_reference)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "message": "Tool created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Tool name already exists")
    finally:
        conn.close()

@router.delete("/tools/{tool_id}")
def delete_tool(tool_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()
    return {"message": "Tool deleted"}

# --- Agents API ---
class AgentCreate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    system_prompt: str
    input_schema: Optional[str] = None
    output_schema: Optional[str] = None
    tool_ids: List[int] = []

class AgentUpdate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    system_prompt: str
    input_schema: Optional[str] = None
    output_schema: Optional[str] = None
    tool_ids: List[int] = []

@router.get("/agents")
def get_agents():
    conn = get_db_connection()
    agents = conn.execute("SELECT * FROM agents").fetchall()
    
    result = []
    for a in agents:
        agent_dict = dict(a)
        tools = conn.execute("SELECT tool_id FROM agent_tools WHERE agent_id = ?", (a["id"],)).fetchall()
        agent_dict["tool_ids"] = [t["tool_id"] for t in tools]
        result.append(agent_dict)
        
    conn.close()
    return result

@router.post("/agents")
def create_agent(agent: AgentCreate):
    conn = get_db_connection()
    if is_system_locked(conn):
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot modify agents while a workflow is active.")
        
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agents (name, type, description, system_prompt, input_schema, output_schema) VALUES (?, ?, ?, ?, ?, ?)",
            (agent.name, agent.type, agent.description, agent.system_prompt, agent.input_schema, agent.output_schema)
        )
        agent_id = cursor.lastrowid
        
        # Assign tools
        for tool_id in agent.tool_ids:
            cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)", (agent_id, tool_id))
            
        conn.commit()
        return {"id": agent_id, "message": "Agent created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Agent name already exists")
    finally:
        conn.close()

@router.put("/agents/{agent_id}")
def update_agent(agent_id: int, agent: AgentUpdate):
    conn = get_db_connection()
    if is_system_locked(conn):
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot modify agents while a workflow is active.")
        
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE agents SET name = ?, type = ?, description = ?, system_prompt = ?, input_schema = ?, output_schema = ? WHERE id = ?",
            (agent.name, agent.type, agent.description, agent.system_prompt, agent.input_schema, agent.output_schema, agent_id)
        )
        
        # Re-assign tools
        cursor.execute("DELETE FROM agent_tools WHERE agent_id = ?", (agent_id,))
        for tool_id in agent.tool_ids:
            cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)", (agent_id, tool_id))
            
        conn.commit()
        return {"message": "Agent updated successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Agent name already exists")
    finally:
        conn.close()

@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: int):
    conn = get_db_connection()
    if is_system_locked(conn):
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot delete agents while a workflow is active.")
        
    conn.execute("DELETE FROM agent_tools WHERE agent_id = ?", (agent_id,))
    conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
    conn.commit()
    conn.close()
    return {"message": "Agent deleted"}
