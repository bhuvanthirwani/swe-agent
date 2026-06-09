import sys
import os

file_path = r'c:\Projects\swe-agent\frontend\src\components\VisualEditor.tsx'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace escaped backticks
content = content.replace('\\`', '`')
# Replace escaped dollar signs
content = content.replace('\\${', '${')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed escaped template literals in VisualEditor.tsx')
