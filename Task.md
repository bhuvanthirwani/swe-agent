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

## Phase 6: Node.js to Python Migration
- [ ] Audit existing Node.js API routes and backend features.
- [ ] Incrementally migrate existing Node.js features to the Python `backend` directory.
- [ ] Update frontend requests to point to the new Python endpoints.
- [ ] Deprecate and remove old Node.js backend code once migration is fully completed and verified.

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
```
