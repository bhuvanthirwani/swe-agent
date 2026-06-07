import os

filepath = 'frontend/src/app/page.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "import { saveToHistory }" in line:
        continue
    if "import { loadMemory, updateMemory, extractPreferencesFromAnalystOutput }" in line:
        continue
    if "saveToHistory(" in line:
        continue
    new_lines.append(line)

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

