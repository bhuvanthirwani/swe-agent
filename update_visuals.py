import json

visual_configs = {
  'router-agent': {'display_name': 'Router / Classifier', 'icon': '🧭', 'color': '#f43f5e', 'max_tokens': 512},
  'requirements-analyst': {'display_name': 'Requirements Analyst', 'icon': '🔍', 'color': '#6366f1', 'max_tokens': 2048},
  'task-planner': {'display_name': 'Task Planner', 'icon': '📋', 'color': '#8b5cf6', 'max_tokens': 2048},
  'developer': {'display_name': 'Developer Agent', 'icon': '💻', 'color': '#06b6d4', 'max_tokens': 4096},
  'code-reviewer': {'display_name': 'Code Reviewer', 'icon': '🔎', 'color': '#f59e0b', 'max_tokens': 2048},
  'security-reviewer': {'display_name': 'Security Reviewer', 'icon': '🛡️', 'color': '#ef4444', 'max_tokens': 3072},
  'testing-agent': {'display_name': 'Testing Agent', 'icon': '🧪', 'color': '#ec4899', 'max_tokens': 3072},
  'deployment-agent': {'display_name': 'Deployment Agent', 'icon': '🚀', 'color': '#10b981', 'max_tokens': 2048},
  'product-manager': {'display_name': 'Product Manager', 'icon': '📊', 'color': '#f59e0b', 'max_tokens': 2048},
  'ux-designer': {'display_name': 'UX/UI Designer', 'icon': '🎨', 'color': '#ec4899', 'max_tokens': 2048},
  'github-suggestion-agent': {'display_name': 'GitHub Suggestion Agent', 'icon': '🐙', 'color': '#3b82f6', 'max_tokens': 3072},
  'compliance-agent': {'display_name': 'Compliance Agent', 'icon': '⚖️', 'color': '#8b5cf6', 'max_tokens': 2048},
  'debt-scanner': {'display_name': 'Debt Scanner', 'icon': '💳', 'color': '#ef4444', 'max_tokens': 2048},
}

with open('new_agents.json', 'r', encoding='utf-8') as f:
    agents = json.load(f)

for agent in agents:
    name = agent['name']
    if name in visual_configs:
        agent.update(visual_configs[name])

with open('new_agents.json', 'w', encoding='utf-8') as f:
    json.dump(agents, f, indent=2)

print("Updated new_agents.json with visual configs")
