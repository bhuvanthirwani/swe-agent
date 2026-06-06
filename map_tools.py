import sqlite3
import os

DATABASE_PATH = os.getenv("DATABASE_PATH", "backend/swe_agent.db")

agent_tools_map = {
    "requirements-analyst": ["search_web"],
    "task-planner": [],
    "developer": ["read_file", "edit_code", "code_runner", "search_web"],
    "code-reviewer": ["read_file", "lint_code"],
    "security-reviewer": ["read_file", "lint_code"],
    "testing-agent": ["read_file", "edit_code", "code_runner"],
    "deployment-agent": ["read_file", "edit_code"],
    "compliance-agent": ["read_file", "lint_code"],
    "debt-scanner": ["read_file", "lint_code"],
    "product-manager": ["search_web"],
    "ux-designer": ["search_web"],
    "routerAgent": []
}

agent_tool_prompts = {
    "requirements-analyst": "\n\nYou have access to the search_web tool. Use it to research modern documentation or existing technical solutions if the user's request involves unfamiliar technologies.",
    "developer": "\n\nYou have access to the read_file and edit_code tools to manipulate the workspace. Use code_runner to verify snippets of logic before committing them. Use search_web if you need to look up exact syntax or library documentation.",
    "code-reviewer": "\n\nYou have access to the lint_code tool. ALWAYS run it on the generated files before providing your final review. Use read_file to inspect the full context of files.",
    "security-reviewer": "\n\nYou have access to the lint_code tool. ALWAYS run it on the generated files before providing your final review. Use read_file to inspect the full context of files.",
    "testing-agent": "\n\nYou have access to the read_file and edit_code tools. Use code_runner to execute the tests you generate and ensure they actually pass against the codebase.",
    "deployment-agent": "\n\nYou have access to the read_file and edit_code tools to inspect and write deployment configurations.",
    "compliance-agent": "\n\nYou have access to the lint_code tool and read_file tool to inspect the full context of files for compliance.",
    "debt-scanner": "\n\nYou have access to the lint_code tool and read_file tool to inspect the full context of files for architectural issues.",
    "product-manager": "\n\nYou have access to the search_web tool to research market standards and competitors.",
    "ux-designer": "\n\nYou have access to the search_web tool to research design trends and modern UI frameworks."
}

conn = sqlite3.connect(DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get tool IDs
cursor.execute("SELECT id, name FROM tools")
tools = {row['name']: row['id'] for row in cursor.fetchall()}

# Clear existing agent_tools
cursor.execute("DELETE FROM agent_tools")

# Get agents
cursor.execute("SELECT id, name, system_prompt FROM agents")
agents = cursor.fetchall()

for agent in agents:
    agent_id = agent['id']
    agent_name = agent['name']
    
    # 1. Update system prompt
    if agent_name in agent_tool_prompts:
        prompt_suffix = agent_tool_prompts[agent_name]
        current_prompt = agent['system_prompt']
        if prompt_suffix not in current_prompt:
            new_prompt = current_prompt + prompt_suffix
            cursor.execute("UPDATE agents SET system_prompt = ? WHERE id = ?", (new_prompt, agent_id))
            print(f"Updated prompt for {agent_name}")
    
    # 2. Insert into agent_tools
    if agent_name in agent_tools_map:
        for tool_name in agent_tools_map[agent_name]:
            if tool_name in tools:
                tool_id = tools[tool_name]
                cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)", (agent_id, tool_id))
                print(f"Mapped {agent_name} -> {tool_name}")

conn.commit()
conn.close()
print("Successfully mapped tools and updated prompts.")
