import json

new_agents = json.load(open('c:/Projects/swe-agent/new_agents.json', encoding='utf-8'))

with open('c:/Projects/swe-agent/backend/seed.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace everything from "    agents = [" to "cursor.execute(\"DELETE FROM agent_llms\")"
start_str = "    agents = ["
end_str = "    cursor.execute(\"DELETE FROM agent_llms\")"

if start_str in content and end_str in content:
    idx_start = content.find(start_str)
    idx_end = content.find(end_str)
    
    # build the new agents_py string
    agents_py = '    agents = ' + json.dumps(new_agents, indent=8) + '\n\n'
    
    # Ensure booleans in json.dumps (like true/false) don't break Python if it expects True/False?
    # Wait! json.dumps generates valid JSON, but Python expects True/False for booleans.
    # Actually, json.dumps outputs valid Python dictionaries if we don't have true/false/null.
    # The agents dict only has strings, so json.dumps output is 100% valid Python!
    
    new_content = content[:idx_start] + agents_py + content[idx_end:]
    
    with open('c:/Projects/swe-agent/backend/seed.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed seed.py")
else:
    print("Could not find blocks")
