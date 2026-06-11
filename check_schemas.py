import sqlite3, json

conn = sqlite3.connect('backend/swe_agent.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT id, name, output_schema FROM agents').fetchall()
for r in rows:
    schema = r['output_schema']
    print(f"  {r['id']:3}  {r['name']:30}  schema={'NULL' if not schema else schema[:120]}")
conn.close()
