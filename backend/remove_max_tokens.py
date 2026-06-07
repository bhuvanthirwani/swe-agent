import re

with open('backend/seed.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove '"max_tokens": 2048'
content = re.sub(r',\s*"max_tokens":\s*\d+', '', content)

# Remove 'max_tokens INTEGER' from ALTER TABLE
content = re.sub(r'cursor\.execute\("ALTER TABLE agents ADD COLUMN max_tokens INTEGER"\)', '', content)
content = re.sub(r"if 'max_tokens' not in columns:", '', content)

# Remove from INSERT INTO agents (...) VALUES (...)
content = re.sub(r', max_tokens', '', content)
content = re.sub(r'agent\.get\("max_tokens"\), ', '', content)
content = re.sub(r'agent\.get\("max_tokens"\)', '', content)

# Remove the trailing comma and extra placeholder from VALUES
content = content.replace(', ?)', ')')
content = content.replace('color = ?, max_tokens = ?', 'color = ?')

with open('backend/seed.py', 'w', encoding='utf-8') as f:
    f.write(content)

