from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import asyncio
from backend.core.database import get_db_connection

router = APIRouter()

class FlowBuilderConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.generation_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        self.cancel_generation(session_id)

    async def send_json(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except:
                pass

    def cancel_generation(self, session_id: str):
        if session_id in self.generation_tasks:
            self.generation_tasks[session_id].cancel()
            del self.generation_tasks[session_id]

manager = FlowBuilderConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, sessionId: str, workflowId: str = None):
    await manager.connect(sessionId, websocket)
    
    # Optional: load existing session if present, else create
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT id FROM builder_sessions WHERE id = ?", (sessionId,)).fetchone()
        if not row:
            conn.execute("INSERT INTO builder_sessions (id, workflow_id) VALUES (?, ?)", (sessionId, workflowId))
            conn.commit()
    finally:
        conn.close()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type")
            
            if msg_type == "ping":
                await manager.send_json(sessionId, {"type": "pong"})
                
            elif msg_type == "user_message":
                content = message.get("content", "")
                current_workflow = message.get("currentWorkflow")
                
                from backend.core.flow_architect import FlowArchitectService
                try:
                    architect = FlowArchitectService()
                except Exception as e:
                    await manager.send_json(sessionId, {"type": "assistant_token", "token": f"❌ **Error**: {str(e)}"})
                    continue
                
                async def generate_task():
                    try:
                        async for event in architect.generate_workflow_stream(content, sessionId, current_workflow):
                            await manager.send_json(sessionId, event)
                    except Exception as e:
                        print("Error in generator:", e)
                        await manager.send_json(sessionId, {"type": "assistant_token", "token": f"\\n\\n❌ **Error during generation**: {str(e)}"})
                        
                manager.generation_tasks[sessionId] = asyncio.create_task(generate_task())
                
            elif msg_type == "cancel":
                manager.cancel_generation(sessionId)
                await manager.send_json(sessionId, {"type": "generation_cancelled"})
                
    except WebSocketDisconnect:
        manager.disconnect(sessionId)
