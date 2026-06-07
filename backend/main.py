from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from backend.models.interfaces import AgentInput, AgentOutput
from backend.models.validators import OrchestrationRequest, WorkspaceAnalysisRequest, HITLResponse, DeliveryRequest
from backend.core.agent_runtime import UniversalAgentRuntime
from backend.core.orchestrator import PipelineOrchestrator
from backend.api.slack_webhook import router as slack_router
from backend.api.dashboard import router as dashboard_router
from backend.api.config import router as config_router
from backend.api.workflows import router as workflows_router
from backend.api.webhooks import router as webhooks_router
from backend.api.connectors import router as connectors_router
from backend.api.rbac import router as rbac_router
from backend.api.skills import router as skills_router
from backend.api.rag import router as rag_router
import sqlite3
import asyncio
import json
import os
from datetime import datetime
from croniter import croniter

app = FastAPI(title="Agentic Workflow API", description="Python Backend for Universal Agents")

# Mount Routers
app.include_router(slack_router, prefix="/api", tags=["Slack Webhook"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(config_router, prefix="/api", tags=["Config"])
app.include_router(workflows_router, prefix="/api", tags=["Workflows"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Generic Webhooks"])
app.include_router(connectors_router, prefix="/api/connectors", tags=["Connectors"])
app.include_router(rbac_router, prefix="/api/rbac", tags=["RBAC"])
app.include_router(skills_router, prefix="/api/skills", tags=["Skills"])
app.include_router(rag_router, prefix="/api/rag", tags=["RAG"])

async def cron_scheduler_task():
    """Background loop to trigger workflows that have a cron schedule."""
    from backend.core.database import get_db_connection
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name, cron_schedule FROM workflows WHERE cron_schedule IS NOT NULL AND cron_schedule != ''")
            workflows = cursor.fetchall()
            
            now = datetime.utcnow()
            
            # Ensure we have a default project
            cursor.execute("SELECT id FROM projects LIMIT 1")
            proj_row = cursor.fetchone()
            project_id = proj_row['id'] if proj_row else 1
            
            for wf in workflows:
                wf_id = wf['id']
                cron_str = wf['cron_schedule']
                
                # Find last run time for this workflow
                cursor.execute("SELECT MAX(started_at) as last_run FROM tasks WHERE workflow_id = ?", (wf_id,))
                run_row = cursor.fetchone()
                
                # If never run, run immediately? Or wait for next cron? 
                # Let's say if never run, we use workflow creation time or just default to now.
                # Actually, better to check if `croniter` next execution is past due since last run.
                try:
                    last_run_time = datetime.fromisoformat(run_row['last_run'].replace('Z', '')) if (run_row and run_row['last_run']) else now
                    cron = croniter(cron_str, last_run_time)
                    next_run = cron.get_next(datetime)
                    
                    if next_run <= now:
                        print(f"Triggering scheduled workflow: {wf['name']} ({wf_id})")
                        # Insert a new task
                        cursor.execute(
                            "INSERT INTO tasks (project_id, title, status, workflow_id) VALUES (?, ?, ?, ?)",
                            (project_id, f"Scheduled Run: {wf['name']}", 'in_progress', wf_id)
                        )
                        task_id = cursor.lastrowid
                        conn.commit()
                        
                        # Trigger execution asynchronously so it doesn't block scheduler
                        orchestrator = PipelineOrchestrator(task_id) # Legacy support check? No, use DAGOrchestrator
                        from backend.core.orchestrator import DAGOrchestrator
                        dag_orch = DAGOrchestrator(task_id, wf_id)
                        asyncio.create_task(dag_orch.execute({"trigger_source": "cron"}))
                        
                except Exception as ce:
                    print(f"Cron eval error for wf {wf_id}: {ce}")
                    
            conn.close()
        except Exception as e:
            print(f"Workflow scheduler error: {e}")
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cron_scheduler_task())

@app.post("/api/agents/run", response_model=AgentOutput)
async def run_agent(input_data: AgentInput):
    try:
        # Initialize the universal runtime for the specific agent
        runtime = UniversalAgentRuntime(agent_id=input_data.agent_id)
        
        # Execute the agent with the provided input context
        result = await runtime.execute(input_data)
        return result
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except sqlite3.Error as sqle:
        raise HTTPException(status_code=500, detail=f"Database error: {str(sqle)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")

@app.post("/api/orchestrate")
async def execute_workflow(req: OrchestrationRequest):
    if req.workflow_id and req.workflow_id != 'standard-pipeline':
        from backend.core.pipeline import execute_dag_pipeline
        return StreamingResponse(
            execute_dag_pipeline(req.requirement, req.workflow_id, req.hitl_enabled),
            media_type="text/event-stream"
        )
    else:
        from backend.core.pipeline import execute_linear_pipeline
        return StreamingResponse(
            execute_linear_pipeline(req.requirement, req.hitl_enabled),
            media_type="text/event-stream"
        )

@app.post("/api/workspace")
async def save_workspace():
    return {"success": True, "projectPath": "/workspace/saved"}

@app.get("/api/sessions")
async def get_sessions():
    return []

@app.post("/api/vision/process")
async def process_vision():
    return {"code": "console.log('Mock vision process')", "tokensUsed": 100}

@app.post("/api/analyze")
async def analyze_workspace(req: WorkspaceAnalysisRequest):
    return {"status": "analyzed", "repo": req.repo_url}

@app.post("/api/hitl")
async def hitl_response(req: HITLResponse):
    return {"status": "hitl_processed", "decision": req.decision}

@app.post("/api/deliver")
async def deliver_artifacts(req: DeliveryRequest):
    return {"status": "delivered", "target": req.target, "success": True, "repoUrl": "https://github.com/mock/repo"}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Agentic Workflow Backend"}
