from fastapi import APIRouter, Request, HTTPException
import json
from backend.core.database import get_db_connection
from backend.core.orchestrator import DAGOrchestrator
import asyncio

router = APIRouter()

@router.post("/{connector_id}")
async def handle_webhook(connector_id: str, request: Request):
    if connector_id == "slack":
        form_data = await request.form()
        payload_str = form_data.get("payload")
        if not payload_str:
            raise HTTPException(status_code=400, detail="Missing payload")

        payload = json.loads(payload_str)
        if payload.get("type") == "block_actions":
            actions = payload.get("actions", [])
            for action in actions:
                action_value = action.get("value")
                # Expected value format: "task_id:node_id:decision"
                if action_value and ":" in action_value:
                    parts = action_value.split(":")
                    if len(parts) >= 3:
                        task_id = parts[0]
                        node_id = parts[1]
                        decision = parts[2]
                        
                        conn = get_db_connection()
                        try:
                            # Resume logic - update the specific waiting node execution
                            # In our schema, agent_runs tracks node executions
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE agent_runs SET status = 'success', output_result = ? WHERE task_id = ? AND status = 'waiting'",
                                (json.dumps({"decision": decision}), int(task_id))
                            )
                            
                            # Mark overarching task as in_progress again
                            cursor.execute(
                                "UPDATE tasks SET status = 'in_progress' WHERE id = ?",
                                (int(task_id),)
                            )
                            conn.commit()
                            
                            # Re-invoke the orchestrator to continue the DAG
                            # We need workflow_id to initialize DAGOrchestrator
                            cursor.execute("SELECT workflow_id FROM tasks WHERE id = ?", (int(task_id),))
                            task_row = cursor.fetchone()
                            if task_row and task_row['workflow_id']:
                                orchestrator = DAGOrchestrator(task_id=int(task_id), workflow_id=task_row['workflow_id'])
                                asyncio.create_task(orchestrator.execute())
                            
                        finally:
                            conn.close()
                        
                        return {"text": f"Workflow resumed with decision: {decision}"}
                        
    return {"status": "ok", "connector": connector_id}
