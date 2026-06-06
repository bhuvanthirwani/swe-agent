from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.database import get_db_connection
import sqlite3
import json

router = APIRouter()

# --- LLM Configs API ---
class LLMConfigCreate(BaseModel):
    name: str
    provider: str
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class LLMConfigResponse(LLMConfigCreate):
    id: int

@router.get("/llm_configs", response_model=List[LLMConfigResponse])
def get_llm_configs():
    conn = get_db_connection()
    configs = conn.execute("SELECT * FROM llm_configs").fetchall()
    conn.close()
    return [dict(c) for c in configs]

@router.post("/llm_configs", response_model=LLMConfigResponse)
def create_llm_config(config: LLMConfigCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO llm_configs (name, provider, model_name, api_key, base_url) VALUES (?, ?, ?, ?, ?)",
            (config.name, config.provider, config.model_name, config.api_key, config.base_url)
        )
        conn.commit()
        config_id = cursor.lastrowid
        return {**config.dict(), "id": config_id}
    finally:
        conn.close()

@router.put("/llm_configs/{config_id}", response_model=LLMConfigResponse)
def update_llm_config(config_id: int, config: LLMConfigCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE llm_configs SET name = ?, provider = ?, model_name = ?, api_key = ?, base_url = ? WHERE id = ?",
            (config.name, config.provider, config.model_name, config.api_key, config.base_url, config_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="LLM config not found")
        conn.commit()
        return {**config.dict(), "id": config_id}
    finally:
        conn.close()

@router.delete("/llm_configs/{config_id}")
def delete_llm_config(config_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM agent_llms WHERE llm_id = ?", (config_id,))
    conn.execute("DELETE FROM llm_configs WHERE id = ?", (config_id,))
    conn.commit()
    conn.close()
    return {"message": "LLM config deleted"}

# --- Agent Models Mapping API ---
class AgentLLMMap(BaseModel):
    agent_name: str
    llm_id: int

@router.post("/agent_llms")
def set_agent_llm(mapping: AgentLLMMap):
    conn = get_db_connection()
    cursor = conn.cursor()
    # find agent by name
    agent_row = cursor.execute("SELECT id FROM agents WHERE name = ?", (mapping.agent_name,)).fetchone()
    if not agent_row:
        # Create a stub agent entry if it doesn't exist
        cursor.execute("INSERT INTO agents (name, type, system_prompt) VALUES (?, 'generator', '')", (mapping.agent_name,))
        agent_id = cursor.lastrowid
    else:
        agent_id = agent_row["id"]

    cursor.execute("DELETE FROM agent_llms WHERE agent_id = ?", (agent_id,))
    cursor.execute(
        "INSERT INTO agent_llms (agent_id, llm_id, is_primary) VALUES (?, ?, 1)",
        (agent_id, mapping.llm_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Agent LLM mapped"}

@router.get("/agent_llms")
def get_agent_llms():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT a.name as agent_name, l.id as llm_id 
        FROM agent_llms al
        JOIN agents a ON al.agent_id = a.id
        JOIN llm_configs l ON al.llm_id = l.id
        WHERE al.is_primary = 1
    """).fetchall()
    conn.close()
    return {row["agent_name"]: row["llm_id"] for row in rows}

# --- Service Integrations API ---
class ServiceIntegration(BaseModel):
    service_name: str
    metadata: Dict[str, Any]

@router.get("/service_integrations/{service_name}")
def get_service_integration(service_name: str):
    conn = get_db_connection()
    row = conn.execute("SELECT metadata FROM service_integrations WHERE service_name = ?", (service_name,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["metadata"])
    return {}

@router.post("/service_integrations")
def create_or_update_service_integration(integration: ServiceIntegration):
    conn = get_db_connection()
    metadata_json = json.dumps(integration.metadata)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM service_integrations WHERE service_name = ?", (integration.service_name,))
        if cursor.fetchone():
            cursor.execute("UPDATE service_integrations SET metadata = ? WHERE service_name = ?", (metadata_json, integration.service_name))
        else:
            cursor.execute("INSERT INTO service_integrations (service_name, metadata) VALUES (?, ?)", (integration.service_name, metadata_json))
        conn.commit()
        return {"message": "Service integration saved"}
    finally:
        conn.close()
