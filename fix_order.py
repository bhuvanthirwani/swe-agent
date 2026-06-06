with open('c:/Projects/swe-agent/backend/seed.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('cursor.execute("DELETE FROM agents")', 'cursor.execute("DELETE FROM agent_tools")\n    cursor.execute("DELETE FROM agents")')

with open('c:/Projects/swe-agent/backend/seed.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed deletion order')
