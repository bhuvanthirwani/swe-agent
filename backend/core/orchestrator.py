import json
import asyncio
from typing import List, Dict, Any
from backend.core.agent_runtime import UniversalAgentRuntime
from backend.models.interfaces import AgentInput
from backend.core.database import get_db_connection
from backend.connectors.slack import SlackConnector
from backend.connectors.discord import DiscordConnector
from backend.connectors.webhook import WebhookConnector

class DAGOrchestrator:
    def __init__(self, task_id: int, workflow_id: str):
        self.task_id = task_id
        self.workflow_id = workflow_id
        
    def _ensure_schema(self, conn):
        # Dynamically add node_id to agent_runs if it doesn't exist
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(agent_runs)")
        columns = [col['name'] for col in cursor.fetchall()]
        if 'node_id' not in columns:
            cursor.execute("ALTER TABLE agent_runs ADD COLUMN node_id TEXT")
            
        cursor.execute("PRAGMA table_info(tasks)")
        task_columns = [col['name'] for col in cursor.fetchall()]
        if 'workflow_id' not in task_columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN workflow_id TEXT")
            
        conn.commit()

    async def execute(self, initial_context: Dict[str, Any] = None):
        conn = get_db_connection()
        try:
            self._ensure_schema(conn)
            cursor = conn.cursor()
            
            # Fetch workflow
            cursor.execute("SELECT nodes_json, edges_json, entry_node_id FROM workflows WHERE id = ?", (self.workflow_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Workflow {self.workflow_id} not found")
                
            nodes = json.loads(row['nodes_json'])
            edges = json.loads(row['edges_json'])
            entry_node_id = row['entry_node_id']
            
            # Get completed node_ids for this task
            cursor.execute("SELECT node_id, status, output_result FROM agent_runs WHERE task_id = ?", (self.task_id,))
            runs = cursor.fetchall()
            
            completed_nodes = {}
            for r in runs:
                if r['node_id'] and r['status'] == 'success':
                    completed_nodes[r['node_id']] = r['output_result']
                elif r['node_id'] and r['status'] == 'waiting':
                    # If we are waiting, we stop execution here.
                    print(f"Orchestrator halted: Node {r['node_id']} is waiting for human/external input.")
                    return
            
            # Topological sort or simple BFS based on completed nodes
            # For simplicity, if no nodes run, we start with entry node or nodes with no incoming edges
            if not completed_nodes:
                next_nodes = [n['id'] for n in nodes if not any(e['to'] == n['id'] for e in edges)]
            else:
                next_nodes = []
                for edge in edges:
                    if edge['from'] in completed_nodes and edge['to'] not in completed_nodes:
                        # Check if all predecessors of edge['to'] are completed
                        preds = [e['from'] for e in edges if e['to'] == edge['to']]
                        if all(p in completed_nodes for p in preds):
                            if edge['to'] not in next_nodes:
                                next_nodes.append(edge['to'])
                                
            if not next_nodes:
                # Finished
                cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (self.task_id,))
                conn.commit()
                print(f"Workflow {self.workflow_id} for task {self.task_id} completed.")
                return
                
            # Execute the next nodes
            for node_id in next_nodes:
                node_config = next((n for n in nodes if n['id'] == node_id), None)
                if not node_config:
                    continue
                    
                print(f"Executing node: {node_id} ({node_config['type']})")
                
                # Context merging from predecessors
                preds = [e['from'] for e in edges if e['to'] == node_id]
                merged_context = initial_context or {}
                for p in preds:
                    if p in completed_nodes and completed_nodes[p]:
                        try:
                            parsed = json.loads(completed_nodes[p])
                            if isinstance(parsed, dict):
                                merged_context.update(parsed)
                        except:
                            pass

                if node_config['type'] == 'agent':
                    # Resolve agent_id
                    cursor.execute("SELECT id FROM agents WHERE name = ?", (node_config.get('agentName', ''),))
                    agent_row = cursor.fetchone()
                    agent_id = agent_row['id'] if agent_row else 0
                    
                    # Insert run
                    cursor.execute(
                        "INSERT INTO agent_runs (task_id, agent_id, step_order, status, input_context, node_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (self.task_id, agent_id, 0, 'running', json.dumps(merged_context), node_id)
                    )
                    run_id = cursor.lastrowid
                    conn.commit()
                    
                    runtime = UniversalAgentRuntime(agent_id=agent_id)
                    input_data = AgentInput(task_id=self.task_id, agent_id=agent_id, input_context=merged_context)
                    result = await runtime.execute(input_data)
                    
                    cursor.execute(
                        "UPDATE agent_runs SET status = 'success', output_result = ? WHERE id = ?",
                        (str(result.output_result), run_id)
                    )
                    conn.commit()
                    
                elif node_config['type'] == 'action':
                    connector_id = node_config.get('connectorId')
                    # Find integration
                    cursor.execute("SELECT metadata FROM service_integrations WHERE service_name = ?", (connector_id,))
                    meta_row = cursor.fetchone()
                    webhook_url = json.loads(meta_row['metadata']).get('webhookUrl') if meta_row else None
                    
                    cursor.execute(
                        "INSERT INTO agent_runs (task_id, agent_id, step_order, status, input_context, node_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (self.task_id, 0, 0, 'running', json.dumps(merged_context), node_id)
                    )
                    run_id = cursor.lastrowid
                    conn.commit()
                    
                    # Dispatch
                    success = False
                    if connector_id == 'slack':
                        slack = SlackConnector(webhook_url)
                        success = await slack.send_notification("Workflow Action", "Action executed automatically.", "info")
                    elif connector_id == 'discord':
                        discord = DiscordConnector(webhook_url)
                        success = await discord.send_notification("Workflow Action", "Action executed automatically.", "info")
                        
                    cursor.execute(
                        "UPDATE agent_runs SET status = ?, output_result = ? WHERE id = ?",
                        ('success' if success else 'failed', json.dumps({"dispatched": success}), run_id)
                    )
                    conn.commit()
                    
                elif node_config['type'] == 'human_checkpoint':
                    connector_id = node_config.get('connectorId', 'slack')
                    
                    cursor.execute("SELECT metadata FROM service_integrations WHERE service_name = ?", (connector_id,))
                    meta_row = cursor.fetchone()
                    webhook_url = json.loads(meta_row['metadata']).get('webhookUrl') if meta_row else None
                    
                    # Set status to waiting
                    cursor.execute(
                        "INSERT INTO agent_runs (task_id, agent_id, step_order, status, input_context, node_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (self.task_id, 0, 0, 'waiting', json.dumps(merged_context), node_id)
                    )
                    conn.commit()
                    
                    # Update tasks to paused
                    cursor.execute("UPDATE tasks SET status = 'paused' WHERE id = ?", (self.task_id,))
                    conn.commit()
                    
                    # Dispatch Interactive message
                    if connector_id == 'slack':
                        slack = SlackConnector(webhook_url)
                        # We use the Slack action fallback where we pass action format
                        # Real implementation would use Slack block kit with task_id:node_id
                        # Wait for webhook resume
                        
                    print(f"Workflow paused at node {node_id}")
                    return # Stop traversal
                    
                else:
                    # Condition, Parallel, Merge nodes just pass through context for now
                    cursor.execute(
                        "INSERT INTO agent_runs (task_id, agent_id, step_order, status, input_context, node_id, output_result) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (self.task_id, 0, 0, 'success', json.dumps(merged_context), node_id, json.dumps(merged_context))
                    )
                    conn.commit()
                    
            # Recursively continue
            await self.execute(initial_context)
            
        finally:
            conn.close()

# Keep PipelineOrchestrator for backwards compatibility
class PipelineOrchestrator:
    def __init__(self, task_id: int):
        self.task_id = task_id
        
    async def run_pipeline(self, pipeline_agent_ids: List[int], initial_context: Dict[str, Any]) -> Dict[str, Any]:
        print("Running legacy linear pipeline...")
        return initial_context
