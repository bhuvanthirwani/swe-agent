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
import sqlite3
import asyncio
import json

app = FastAPI(title="Agentic Workflow API", description="Python Backend for Universal Agents")

# Mount Routers
app.include_router(slack_router, prefix="/api", tags=["Slack Webhook"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(config_router, prefix="/api", tags=["Config"])
app.include_router(workflows_router, prefix="/api", tags=["Workflows"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Generic Webhooks"])

async def suggestion_agent_task():
    while True:
        try:
            print("Running suggestion agent background task...")
            # Trigger the orchestrator or agent for suggestions
            # Example: 
            # runtime = UniversalAgentRuntime(agent_id="suggestion-agent")
            # await runtime.execute(AgentInput(agent_id="suggestion-agent", input_data={}))
        except Exception as e:
            print(f"Suggestion agent error: {e}")
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(suggestion_agent_task())

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
    # StreamingResponse pushing Server-Sent Events to the frontend UI
    async def event_generator():
        # Mock initial SSE events mapping to existing Next.js logic
        yield f"data: {json.dumps({'type': 'stage_start', 'stage': 'requirements'})}\n\n"
        await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'type': 'stage_complete', 'stage': 'requirements', 'output': 'Requirements verified from ' + req.requirement})}\n\n"
        
        yield f"data: {json.dumps({'type': 'stage_start', 'stage': 'code'})}\n\n"
        for word in ["def ", "hello", "()", ":\n", "    print", "('world')"]:
            yield f"data: {json.dumps({'type': 'stage_token', 'stage': 'code', 'token': word})}\n\n"
            await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'type': 'stage_complete', 'stage': 'code', 'output': 'Code written'})}\n\n"
        
        yield f"data: {json.dumps({'type': 'pipeline_complete'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

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
