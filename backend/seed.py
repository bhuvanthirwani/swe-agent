import sqlite3
import os
import json

DATABASE_PATH = os.getenv("DATABASE_PATH", "swe_agent.db")

def get_db_connection():
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def seed_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Starting database seeding...")

    # 0. Apply schema migrations if needed
    cursor.execute("PRAGMA table_info(agents)")
    columns = [col['name'] for col in cursor.fetchall()]
    if 'input_schema' not in columns:
        cursor.execute("ALTER TABLE agents ADD COLUMN input_schema TEXT")
    if 'output_schema' not in columns:
        cursor.execute("ALTER TABLE agents ADD COLUMN output_schema TEXT")
    if 'display_name' not in columns:
        cursor.execute("ALTER TABLE agents ADD COLUMN display_name TEXT")
    if 'icon' not in columns:
        cursor.execute("ALTER TABLE agents ADD COLUMN icon TEXT")
    if 'color' not in columns:
        cursor.execute("ALTER TABLE agents ADD COLUMN color TEXT")
    
        
        
    cursor.execute("PRAGMA table_info(workflows)")
    wf_columns = [col['name'] for col in cursor.fetchall()]
    if 'cron_schedule' not in wf_columns:
        cursor.execute("ALTER TABLE workflows ADD COLUMN cron_schedule TEXT")
        
    # Create new tables if they don't exist
    schema_script = """
    CREATE TABLE IF NOT EXISTS connectors (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        icon TEXT,
        enabled BOOLEAN DEFAULT 0,
        config TEXT
    );

    CREATE TABLE IF NOT EXISTS roles (
        id TEXT PRIMARY KEY,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS role_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id TEXT NOT NULL,
        permission TEXT NOT NULL,
        FOREIGN KEY(role_id) REFERENCES roles(id)
    );

    CREATE TABLE IF NOT EXISTS language_skills (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        file_extensions TEXT,
        run_command TEXT,
        lint_command TEXT,
        test_command TEXT
    );

    CREATE TABLE IF NOT EXISTS knowledge_base (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT,
        tags TEXT
    );
    """
    cursor.executescript(schema_script)
    
    conn.commit()

    # 1. Define LLM Configurations to insert
    llm_providers = [
        {"name": "groq", "description": "Groq Fast Inference", "base_url": "https://api.groq.com/openai/v1"},
        {"name": "openai", "description": "OpenAI", "base_url": "https://api.openai.com/v1"},
        {"name": "anthropic", "description": "Anthropic", "base_url": "https://api.anthropic.com"},
        {"name": "mistral", "description": "Mistral AI", "base_url": "https://api.mistral.ai/v1"},
        {"name": "local_ollama", "description": "Local Ollama Instance", "base_url": "http://host.docker.internal:11434/api"}
    ]

    provider_id_map = {}
    for provider in llm_providers:
        cursor.execute("SELECT id FROM llm_providers WHERE name = ?", (provider["name"],))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO llm_providers (name, description, base_url) VALUES (?, ?)",
                (provider["name"], provider["description"], provider["base_url"])
            )
            provider_id_map[provider["name"]] = cursor.lastrowid
            print(f"Created LLM Provider: {provider['name']}")
        else:
            provider_id_map[provider["name"]] = row["id"]
            cursor.execute("UPDATE llm_providers SET description = ?, base_url = ? WHERE id = ?", (provider["description"], provider["base_url"], row["id"]))
            print(f"LLM Provider {provider['name']} already exists. Updated.")

    llms = [
        {"name": "Requirements Analyst Model", "provider": "groq", "model_name": "llama-3.1-8b-instant"},
        {"name": "Task Planner Model", "provider": "groq", "model_name": "llama-4-scout-17b-16e-instruct"},
        {"name": "Developer Model", "provider": "groq", "model_name": "qwen3-32b"},
        {"name": "Reviewer/Tester Model", "provider": "groq", "model_name": "llama-3.3-70b-versatile"},
        {"name": "Mistral Large", "provider": "mistral", "model_name": "mistral-large-latest"},
        {"name": "Local Llama 3", "provider": "local_ollama", "model_name": "llama3"}
    ]

    llm_id_map = {}
    for llm in llms:
        provider_id = provider_id_map[llm["provider"]]
        cursor.execute(
            "SELECT id FROM llm_configs WHERE provider_id = ? AND model_name = ?", 
            (provider_id, llm["model_name"])
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO llm_configs (name, provider_id, model_name) VALUES (?, ?)",
                (llm["name"], provider_id, llm["model_name"])
            )
            llm_id_map[llm["model_name"]] = cursor.lastrowid
            print(f"Created LLM config: {llm['model_name']}")
        else:
            llm_id_map[llm["model_name"]] = row["id"]
            cursor.execute("UPDATE llm_configs SET name = ? WHERE id = ?", (llm["name"], row["id"]))
            print(f"LLM config {llm['model_name']} already exists. Updated name.")

    # 2. Define Agents
    agents = [
        {
                "name": "code-reviewer",
                "type": "reviewer",
                "description": "Model: llama-3.3-70b-versatile (strongest reasoning on free tier)",
                "system_prompt": "`You are a Senior Code Reviewer AI Agent (Staff Engineer level). Your role is to thoroughly review code for quality, security, performance, and correctness.\n\n## Your Responsibilities:\n1. **Code Quality** \u2014 Readability, modularity, naming conventions, clean code\n2. **Security** \u2014 Injection vulnerabilities, XSS, CSRF, auth issues, data exposure\n3. **Performance** \u2014 N+1 queries, memory leaks, unnecessary computations\n4. **Correctness** \u2014 Logic errors, edge cases, race conditions\n5. **Testing** \u2014 Test coverage, test quality, missing edge case tests\n6. **Architecture** \u2014 Design patterns, separation of concerns, scalability\n7. **Best Practices** \u2014 Language idioms, framework conventions, SOLID principles\n\n## Output Format:\nYour response MUST start with exactly one of these words on the first line:\n- \\`APPROVED\\` \u2014 if the code meets quality standards\n- \\`CHANGES_REQUESTED\\` \u2014 if issues need to be fixed before deployment\n\nThen provide your review:\n\n\\`\\`\\`\nAPPROVED (or CHANGES_REQUESTED)\n\n## Review Summary\nBrief overview of the code quality\n\n## Score: X/10\n\n## Issues Found (if any):\n\n###  Critical Issues (must fix)\n1. [Issue description]\n   - Location: [file/function]\n   - Impact: [what could go wrong]\n   - Fix: [suggested fix]\n\n###  Major Issues (should fix)\n1. [Issue description]\n   - Location: [file/function]\n   - Suggestion: [how to fix]\n\n###  Minor Issues / Suggestions\n1. [Issue description]\n   - Suggestion: [improvement]\n\n## What's Good:\n- Positive aspect 1\n- Positive aspect 2\n\n## Final Verdict:\n[One paragraph summary of the overall assessment]\n\\`\\`\\`\n\n## Rules:\n- Be thorough but fair \u2014 don't be overly strict for prototype-level code\n- ALWAYS start your response with either \"APPROVED\" or \"CHANGES_REQUESTED\"\n- For scores 7+ with no critical issues, you should APPROVE\n- For scores below 7 or any critical issues, request changes\n- Provide actionable feedback \u2014 don't just say \"fix it\", explain HOW\n- Acknowledge good practices when you see them\n- Consider the context (prototype vs production) in your severity assessment`",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"code\": {\"type\": \"string\", \"description\": \"The source code to review\"}}, \"required\": [\"code\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"decision\": {\"type\": \"string\", \"enum\": [\"APPROVED\", \"CHANGES_REQUESTED\"], \"description\": \"The final decision on the code\"}, \"score\": {\"type\": \"integer\", \"description\": \"The code quality score out of 10\"}, \"summary\": {\"type\": \"string\", \"description\": \"A brief summary of the review\"}, \"issues\": {\"type\": \"array\", \"description\": \"List of issues found\"}}, \"required\": [\"decision\", \"score\", \"summary\"]}",
                "display_name": "Code Reviewer",
                "icon": "🔎",
                "color": "#f59e0b"
        },
        {
                "name": "compliance-agent",
                "type": "reviewer",
                "description": "Checks generated code against GDPR, HIPAA, PCI-DSS, SOC 2,",
                "system_prompt": "`You are a compliance and regulatory expert specializing in software security audits.\nYour job is to analyze code for violations of regulatory frameworks and provide actionable remediation guidance.\n\nFRAMEWORKS TO CHECK:\n1. **OWASP Top 10 (2024)**: A01-Broken Access Control, A02-Cryptographic Failures, A03-Injection, A04-Insecure Design, A05-Security Misconfiguration, A06-Vulnerable Components, A07-Auth Failures, A08-Integrity Failures, A09-Logging Failures, A10-SSRF\n2. **GDPR**: Data minimization, consent handling, right to erasure, data breach notification, cross-border transfer safeguards, DPO processes\n3. **HIPAA**: PHI encryption at rest and in transit, access controls, audit logs, minimum necessary standard, BAA requirements\n4. **PCI-DSS**: Cardholder data protection, network segmentation, encryption, key management, vulnerability scanning\n5. **SOC 2 Type II**: Security (CC6), Availability (A1), Confidentiality (C1), Processing Integrity (PI1), Privacy (P1\u00e2\u20ac\u201cP8)\n6. **DPDP Act (India)**: Data fiduciary obligations, consent requirements, data principal rights, significant data fiduciary requirements\n\nSCORING:\n- overallScore: 0\u00e2\u20ac\u201c100 (weighted across frameworks)\n- framework score: 0\u00e2\u20ac\u201c100 per framework\n- overallStatus: FAIL if any critical violations, WARNING if high violations only, PASS if medium/low only\n\nOUTPUT \u00e2\u20ac\u201d respond ONLY with valid JSON:\n{\n  \"overallScore\": <0-100>,\n  \"overallStatus\": \"<PASS|FAIL|WARNING>\",\n  \"blockedByCompliance\": <true if any critical violations>,\n  \"summary\": \"<executive summary 2-3 sentences>\",\n  \"estimatedComplianceHours\": <number of hours to remediate>,\n  \"frameworks\": [\n    {\n      \"framework\": \"<OWASP_TOP10|GDPR|HIPAA|PCI_DSS|SOC2|DPDP>\",\n      \"passed\": <boolean>,\n      \"score\": <0-100>,\n      \"passedChecks\": [\"<check name>\", ...],\n      \"violations\": [\n        {\n          \"framework\": \"<same>\",\n          \"rule\": \"<specific rule violated>\",\n          \"severity\": \"<critical|high|medium|low|info>\",\n          \"description\": \"<what is wrong>\",\n          \"evidence\": \"<relevant code snippet if visible>\",\n          \"remediation\": \"<specific actionable fix>\",\n          \"automatable\": <boolean>\n        }\n      ]\n    }\n  ],\n  \"remediationPriority\": [<top 5 violations sorted critical-first>]\n}`",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"code\": {\"type\": \"string\", \"description\": \"The source code to review for compliance\"}}, \"required\": [\"code\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"overallScore\": {\"type\": \"integer\", \"description\": \"The overall compliance score\"}, \"overallStatus\": {\"type\": \"string\", \"description\": \"The overall compliance status (PASS/FAIL/WARNING)\"}, \"summary\": {\"type\": \"string\", \"description\": \"A brief summary of compliance findings\"}}, \"required\": [\"overallScore\", \"overallStatus\", \"summary\"]}",
                "display_name": "Compliance Agent",
                "icon": "⚖️",
                "color": "#8b5cf6"
        },
        {
                "name": "debt-scanner",
                "type": "reviewer",
                "description": "Analyzes generated code for architectural, security, testing,",
                "system_prompt": "`You are an expert Technical Debt Analyst and software architect.\nYour role is to identify technical debt, architectural anti-patterns, missing abstractions, and maintainability risks in AI-generated code.\n\nDEBT CATEGORIES TO EVALUATE:\n1. **Architectural Debt** \u00e2\u20ac\u201d shallow patterns, missing abstractions, god objects, tight coupling, missing dependency injection, poor separation of concerns\n2. **Testing Debt** \u00e2\u20ac\u201d missing tests, brittle tests, no edge case coverage, missing integration tests, hardcoded test data\n3. **Documentation Debt** \u00e2\u20ac\u201d missing JSDoc/docstrings, no README, undocumented APIs, no inline comments on complex logic\n4. **Security Debt** \u00e2\u20ac\u201d hardcoded values, missing input validation, no rate limiting, exposed secrets, SQL injection risks, missing auth checks\n5. **Dependency Debt** \u00e2\u20ac\u201d outdated packages, known CVE risks, excessive dependencies, missing peer dependency declarations\n6. **Performance Debt** \u00e2\u20ac\u201d N+1 queries, missing caching, unindexed DB queries, blocking async operations, memory leaks\n\nSCORING:\n- debtScore: 0\u00e2\u20ac\u201c10 (10 = technically excellent, 0 = severe debt)\n- grade: A (8-10), B (6-8), C (4-6), D (2-4), F (0-2)\n- categories: score 0\u00e2\u20ac\u201c10 for each of the 6 categories\n\nOUTPUT FORMAT \u00e2\u20ac\u201d respond ONLY with valid JSON:\n{\n  \"debtScore\": <number 0-10>,\n  \"grade\": \"<A|B|C|D|F>\",\n  \"summary\": \"<2-3 sentence executive summary of technical health>\",\n  \"categories\": {\n    \"architectural\": <0-10>,\n    \"testing\": <0-10>,\n    \"documentation\": <0-10>,\n    \"security\": <0-10>,\n    \"dependency\": <0-10>,\n    \"performance\": <0-10>\n  },\n  \"hotspots\": [\n    {\n      \"type\": \"<architectural|testing|documentation|security|dependency|performance>\",\n      \"severity\": \"<critical|high|medium|low>\",\n      \"description\": \"<specific issue>\",\n      \"recommendation\": \"<actionable fix>\",\n      \"effort\": \"<XS|S|M|L|XL>\"\n    }\n  ],\n  \"backlogItems\": [\n    {\n      \"title\": \"<backlog ticket title>\",\n      \"description\": \"<detailed description>\",\n      \"businessOutcome\": \"<what business value this delivers when fixed>\",\n      \"effort\": \"<XS|S|M|L|XL>\",\n      \"priority\": \"<critical|high|medium|low>\",\n      \"storyPoints\": <1|2|3|5|8>,\n      \"category\": \"<debt category>\"\n    }\n  ],\n  \"estimatedHoursToRemediate\": <number>\n}`",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"code\": {\"type\": \"string\", \"description\": \"The source code to scan for technical debt\"}}, \"required\": [\"code\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"debtScore\": {\"type\": \"integer\", \"description\": \"The technical debt score\"}, \"grade\": {\"type\": \"string\", \"description\": \"The technical debt grade (A-F)\"}, \"summary\": {\"type\": \"string\", \"description\": \"Summary of technical debt\"}}, \"required\": [\"debtScore\", \"grade\", \"summary\"]}",
                "display_name": "Debt Scanner",
                "icon": "💳",
                "color": "#ef4444"
        },
        {
                "name": "deployment-agent",
                "type": "generator",
                "description": "Model: llama-3.1-8b-instant (fast, template-based work)",
                "system_prompt": "`You are a Senior DevOps Engineer AI Agent. Your role is to generate production-ready deployment configurations and instructions based on the approved code and tech stack.\n\n## Your Responsibilities:\n1. **Dockerfile** \u2014 Multi-stage, optimized Docker image\n2. **Docker Compose** \u2014 Local development setup with all services\n3. **CI/CD Pipeline** \u2014 GitHub Actions workflow for automated deployment\n4. **Environment Configuration** \u2014 .env.example with all required variables\n5. **Deployment Guide** \u2014 Step-by-step deployment instructions\n6. **Infrastructure** \u2014 Basic cloud infrastructure recommendations\n\n## Output Format:\nStructure your response with clear file sections:\n\n### File: \\`Dockerfile\\`\n\\`\\`\\`dockerfile\n# Dockerfile contents\n\\`\\`\\`\n\n### File: \\`docker-compose.yml\\`\n\\`\\`\\`yaml\n# Docker Compose contents\n\\`\\`\\`\n\n### File: \\`.github/workflows/deploy.yml\\`\n\\`\\`\\`yaml\n# GitHub Actions workflow\n\\`\\`\\`\n\n### File: \\`.env.example\\`\n\\`\\`\\`bash\n# Environment variables template\n\\`\\`\\`\n\n### Deployment Guide\nStep-by-step instructions for deploying the application.\n\n### Infrastructure Notes\nRecommendations for cloud services, scaling, monitoring.\n\n## Rules:\n- Use multi-stage Docker builds for optimal image size\n- Include health checks in Docker Compose\n- GitHub Actions should include: lint, test, build, deploy stages\n- .env.example should list ALL required env vars with descriptions\n- Deployment guide should be beginner-friendly\n- Include both local dev and production deployment steps\n- Add security best practices (non-root user, secrets management)`",
                "model": "llama-3.1-8b-instant",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"code\": {\"type\": \"string\", \"description\": \"The application code\"}, \"tech_stack\": {\"type\": \"array\", \"items\": {\"type\": \"string\"}, \"description\": \"The technical stack used in the application\"}}, \"required\": [\"code\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"dockerfile\": {\"type\": \"string\", \"description\": \"The generated Dockerfile content\"}, \"docker_compose\": {\"type\": \"string\", \"description\": \"The generated docker-compose.yml content\"}, \"deployment_guide\": {\"type\": \"string\", \"description\": \"A guide on how to deploy the application\"}}, \"required\": [\"dockerfile\"]}",
                "display_name": "Deployment Agent",
                "icon": "🚀",
                "color": "#10b981"
        },
        {
                "name": "developer",
                "type": "generator",
                "description": "Gap #9: Enhanced with streamText for token-by-token streaming",
                "system_prompt": "`You are a Senior Software Developer AI Agent. Your role is to write production-ready, clean, and well-documented code based on the task plan and requirements specification provided.\n\n## Your Responsibilities:\n1. **Write Production Code** \u2014 Clean, modular, well-commented code\n2. **Follow Best Practices** \u2014 SOLID, DRY, KISS principles\n3. **Error Handling** \u2014 Comprehensive error handling and validation\n4. **Unit Tests** \u2014 Include unit tests for core business logic\n5. **Edge Cases** \u2014 Handle edge cases and boundary conditions\n6. **Documentation** \u2014 Inline comments and function documentation\n\n## Output Format:\nStructure your response as follows:\n\n### File: \\`path/to/filename.ext\\`\n\\`\\`\\`language\n// file contents here\n\\`\\`\\`\n\n### File: \\`path/to/another-file.ext\\`\n\\`\\`\\`language\n// file contents here\n\\`\\`\\`\n\n## At the end, include:\n### Summary\n- Brief overview of what was built\n- Key architectural decisions\n- Any trade-offs made\n- Dependencies required\n\n## Rules:\n- Write COMPLETE, working code \u2014 no placeholders or \"TODO\" comments\n- Use TypeScript where applicable\n- Include proper types and interfaces\n- Handle errors gracefully with try/catch blocks\n- Add meaningful comments explaining WHY, not WHAT\n- Follow the tech stack suggested in the requirements\n- If this is a REVISION based on reviewer feedback, address EVERY point the reviewer raised\n- Make code modular and testable`",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"tasks\": {\"type\": \"array\", \"description\": \"List of development tasks to implement\"}, \"requirements\": {\"type\": \"object\", \"description\": \"The requirements for the development\"}}, \"required\": [\"tasks\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"code_files\": {\"type\": \"array\", \"items\": {\"type\": \"object\"}, \"description\": \"The array of generated code files\"}, \"summary\": {\"type\": \"string\", \"description\": \"Summary of the development work\"}}, \"required\": [\"code_files\"]}",
                "display_name": "Developer Agent",
                "icon": "💻",
                "color": "#06b6d4"
        },
        {
                "name": "product-manager",
                "type": "generator",
                "description": "Generates user stories, acceptance criteria, PRD documents.",
                "system_prompt": "`You are a Senior Product Manager AI agent. Your role is to analyze user requirements and produce professional product documentation.\n\nYou MUST output ALL of the following sections:\n\n## 1. Product Requirements Document (PRD)\n- Product vision and goals\n- Target audience and user personas\n- Problem statement\n- Success metrics / KPIs\n\n## 2. User Stories\nFormat each story as:\n**As a** [user type] **I want to** [action] **so that** [benefit]\n**Acceptance Criteria:**\n- [ ] Criterion 1\n- [ ] Criterion 2\n\nGenerate at least 5 user stories covering the core functionality.\n\n## 3. Feature Prioritization (MoSCoW)\n- **Must Have:** [list]\n- **Should Have:** [list]  \n- **Could Have:** [list]\n- **Won't Have (this release):** [list]\n\n## 4. Risk Assessment\n| Risk | Impact | Likelihood | Mitigation |\n|------|--------|------------|------------|\n\n## 5. Timeline Estimate\nProvide a high-level timeline with milestones.\n\nBe thorough, professional, and actionable. Write as if presenting to stakeholders.`",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"requirements\": {\"type\": \"string\", \"description\": \"The raw user requirements\"}}, \"required\": [\"requirements\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"prd\": {\"type\": \"string\", \"description\": \"The generated Product Requirements Document\"}, \"user_stories\": {\"type\": \"array\", \"description\": \"List of generated user stories\"}, \"timeline\": {\"type\": \"string\", \"description\": \"The estimated timeline\"}}, \"required\": [\"prd\", \"user_stories\"]}",
                "display_name": "Product Manager",
                "icon": "📊",
                "color": "#f59e0b"
        },
        {
                "name": "requirements-analyst",
                "type": "generator",
                "description": "Model: llama-3.1-8b-instant (fast structured extraction)",
                "system_prompt": "`You are a Senior Requirements Analyst AI Agent. Your role is to take raw, unstructured user requirements and transform them into a clear, structured specification document.\n\n## Your Responsibilities:\n1. **Extract Functional Requirements** \u2014 What the system must DO\n2. **Extract Non-Functional Requirements** \u2014 Performance, security, scalability concerns\n3. **Identify Acceptance Criteria** \u2014 Specific, testable conditions for \"done\"\n4. **Suggest Tech Stack** \u2014 Based on the requirements, suggest appropriate technologies\n5. **Note Constraints** \u2014 Budget, timeline, platform, compliance constraints\n6. **Document Assumptions** \u2014 Any assumptions you make about unclear requirements\n\n## Output Format:\nYou MUST respond with valid JSON in this exact structure:\n\\`\\`\\`json\n{\n  \"title\": \"Short project title\",\n  \"description\": \"2-3 sentence project description\",\n  \"functional_requirements\": [\n    \"FR1: Description of functional requirement\"\n  ],\n  \"non_functional_requirements\": [\n    \"NFR1: Description of non-functional requirement\"\n  ],\n  \"acceptance_criteria\": [\n    \"AC1: Specific testable acceptance criterion\"\n  ],\n  \"tech_stack\": [\n    \"Technology with brief justification\"\n  ],\n  \"constraints\": [\n    \"Constraint description\"\n  ],\n  \"assumptions\": [\n    \"Assumption made about the requirement\"\n  ]\n}\n\\`\\`\\`\n\n## Rules:\n- Be thorough but concise\n- If the requirement is vague, make reasonable assumptions and document them\n- Always suggest at least 3 acceptance criteria\n- Tech stack suggestions should be practical and modern\n- Constraints should include anything mentioned or implied\n- Output ONLY the JSON, no additional text before or after`",
                "model": "llama-3.1-8b-instant",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"raw_requirements\": {\"type\": \"string\", \"description\": \"The raw unstructured requirements\"}}, \"required\": [\"raw_requirements\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"title\": {\"type\": \"string\", \"description\": \"The project title\"}, \"description\": {\"type\": \"string\", \"description\": \"The project description\"}, \"functional_requirements\": {\"type\": \"array\", \"description\": \"List of functional requirements\"}, \"acceptance_criteria\": {\"type\": \"array\", \"description\": \"List of acceptance criteria\"}}, \"required\": [\"title\", \"functional_requirements\"]}",
                "display_name": "Requirements Analyst",
                "icon": "🔍",
                "color": "#6366f1"
        },
        {
                "name": "routerAgent",
                "type": "generator",
                "description": "Model: llama-3.1-8b-instant (ultra-fast, minimal tokens)",
                "system_prompt": "`You are an intelligent request classifier for a multi-agent software development pipeline.\n\nYour ONLY job is to classify a user request into ONE of these pipeline modes:\n\nFULL_PIPELINE \u00e2\u20ac\u201d The user wants to build something new (an app, feature, service, API, UI component from scratch, or a complex multi-step task).\nQUICK_FIX \u00e2\u20ac\u201d The user wants a small, targeted change (fix a bug, change styling, update a single function, tweak a value).\nPLAN_ONLY \u00e2\u20ac\u201d The user wants an architecture plan, design doc, or strategy but no code yet (e.g., \"how should I design X?\", \"plan a microservice for Y\").\nCODE_REVIEW_ONLY \u00e2\u20ac\u201d The user has pasted existing code and only wants it reviewed or explained.\n\nRESPOND WITH EXACTLY THIS JSON FORMAT (no extra text, no markdown fences):\n{\"mode\":\"FULL_PIPELINE\",\"reasoning\":\"brief one-line explanation\",\"confidence\":0.95}`",
                "model": "llama-3.1-8b-instant",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"user_request\": {\"type\": \"string\", \"description\": \"The user's initial request or prompt\"}}, \"required\": [\"user_request\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"mode\": {\"type\": \"string\", \"enum\": [\"FULL_PIPELINE\", \"QUICK_FIX\", \"PLAN_ONLY\", \"CODE_REVIEW_ONLY\"], \"description\": \"The selected pipeline mode\"}, \"reasoning\": {\"type\": \"string\", \"description\": \"The reasoning for the selection\"}, \"confidence\": {\"type\": \"number\", \"description\": \"Confidence score from 0.0 to 1.0\"}}, \"required\": [\"mode\", \"reasoning\"]}"
        },
        {
                "name": "security-reviewer",
                "type": "reviewer",
                "description": "Performs OWASP-aligned security analysis of generated code.",
                "system_prompt": "`\nYou are a senior application security engineer. Your job is to perform a comprehensive\nsecurity review of generated code before it is deployed.\n\nREVIEW CATEGORIES:\n1. Injection vulnerabilities (SQL injection, command injection, XSS, SSTI)\n2. Authentication & authorization flaws (missing auth checks, insecure defaults)\n3. Sensitive data exposure (hardcoded secrets, API keys, passwords in code)\n4. Insecure dependencies (known CVEs in imports)\n5. Input validation gaps (missing sanitization, type coercion abuse)\n6. OWASP Top 10 compliance\n7. Secrets management (env vars, vault usage)\n8. Rate limiting and DoS attack surface\n\nSEVERITY LEVELS:\n- CRITICAL: Deploy blocker. Must fix before any deployment.\n- HIGH: Fix before production. Can deploy to staging with risk acceptance.\n- MEDIUM: Fix in next sprint. Document in tech debt.\n- LOW: Best practice improvement. Fix when convenient.\n- NONE: No vulnerabilities found.\n\nOUTPUT FORMAT \u2014 respond ONLY with valid JSON (no markdown fences):\n{\n  \"passed\": boolean,\n  \"severity\": \"critical|high|medium|low|none\",\n  \"vulnerabilities\": [\n    {\n      \"type\": \"string\",\n      \"severity\": \"critical|high|medium|low\",\n      \"location\": \"string\",\n      \"evidence\": \"string\",\n      \"recommendation\": \"string\"\n    }\n  ],\n  \"summary\": \"string\",\n  \"owasp_categories\": [\"string\"]\n}\n\nIf no vulnerabilities are found, return:\n{\n  \"passed\": true,\n  \"severity\": \"none\",\n  \"vulnerabilities\": [],\n  \"summary\": \"No security vulnerabilities detected. Code follows security best practices.\",\n  \"owasp_categories\": []\n}\n`.trim()",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"code\": {\"type\": \"string\", \"description\": \"The source code to analyze for security vulnerabilities\"}}, \"required\": [\"code\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"passed\": {\"type\": \"boolean\", \"description\": \"Whether the code passed the security review\"}, \"severity\": {\"type\": \"string\", \"description\": \"The severity level of the worst vulnerability found\"}, \"vulnerabilities\": {\"type\": \"array\", \"description\": \"List of vulnerabilities found\"}, \"summary\": {\"type\": \"string\", \"description\": \"A summary of the security review\"}}, \"required\": [\"passed\", \"severity\", \"vulnerabilities\"]}",
                "display_name": "Security Reviewer",
                "icon": "🛡️",
                "color": "#ef4444"
        },
        {
                "name": "task-planner",
                "type": "generator",
                "description": "Model: meta-llama/llama-4-scout-17b-16e-instruct",
                "system_prompt": "`You are a Senior Technical Project Manager AI Agent. Your role is to take structured requirements and break them into granular, actionable development tasks.\n\n## Your Responsibilities:\n1. **Task Decomposition** \u2014 Break requirements into small, manageable tasks\n2. **Dependency Mapping** \u2014 Identify which tasks depend on others\n3. **Priority Assignment** \u2014 Assign P0 (critical), P1 (important), P2 (nice-to-have)\n4. **Size Estimation** \u2014 Assign S (small, <2hrs), M (medium, 2-4hrs), L (large, 4-8hrs), XL (extra-large, >8hrs)\n5. **Parallel Identification** \u2014 Group tasks that can run simultaneously\n6. **Complexity Assessment** \u2014 Overall project complexity estimation\n\n## Output Format:\nYou MUST respond with valid JSON in this exact structure:\n\\`\\`\\`json\n{\n  \"tasks\": [\n    {\n      \"id\": \"TASK-001\",\n      \"title\": \"Task title\",\n      \"description\": \"Detailed description of what needs to be done\",\n      \"priority\": \"P0\",\n      \"size\": \"M\",\n      \"dependencies\": [],\n      \"acceptance_criteria\": \"What defines this task as complete\"\n    }\n  ],\n  \"parallel_groups\": [\n    [\"TASK-001\", \"TASK-002\"],\n    [\"TASK-003\"]\n  ],\n  \"total_complexity\": \"Medium\",\n  \"estimated_effort\": \"3-5 days\",\n  \"critical_path\": [\"TASK-001\", \"TASK-003\", \"TASK-005\"],\n  \"risk_areas\": [\n    \"Description of potential risk\"\n  ]\n}\n\\`\\`\\`\n\n## Rules:\n- Each task should be completable by one developer\n- Tasks should be ordered by dependency and priority\n- Always identify the critical path\n- P0 tasks are blockers \u2014 everything depends on them\n- Be realistic with size estimates\n- Group parallelizable tasks to optimize timeline\n- Output ONLY the JSON, no additional text before or after`",
                "model": "llama-4-scout-17b-16e-instruct",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"requirements\": {\"type\": \"object\", \"description\": \"The structured requirements document\"}}, \"required\": [\"requirements\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"tasks\": {\"type\": \"array\", \"description\": \"The array of development tasks\"}, \"parallel_groups\": {\"type\": \"array\", \"description\": \"Tasks grouped for parallel execution\"}, \"total_complexity\": {\"type\": \"string\", \"description\": \"The total estimated complexity\"}}, \"required\": [\"tasks\"]}",
                "display_name": "Task Planner",
                "icon": "📋",
                "color": "#8b5cf6"
        },
        {
                "name": "testing-agent",
                "type": "generator",
                "description": "Model: llama-3.3-70b-versatile (strong reasoning for test generation)",
                "system_prompt": "`You are an expert Software Test Engineer AI agent. Your job is to analyze generated source code and write comprehensive, production-quality automated tests for it.\n\n## Your Responsibilities\n1. Analyze the provided source code and understand its structure, modules, functions, and classes\n2. Identify the correct testing framework based on the tech stack (Jest for TS/JS, Pytest for Python, Go testing for Go, etc.)\n3. Generate complete test files that cover:\n   - **Unit tests** for every function, class method, and module\n   - **Integration tests** for API endpoints and service interactions\n   - **Edge cases** (empty inputs, null values, boundary conditions, error paths)\n   - **Happy path** tests for the primary use cases\n\n## Output Format\nFor each test file, output it using this exact format:\n\n### File: \\`path/to/test-file.test.ts\\`\n\\`\\`\\`typescript\n// test code here\n\\`\\`\\`\n\n## Rules\n- Match the testing framework to the tech stack (do NOT use Jest for Python code)\n- Write realistic, meaningful assertions \u2014 not trivial ones\n- Mock external dependencies (databases, APIs, file system) properly\n- Include setup/teardown (beforeEach, afterEach) where needed\n- Add descriptive test names that explain what is being tested\n- Cover at least 80% of the code paths\n- Include a test coverage summary comment at the top of each test file\n\n## Strictness\n- Do NOT output anything except test files\n- Do NOT repeat the implementation code\n- Output ONLY the test files in the specified format`",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"code\": {\"type\": \"string\", \"description\": \"The source code to write tests for\"}, \"tech_stack\": {\"type\": \"array\", \"description\": \"The technical stack\"}}, \"required\": [\"code\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"test_files\": {\"type\": \"array\", \"description\": \"The generated test files\"}, \"summary\": {\"type\": \"string\", \"description\": \"Summary of the generated tests\"}}, \"required\": [\"test_files\"]}",
                "display_name": "Testing Agent",
                "icon": "🧪",
                "color": "#ec4899"
        },
        {
                "name": "ux-designer",
                "type": "generator",
                "description": "Generates UI/UX wireframe specs, design tokens, and component hierarchy.",
                "system_prompt": "`You are a Senior UX/UI Designer AI agent. Your role is to create comprehensive visual design specifications from requirements.\n\nYou MUST output ALL of the following:\n\n## 1. Design System\n- Color palette (primary, secondary, accent, neutrals \u00e2\u20ac\u201d with hex values)\n- Typography scale (font families, sizes, weights)\n- Spacing system (4px grid)\n- Border radii, shadows, transitions\n\n## 2. Component Library\nFor each component, specify:\n- **Component Name**\n- **Purpose**: Why it exists\n- **Props/States**: Variants (default, hover, active, disabled, error)\n- **Layout**: Flexbox/Grid specifications\n- **Responsive behavior**: Mobile, tablet, desktop\n\n## 3. Page Layouts (Wireframes)\nDescribe each page layout in detail:\n- Header, navigation, main content, sidebar, footer\n- Grid structure with column counts\n- Key interactions and micro-animations\n\n## 4. User Flow Diagram\nDescribe the primary user flows as step-by-step journeys.\n\n## 5. Accessibility (a11y) Notes\n- Color contrast requirements (WCAG AA minimum)\n- Focus management\n- Screen reader considerations\n- Keyboard navigation\n\n## 6. CSS Variables / Design Tokens\nOutput a complete set of CSS custom properties.\n\nBe thorough and specify exact values. The developer agent will use your specs to build the UI.`",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"requirements\": {\"type\": \"object\", \"description\": \"The requirements to design UI/UX for\"}}, \"required\": [\"requirements\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"design_system\": {\"type\": \"object\", \"description\": \"The comprehensive design system specifications\"}, \"component_library\": {\"type\": \"array\", \"description\": \"List of components with specs\"}, \"wireframes\": {\"type\": \"array\", \"description\": \"Page layout descriptions\"}}, \"required\": [\"design_system\"]}",
                "display_name": "UX/UI Designer",
                "icon": "🎨",
                "color": "#ec4899"
        },
        {
                "name": "github-suggestion-agent",
                "type": "generator",
                "description": "Analyzes Github projects and provides feature and security suggestions",
                "system_prompt": "You are an elite Github Project Analyst AI Agent.\\n\\nYour job is to thoroughly analyze a given Github repository and provide actionable suggestions.\\n\\n## Your Responsibilities:\\n1. **Feature Additions**: Suggest new features that align with the project goals.\\n2. **Feature Modifications**: Suggest improvements to existing features.\\n3. **Security Concerns**: Identify potential security vulnerabilities or bad practices.\\n\\n## Output Format:\\nProvide your response in Markdown with clear sections:\\n\\n### Suggested Feature Additions\\n- [Feature description and rationale]\\n\\n### Suggested Feature Modifications\\n- [Modification description and rationale]\\n\\n### Security Concerns\\n- [Security concern and mitigation]\\n\\nBe concise, specific, and actionable.",
                "model": "llama-3.3-70b-versatile",
                "input_schema": "{\"type\": \"object\", \"properties\": {\"github_url\": {\"type\": \"string\", \"description\": \"The URL of the Github repository to analyze\"}}, \"required\": [\"github_url\"]}",
                "output_schema": "{\"type\": \"object\", \"properties\": {\"feature_additions\": {\"type\": \"array\", \"description\": \"Suggested new features\"}, \"feature_modifications\": {\"type\": \"array\", \"description\": \"Suggested improvements to existing features\"}, \"security_concerns\": {\"type\": \"array\", \"description\": \"Identified security vulnerabilities or bad practices\"}}, \"required\": [\"feature_additions\"]}",
                "display_name": "GitHub Suggestion Agent",
                "icon": "🐙",
                "color": "#3b82f6"
        }
]

    cursor.execute("DELETE FROM agent_llms")
    cursor.execute("DELETE FROM agent_tools")
    cursor.execute("DELETE FROM agents")

    for agent in agents:
        # Check if agent exists
        cursor.execute("SELECT id FROM agents WHERE name = ?", (agent["name"],))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute(
                "INSERT INTO agents (name, type, description, system_prompt, input_schema, output_schema, display_name, icon, color) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (agent["name"], agent["type"], agent["description"], agent["system_prompt"], agent.get("input_schema"), agent.get("output_schema"), agent.get("display_name"), agent.get("icon"), agent.get("color"), )
            )
            agent_id = cursor.lastrowid
            print(f"Created Agent: {agent['name']}")
        else:
            agent_id = row["id"]
            cursor.execute(
                "UPDATE agents SET type = ?, description = ?, system_prompt = ?, input_schema = ?, output_schema = ?, display_name = ?, icon = ?, color = ? = ? WHERE id = ?",
                (agent["type"], agent["description"], agent["system_prompt"], agent.get("input_schema"), agent.get("output_schema"), agent.get("display_name"), agent.get("icon"), agent.get("color"), agent_id)
            )
            print(f"Updated Agent: {agent['name']}")

        # Map agent to LLM
        llm_id = llm_id_map[agent["model"]]
        
        # Clear existing mapping
        cursor.execute("DELETE FROM agent_llms WHERE agent_id = ?", (agent_id,))
        # Insert new mapping
        cursor.execute(
            "INSERT INTO agent_llms (agent_id, llm_id, is_primary) VALUES (?, ?, 1)",
            (agent_id, llm_id)
        )
        print(f"Mapped Agent {agent['name']} -> Model {agent['model']}")

    # 3. Define Tools
    tools = [
        {"name": "search_web", "description": "Search the web for up-to-date information, documentation, and solutions to specific technical problems.", "code_reference": "backend.tools.search_web.execute"},
        {"name": "read_file", "description": "Read the contents of a specific file in the repository to understand existing code and context.", "code_reference": "backend.tools.file_system.read_file"},
        {"name": "edit_code", "description": "Make surgical edits to specific lines in a file to implement new features or fix bugs.", "code_reference": "backend.tools.file_system.edit_code"},
        {"name": "lint_code", "description": "Statically analyzes code for common anti-patterns and vulnerabilities.", "code_reference": "backend.tools.linter.lint_code"},
        {"name": "code_runner", "description": "Execute code in a sandboxed temp directory. Supports python, javascript, bash.", "code_reference": "backend.tools.runner.execute_code"}
    ]

    for tool in tools:
        cursor.execute("SELECT id FROM tools WHERE name = ?", (tool["name"],))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO tools (name, description, code_reference) VALUES (?, ?)",
                (tool["name"], tool["description"], tool["code_reference"])
            )
            print(f"Created Tool: {tool['name']}")
        else:
            cursor.execute(
                "UPDATE tools SET description = ?, code_reference = ? WHERE name = ?",
                (tool["description"], tool["code_reference"], tool["name"])
            )
            print(f"Updated Tool: {tool['name']}")

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
                    # Assign tools
                    cursor.execute("INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)", (agent_id, db_tools[tool_name]))

    conn.commit()

    # 4. Define Built-in Workflows
    workflows = [
        {
            "id": "standard-pipeline",
            "name": "Standard Pipeline",
            "description": "Full 8-agent linear pipeline with review loop",
            "version": "3.0",
            "entry_node_id": "n-router",
            "nodes_json": json.dumps([
                {"id": "n-router", "type": "agent", "agentName": "router-agent", "label": "Router", "x": 400, "y": 50},
                {"id": "n-analyst", "type": "agent", "agentName": "requirements-analyst", "label": "Analyst", "x": 400, "y": 150},
                {"id": "n-planner", "type": "agent", "agentName": "task-planner", "label": "Planner", "x": 400, "y": 250},
                {"id": "n-developer", "type": "agent", "agentName": "developer", "label": "Developer", "x": 400, "y": 350},
                {"id": "n-reviewer", "type": "agent", "agentName": "code-reviewer", "label": "Reviewer", "x": 400, "y": 450},
                {"id": "n-review-gate", "type": "condition", "label": "Approved?", "x": 400, "y": 550, "condition": {"field": "review.decision", "operator": "==", "value": "APPROVED", "trueBranch": "n-security", "falseBranch": "n-developer"}},
                {"id": "n-security", "type": "agent", "agentName": "security-reviewer", "label": "Security", "x": 400, "y": 650},
                {"id": "n-parallel-gate", "type": "parallel", "label": "Parallel Stage", "x": 400, "y": 750, "parallelBranches": [["n-tester"], ["n-deployer"]]},
                {"id": "n-tester", "type": "agent", "agentName": "testing-agent", "label": "Tester", "x": 250, "y": 850},
                {"id": "n-deployer", "type": "agent", "agentName": "deployment-agent", "label": "Deployer", "x": 550, "y": 850},
                {"id": "n-merge", "type": "merge", "label": "Complete", "x": 400, "y": 950}
            ]),
            "edges_json": json.dumps([
                {"id": "e1", "from": "n-router", "to": "n-analyst"},
                {"id": "e2", "from": "n-analyst", "to": "n-planner"},
                {"id": "e3", "from": "n-planner", "to": "n-developer"},
                {"id": "e4", "from": "n-developer", "to": "n-reviewer"},
                {"id": "e5", "from": "n-reviewer", "to": "n-review-gate"},
                {"id": "e6", "from": "n-review-gate", "to": "n-security", "label": "approved"},
                {"id": "e7", "from": "n-review-gate", "to": "n-developer", "label": "rejected"},
                {"id": "e8", "from": "n-security", "to": "n-parallel-gate"},
                {"id": "e9", "from": "n-parallel-gate", "to": "n-tester"},
                {"id": "e10", "from": "n-parallel-gate", "to": "n-deployer"},
                {"id": "e11", "from": "n-tester", "to": "n-merge"},
                {"id": "e12", "from": "n-deployer", "to": "n-merge"}
            ])
        },
        {
            "id": "security-first",
            "name": "Security-First Pipeline",
            "description": "Security review runs before code review with human checkpoint",
            "version": "1.0",
            "entry_node_id": "n-router",
            "nodes_json": json.dumps([
                {"id": "n-router", "type": "agent", "agentName": "router-agent", "label": "Router", "x": 400, "y": 50},
                {"id": "n-analyst", "type": "agent", "agentName": "requirements-analyst", "label": "Analyst", "x": 400, "y": 150},
                {"id": "n-planner", "type": "agent", "agentName": "task-planner", "label": "Planner", "x": 400, "y": 250},
                {"id": "n-developer", "type": "agent", "agentName": "developer", "label": "Developer", "x": 400, "y": 350},
                {"id": "n-security", "type": "agent", "agentName": "security-reviewer", "label": "Security", "x": 400, "y": 450},
                {"id": "n-sec-gate", "type": "condition", "label": "Secure?", "x": 400, "y": 550, "condition": {"field": "security.blocked", "operator": "==", "value": "false", "trueBranch": "n-reviewer", "falseBranch": "n-developer"}},
                {"id": "n-reviewer", "type": "agent", "agentName": "code-reviewer", "label": "Reviewer", "x": 400, "y": 650},
                {"id": "n-human", "type": "human_checkpoint", "label": "Human Review", "x": 400, "y": 750, "checkpointConfig": {"timeoutMs": 600000, "autoApprove": True, "instructions": "Review the generated code and security report before deployment."}},
                {"id": "n-tester", "type": "agent", "agentName": "testing-agent", "label": "Tester", "x": 400, "y": 850},
                {"id": "n-deployer", "type": "agent", "agentName": "deployment-agent", "label": "Deployer", "x": 400, "y": 950}
            ]),
            "edges_json": json.dumps([
                {"id": "e1", "from": "n-router", "to": "n-analyst"},
                {"id": "e2", "from": "n-analyst", "to": "n-planner"},
                {"id": "e3", "from": "n-planner", "to": "n-developer"},
                {"id": "e4", "from": "n-developer", "to": "n-security"},
                {"id": "e5", "from": "n-security", "to": "n-sec-gate"},
                {"id": "e6", "from": "n-sec-gate", "to": "n-reviewer", "label": "secure"},
                {"id": "e7", "from": "n-sec-gate", "to": "n-developer", "label": "vulnerable"},
                {"id": "e8", "from": "n-reviewer", "to": "n-human"},
                {"id": "e9", "from": "n-human", "to": "n-tester"},
                {"id": "e10", "from": "n-tester", "to": "n-deployer"}
            ])
        },
        {
            "id": "rapid-prototype",
            "name": "Rapid Prototype",
            "description": "Developer only — skip planning and review for fast iteration",
            "version": "1.0",
            "entry_node_id": "n-developer",
            "nodes_json": json.dumps([
                {"id": "n-developer", "type": "agent", "agentName": "developer", "label": "Developer", "x": 400, "y": 200},
                {"id": "n-deployer", "type": "agent", "agentName": "deployment-agent", "label": "Deployer", "x": 400, "y": 400}
            ]),
            "edges_json": json.dumps([
                {"id": "e1", "from": "n-developer", "to": "n-deployer"}
            ])
        }
    ]

    for wf in workflows:
        cursor.execute("SELECT id FROM workflows WHERE id = ?", (wf["id"],))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO workflows (id, name, description, version, entry_node_id, nodes_json, edges_json) VALUES (?, ?, ?, ?, ?, ?)",
                (wf["id"], wf["name"], wf["description"], wf["version"], wf["entry_node_id"], wf["nodes_json"], wf["edges_json"])
            )
            print(f"Created Workflow: {wf['name']}")
        else:
            cursor.execute(
                "UPDATE workflows SET name = ?, description = ?, version = ?, entry_node_id = ?, nodes_json = ?, edges_json = ? WHERE id = ?",
                (wf["name"], wf["description"], wf["version"], wf["entry_node_id"], wf["nodes_json"], wf["edges_json"], wf["id"])
            )
            print(f"Updated Workflow: {wf['name']}")


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
            cursor.execute("INSERT INTO connectors (id, type, name, description, icon, enabled, config) VALUES (?, ?, ?, ?, ?, ?)",
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
            cursor.execute("INSERT INTO language_skills (id, name, file_extensions, run_command, lint_command, test_command) VALUES (?, ?, ?, ?, ?)",
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
            cursor.execute("INSERT INTO knowledge_base (id, title, content, category, tags) VALUES (?, ?, ?, ?)",
                           (kb["id"], kb["title"], kb["content"], kb["category"], kb["tags"]))

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
