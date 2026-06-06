import re

with open('c:/Projects/swe-agent/backend/seed.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to insert tool mapping logic after the tools are inserted.
# Find where tools are inserted:
tools_end_str = '''
    for tool in tools:
        cursor.execute("SELECT id FROM tools WHERE name = ?", (tool["name"],))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO tools (name, description, code_reference) VALUES (?, ?, ?)",
                (tool["name"], tool["description"], tool["code_reference"])
            )
            print(f"Created Tool: {tool['name']}")
        else:
            cursor.execute(
                "UPDATE tools SET description = ?, code_reference = ? WHERE name = ?",
                (tool["description"], tool["code_reference"], tool["name"])
            )
            print(f"Updated Tool: {tool['name']}")
'''

tool_mapping_logic = '''
    # 3.5 Map Tools to Agents and update prompts
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
        "requirements-analyst": "\\n\\nYou have access to the search_web tool. Use it to research modern documentation or existing technical solutions if the user's request involves unfamiliar technologies.",
        "developer": "\\n\\nYou have access to the read_file and edit_code tools to manipulate the workspace. Use code_runner to verify snippets of logic before committing them. Use search_web if you need to look up exact syntax or library documentation.",
        "code-reviewer": "\\n\\nYou have access to the lint_code tool. ALWAYS run it on the generated files before providing your final review. Use read_file to inspect the full context of files.",
        "security-reviewer": "\\n\\nYou have access to the lint_code tool. ALWAYS run it on the generated files before providing your final review. Use read_file to inspect the full context of files.",
        "testing-agent": "\\n\\nYou have access to the read_file and edit_code tools. Use code_runner to execute the tests you generate and ensure they actually pass against the codebase.",
        "deployment-agent": "\\n\\nYou have access to the read_file and edit_code tools to inspect and write deployment configurations.",
        "compliance-agent": "\\n\\nYou have access to the lint_code tool and read_file tool to inspect the full context of files for compliance.",
        "debt-scanner": "\\n\\nYou have access to the lint_code tool and read_file tool to inspect the full context of files for architectural issues.",
        "product-manager": "\\n\\nYou have access to the search_web tool to research market standards and competitors.",
        "ux-designer": "\\n\\nYou have access to the search_web tool to research design trends and modern UI frameworks."
    }

    cursor.execute("SELECT id, name FROM tools")
    db_tools = {row['name']: row['id'] for row in cursor.fetchall()}
    cursor.execute("DELETE FROM agent_tools")
    cursor.execute("SELECT id, name, system_prompt FROM agents")
    db_agents = cursor.fetchall()

    for agent in db_agents:
        agent_id = agent['id']
        agent_name = agent['name']
        if agent_name in agent_tool_prompts:
            prompt_suffix = agent_tool_prompts[agent_name]
            current_prompt = agent['system_prompt']
            if prompt_suffix not in current_prompt:
                new_prompt = current_prompt + prompt_suffix
                cursor.execute("UPDATE agents SET system_prompt = ? WHERE id = ?", (new_prompt, agent_id))
        if agent_name in agent_tools_map:
            for tool_name in agent_tools_map[agent_name]:
                if tool_name in db_tools:
                    cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)", (agent_id, db_tools[tool_name]))
'''

if "Updated Tool:" in content:
    idx = content.find('print(f"Updated Tool: {tool[\'name\']}")')
    if idx != -1:
        insert_idx = content.find('\n', idx) + 1
        new_content = content[:insert_idx] + tool_mapping_logic + content[insert_idx:]
        with open('c:/Projects/swe-agent/backend/seed.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Patched seed.py")
else:
    print("Could not find insertion point")
