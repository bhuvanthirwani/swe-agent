import os

seed_append = """
    # 5. Seed Connectors
    connectors = [
        {"id": "slack", "type": "slack", "name": "Slack", "description": "Send pipeline results and notifications to Slack channels", "icon": "💬", "enabled": False, "config": "{}"},
        {"id": "github", "type": "github", "name": "GitHub", "description": "Push generated code to repositories, create PRs, and listen for issues", "icon": "🐙", "enabled": False, "config": "{}"},
        {"id": "email", "type": "email", "name": "Email (SMTP)", "description": "Send pipeline results and audit reports via email", "icon": "📧", "enabled": False, "config": "{}"},
        {"id": "webhook", "type": "webhook", "name": "Custom Webhook", "description": "Send pipeline events to any HTTP endpoint", "icon": "🔗", "enabled": False, "config": "{}"},
        {"id": "discord", "type": "discord", "name": "Discord", "description": "Send pipeline notifications to Discord channels", "icon": "🎮", "enabled": False, "config": "{}"}
    ]
    for conn_data in connectors:
        cursor.execute("SELECT id FROM connectors WHERE id = ?", (conn_data["id"],))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO connectors (id, type, name, description, icon, enabled, config) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (conn_data["id"], conn_data["type"], conn_data["name"], conn_data["description"], conn_data["icon"], conn_data["enabled"], conn_data["config"]))
        else:
            cursor.execute("UPDATE connectors SET type=?, name=?, description=?, icon=? WHERE id=?", 
                           (conn_data["type"], conn_data["name"], conn_data["description"], conn_data["icon"], conn_data["id"]))

    # 6. Seed Roles & Permissions
    roles = {
        "admin": ["*"],
        "developer": ["read:projects", "write:projects", "execute:pipeline", "read:logs"],
        "viewer": ["read:projects", "read:logs"]
    }
    for role_id, perms in roles.items():
        cursor.execute("SELECT id FROM roles WHERE id = ?", (role_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO roles (id, description) VALUES (?, ?)", (role_id, f"{role_id.capitalize()} Role"))
        cursor.execute("DELETE FROM role_permissions WHERE role_id = ?", (role_id,))
        for p in perms:
            cursor.execute("INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)", (role_id, p))

    # 7. Seed Language Skills
    language_skills = [
        {"id": "typescript", "name": "TypeScript", "file_extensions": '["ts", "tsx"]', "run_command": "npx ts-node {file}", "lint_command": "npx eslint {file}", "test_command": "npx jest {file}"},
        {"id": "python", "name": "Python", "file_extensions": '["py"]', "run_command": "python {file}", "lint_command": "flake8 {file}", "test_command": "pytest {file}"},
        {"id": "go", "name": "Go", "file_extensions": '["go"]', "run_command": "go run {file}", "lint_command": "golangci-lint run {file}", "test_command": "go test {file}"},
        {"id": "rust", "name": "Rust", "file_extensions": '["rs"]', "run_command": "cargo run", "lint_command": "cargo clippy", "test_command": "cargo test"},
        {"id": "javascript", "name": "JavaScript", "file_extensions": '["js", "jsx"]', "run_command": "node {file}", "lint_command": "npx eslint {file}", "test_command": "npx jest {file}"}
    ]
    for skill in language_skills:
        cursor.execute("SELECT id FROM language_skills WHERE id = ?", (skill["id"],))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO language_skills (id, name, file_extensions, run_command, lint_command, test_command) VALUES (?, ?, ?, ?, ?, ?)",
                           (skill["id"], skill["name"], skill["file_extensions"], skill["run_command"], skill["lint_command"], skill["test_command"]))

    # 8. Seed RAG Knowledge Base
    kb_chunks = [
        {"id": "kb-1", "title": "Next.js App Router Architecture", "content": "The system uses Next.js App Router for server-side rendering...", "category": "architecture", "tags": '["frontend", "nextjs"]'},
        {"id": "kb-2", "title": "Multi-Agent Database Schema", "content": "The core orchestration relies on an SQLite database mapping tasks to agents...", "category": "architecture", "tags": '["backend", "database"]'},
        {"id": "kb-3", "title": "Deployment Guidelines", "content": "All production deployments must include a Dockerfile and docker-compose.yml.", "category": "devops", "tags": '["deployment", "docker"]'}
    ]
    for kb in kb_chunks:
        cursor.execute("SELECT id FROM knowledge_base WHERE id = ?", (kb["id"],))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO knowledge_base (id, title, content, category, tags) VALUES (?, ?, ?, ?, ?)",
                           (kb["id"], kb["title"], kb["content"], kb["category"], kb["tags"]))
"""

with open('backend/seed.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Insert before conn.commit() conn.close() print("Database seeding completed successfully!")
target_str = "    conn.commit()\n    conn.close()\n    print(\"Database seeding completed successfully!\")"
if target_str in content:
    content = content.replace(target_str, seed_append + "\n" + target_str)
    with open('backend/seed.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Seed data successfully appended to backend/seed.py")
else:
    print("Failed to find target string in backend/seed.py")
