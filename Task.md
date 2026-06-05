# Implementation Tasks: Agentic Workflow & Python Migration

This document tracks the tasks required to build an automated, agentic workflow on top of existing software. 

**Project Aim:**
1. A **Suggestion Agent** will analyze the repository and suggest new features/improvements.
2. A **Notification Agent** will send these suggestions to Slack for review.
3. The user will interactively approve or decline the suggestions directly in Slack.
4. Upon approval, a **Developer Agent** will automatically write the code to develop and implement the approved feature.

**Architecture & Migration Strategy:**
- **Frontend**: The UI for managing this system will be added to the existing frontend project (Next.js).
- **Backend (New Feature)**: The entire backend for this new agentic workflow will be written in **Python**. A new `backend` folder will be created in the root directory for this purpose.
- **Database**: We will use **SQLite** as the database to store progress, suggestion data, and workflow states for the new backend. *(Overview of current state: The existing Next.js application currently does not use a persistent database; it relies entirely on in-memory states, file system parsing, and direct LLM context. We will be introducing SQLite as the first persistent data layer.)*
- **Migration**: After completing this feature, we will systematically migrate existing backend features from Node.js to Python.

---

## Phase 1: Python Backend Initialization & Context (GitHub MCP)
- [ ] Create a `backend` folder in the root directory.
- [ ] Initialize Python environment (e.g., FastAPI, Flask, `requirements.txt`).
- [ ] Install Python MCP SDK or construct lightweight HTTP/SSE MCP client interface.
- [ ] Set up **SQLite** database connection and schema to store application state, suggestions, and task progress.
- [ ] Create Python MCP client (`backend/github_mcp_client.py`) to query the GitHub MCP server for:
  - Repositories list
  - Branch, tree structures, and files
  - Readme and issues context
- [ ] Add configuration variables in `backend/.env` for the GitHub MCP URL and SQLite database path.

## Phase 2: Intelligence (Suggestion Agent - Python)
- [ ] Create Suggestion Agent in Python (`backend/agents/suggestion_agent.py`) using the AI model runtime.
- [ ] Define input/output interfaces for recommendations (structured JSON containing project, title, impact, description, files affected).
- [ ] Write the tool codes which will connect with the database to provide appropriate answers and capabilities to the agents.
- [ ] Hook up suggestion runner to evaluate the workspace context parsed from GitHub MCP.

## Phase 3: Notifications & Approval Interface (Slack - Python)
- [ ] Create Slack Connector (`backend/connectors/slack.py`) to send formatted messages.
- [ ] Use Slack Block Kit blocks containing:
  - Repository name & suggestion details
  - **"Approve"** and **"Decline"** interactive buttons with specific payload keys (e.g. `action_id: "approve_feature"`).
- [ ] Add `backend/.env` parameters for the Slack Bot Token / Incoming Webhook URL.

## Phase 4: Receiver & Trigger Endpoint (Slack Webhook - Python)
- [ ] Create Python API endpoint (`backend/api/slack_webhook.py`) to receive Slack interactive response payloads.
- [ ] Validate Slack request signature/token.
- [ ] Map approved suggestion back to a requirements definition string.
- [ ] Programmatically invoke the multi-agent orchestrator to implement the approved feature task.
- [ ] Update the original Slack message block in-place with execution progress (e.g., "🔄 Implementing...", "✅ Completed!").

## Phase 5: Dashboard & UI Control (Frontend)
- [ ] Add the frontend feature to the existing codebase (e.g., `src/app/page.tsx`).
- [ ] Create UI Suggestion panel displaying:
  - Scanned projects
  - Suggestion cards
  - "Send to Slack" trigger (making an API call to the new Python backend)
  - Manual local approval trigger button (making an API call to the new Python backend)

## Phase 6: Complete Node.js to Python Migration
This phase outlines the complete, from-scratch rewrite of the entire existing Node.js backend (`src/lib` and `src/app/api`) into the new Python `backend/` folder. This ensures the full application retains all existing functionality alongside the new agentic Slack workflow.

### 6.1 Core Orchestration & State Management
- [ ] Migrate `src/lib/orchestrator.ts` to `backend/core/orchestrator.py` (Main DAG/workflow runner).
- [ ] Migrate `src/lib/memory.ts`, `history.ts`, and `sessions.ts` to `backend/core/state_management.py`.
- [ ] Migrate `src/lib/hitl.ts` (Human-in-the-Loop) to integrate with the new SQLite schema and Slack approvals.
- [ ] Migrate `src/lib/audit.ts` and `roi.ts` for tracking metrics and system audits.
- [ ] Migrate `src/lib/rbac.ts` for role-based access control to tools and agents.

### 6.2 Agent Implementations (`src/lib/agents/*`)
- [ ] Port all agent definitions to `backend/agents/`:
  - `developer.py`, `codeReviewer.py`, `complianceAgent.py`, `debtScanner.py`, `deploymentAgent.py`, `productManager.py`, `requirementsAnalyst.py`, `routerAgent.py`, `securityReviewer.py`, `taskPlanner.py`, `testingAgent.py`, `uxDesigner.py`.
- [ ] Migrate system prompts from `src/lib/prompts/` to the new `agents` SQLite table or Python modules.

### 6.3 Tools & Skills (`src/lib/tools/*`, `src/lib/skills/*`)
- [ ] Port all tool executions (sandbox codeRunner, file system ops, git ops) to `backend/tools/`.
- [ ] Register tools in the new `tools` SQLite table and map them to agents in `agent_tools`.
- [ ] Migrate specific language skills and coding rules from `src/lib/skills/` to `backend/skills/`.

### 6.4 RAG, Context & Validation (`src/lib/rag/*`, `src/lib/validation/*`)
- [ ] Migrate `src/lib/validation/` (Zod schemas) to Pydantic models in `backend/models/`.
- [ ] Port `src/lib/rag/knowledgeBase.ts` (In-memory cosine search) to Python using numpy or a lightweight vector store.
- [ ] Migrate `src/lib/context.ts` and `src/lib/workspace/` (AST parsing, workspace handling) to Python equivalents.

### 6.5 API Endpoints (`src/app/api/*`)
Rebuild all Next.js API routes as FastAPI/Flask endpoints under `backend/api/routers/`:
- [ ] `/api/agent` -> `POST /api/agents/run`
- [ ] `/api/analyze` -> `POST /api/analyze/workspace`
- [ ] `/api/deliver` -> `POST /api/deliver/artifacts`
- [ ] `/api/execute` -> `POST /api/execute/workflow`
- [ ] `/api/hitl` -> `POST /api/hitl/respond`
- [ ] `/api/orchestrate` -> `POST /api/orchestrate/start`
- [ ] `/api/sessions` -> CRUD endpoints for sessions
- [ ] `/api/vision` -> `POST /api/vision/process`
- [ ] `/api/workspace` -> Endpoints for file parsing and management

### 6.6 Frontend Integration
- [ ] Update all API calls in `src/components/` and `src/app/page.tsx` to point to the new Python API base URL.
- [ ] Deprecate and remove the old `src/app/api` and `src/lib` backend code once the Python migration is fully completed and verified.
## Phase 7: Containerization (Docker)
- [ ] Create a `Dockerfile` for the Next.js frontend.
- [ ] Create a `Dockerfile` for the Python backend.
- [ ] (Optional) Create a `docker-compose.yml` to orchestrate both services locally.

## Database Schema (SQLite)
Below is the holistic schema design to support the complex multi-agent system and track the step-by-step progress of every single agent (including existing agents like Developer, CodeReviewer, ComplianceAgent, etc.) as they contribute to the overall task.

```sql
-- 1. High-level tracking of projects/repositories
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    repo_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Suggestions generated by the Intelligence Agent or user
CREATE TABLE suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    impact_level TEXT,
    description TEXT,
    files_affected TEXT, -- Stored as JSON string
    status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'declined'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 3. Overall tasks derived from approved suggestions
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suggestion_id INTEGER,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'in_progress', -- 'pending', 'in_progress', 'completed', 'failed'
    overall_progress_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(suggestion_id) REFERENCES suggestions(id),
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 4. Registry of all available agents in the system
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE, -- e.g., 'Developer', 'CodeReviewer', 'ComplianceAgent', 'SecurityReviewer'
    type TEXT NOT NULL, -- e.g., 'generator', 'reviewer', 'planner'
    description TEXT,
    system_prompt TEXT -- System prompt providing exact instructions for the agent
);

-- 4.5. Tools available to the agents, including database connection codes
CREATE TABLE tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    code_reference TEXT -- Indicates where the tool's code resides
);

-- Mapping which agents have access to which tools
CREATE TABLE agent_tools (
    agent_id INTEGER,
    tool_id INTEGER,
    PRIMARY KEY (agent_id, tool_id),
    FOREIGN KEY(agent_id) REFERENCES agents(id),
    FOREIGN KEY(tool_id) REFERENCES tools(id)
);

-- 5. Tracking individual agent steps and their specific progress
CREATE TABLE agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    agent_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL, -- The sequence in the pipeline
    status TEXT DEFAULT 'pending', -- 'pending', 'running', 'success', 'failed'
    input_context TEXT, -- JSON string of the input given to the agent
    output_result TEXT, -- JSON string or raw text of the agent's output
    error_logs TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(agent_id) REFERENCES agents(id)
);

-- 6. Artifacts or specific deliverables generated during the workflow
CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    agent_run_id INTEGER,
    file_path TEXT NOT NULL,
    content_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id),
    FOREIGN KEY(agent_run_id) REFERENCES agent_runs(id)
);
-- 7. Configuration for LLM providers (Deterministic workflows)
CREATE TABLE llm_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL, -- e.g., 'openai', 'anthropic', 'groq'
    model_name TEXT NOT NULL,
    api_key TEXT,
    base_url TEXT
);

-- Mapping agents to their designated LLMs
CREATE TABLE agent_llms (
    agent_id INTEGER,
    llm_id INTEGER,
    is_primary BOOLEAN DEFAULT 1,
    PRIMARY KEY (agent_id, llm_id),
    FOREIGN KEY(agent_id) REFERENCES agents(id),
    FOREIGN KEY(llm_id) REFERENCES llm_configs(id)
);

-- 8. Configuration for external service integrations (GitHub MCP, Social Media, Slack, etc.)
CREATE TABLE service_integrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL UNIQUE, -- e.g., 'github_mcp', 'slack', 'twitter'
    metadata TEXT -- JSON string containing all important config like base_url, api_keys, etc.
);
```
