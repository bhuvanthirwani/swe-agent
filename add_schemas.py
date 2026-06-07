import json

input_schemas = {
    "code-reviewer": {"type": "object", "properties": {"code": {"type": "string", "description": "The source code to review"}}, "required": ["code"]},
    "compliance-agent": {"type": "object", "properties": {"code": {"type": "string", "description": "The source code to review for compliance"}}, "required": ["code"]},
    "debt-scanner": {"type": "object", "properties": {"code": {"type": "string", "description": "The source code to scan for technical debt"}}, "required": ["code"]},
    "deployment-agent": {"type": "object", "properties": {"code": {"type": "string", "description": "The application code"}, "tech_stack": {"type": "array", "items": {"type": "string"}, "description": "The technical stack used in the application"}}, "required": ["code"]},
    "developer": {"type": "object", "properties": {"tasks": {"type": "array", "description": "List of development tasks to implement"}, "requirements": {"type": "object", "description": "The requirements for the development"}}, "required": ["tasks"]},
    "product-manager": {"type": "object", "properties": {"requirements": {"type": "string", "description": "The raw user requirements"}}, "required": ["requirements"]},
    "requirements-analyst": {"type": "object", "properties": {"raw_requirements": {"type": "string", "description": "The raw unstructured requirements"}}, "required": ["raw_requirements"]},
    "routerAgent": {"type": "object", "properties": {"user_request": {"type": "string", "description": "The user's initial request or prompt"}}, "required": ["user_request"]},
    "security-reviewer": {"type": "object", "properties": {"code": {"type": "string", "description": "The source code to analyze for security vulnerabilities"}}, "required": ["code"]},
    "task-planner": {"type": "object", "properties": {"requirements": {"type": "object", "description": "The structured requirements document"}}, "required": ["requirements"]},
    "testing-agent": {"type": "object", "properties": {"code": {"type": "string", "description": "The source code to write tests for"}, "tech_stack": {"type": "array", "description": "The technical stack"}}, "required": ["code"]},
    "ux-designer": {"type": "object", "properties": {"requirements": {"type": "object", "description": "The requirements to design UI/UX for"}}, "required": ["requirements"]},
    "github-suggestion-agent": {"type": "object", "properties": {"github_url": {"type": "string", "description": "The URL of the Github repository to analyze"}}, "required": ["github_url"]}
}

output_schemas = {
    "code-reviewer": {"type": "object", "properties": {"decision": {"type": "string", "enum": ["APPROVED", "CHANGES_REQUESTED"], "description": "The final decision on the code"}, "score": {"type": "integer", "description": "The code quality score out of 10"}, "summary": {"type": "string", "description": "A brief summary of the review"}, "issues": {"type": "array", "description": "List of issues found"}}, "required": ["decision", "score", "summary"]},
    "compliance-agent": {"type": "object", "properties": {"overallScore": {"type": "integer", "description": "The overall compliance score"}, "overallStatus": {"type": "string", "description": "The overall compliance status (PASS/FAIL/WARNING)"}, "summary": {"type": "string", "description": "A brief summary of compliance findings"}}, "required": ["overallScore", "overallStatus", "summary"]},
    "debt-scanner": {"type": "object", "properties": {"debtScore": {"type": "integer", "description": "The technical debt score"}, "grade": {"type": "string", "description": "The technical debt grade (A-F)"}, "summary": {"type": "string", "description": "Summary of technical debt"}}, "required": ["debtScore", "grade", "summary"]},
    "deployment-agent": {"type": "object", "properties": {"dockerfile": {"type": "string", "description": "The generated Dockerfile content"}, "docker_compose": {"type": "string", "description": "The generated docker-compose.yml content"}, "deployment_guide": {"type": "string", "description": "A guide on how to deploy the application"}}, "required": ["dockerfile"]},
    "developer": {"type": "object", "properties": {"code_files": {"type": "array", "items": {"type": "object"}, "description": "The array of generated code files"}, "summary": {"type": "string", "description": "Summary of the development work"}}, "required": ["code_files"]},
    "product-manager": {"type": "object", "properties": {"prd": {"type": "string", "description": "The generated Product Requirements Document"}, "user_stories": {"type": "array", "description": "List of generated user stories"}, "timeline": {"type": "string", "description": "The estimated timeline"}}, "required": ["prd", "user_stories"]},
    "requirements-analyst": {"type": "object", "properties": {"title": {"type": "string", "description": "The project title"}, "description": {"type": "string", "description": "The project description"}, "functional_requirements": {"type": "array", "description": "List of functional requirements"}, "acceptance_criteria": {"type": "array", "description": "List of acceptance criteria"}}, "required": ["title", "functional_requirements"]},
    "routerAgent": {"type": "object", "properties": {"mode": {"type": "string", "enum": ["FULL_PIPELINE", "QUICK_FIX", "PLAN_ONLY", "CODE_REVIEW_ONLY"], "description": "The selected pipeline mode"}, "reasoning": {"type": "string", "description": "The reasoning for the selection"}, "confidence": {"type": "number", "description": "Confidence score from 0.0 to 1.0"}}, "required": ["mode", "reasoning"]},
    "security-reviewer": {"type": "object", "properties": {"passed": {"type": "boolean", "description": "Whether the code passed the security review"}, "severity": {"type": "string", "description": "The severity level of the worst vulnerability found"}, "vulnerabilities": {"type": "array", "description": "List of vulnerabilities found"}, "summary": {"type": "string", "description": "A summary of the security review"}}, "required": ["passed", "severity", "vulnerabilities"]},
    "task-planner": {"type": "object", "properties": {"tasks": {"type": "array", "description": "The array of development tasks"}, "parallel_groups": {"type": "array", "description": "Tasks grouped for parallel execution"}, "total_complexity": {"type": "string", "description": "The total estimated complexity"}}, "required": ["tasks"]},
    "testing-agent": {"type": "object", "properties": {"test_files": {"type": "array", "description": "The generated test files"}, "summary": {"type": "string", "description": "Summary of the generated tests"}}, "required": ["test_files"]},
    "ux-designer": {"type": "object", "properties": {"design_system": {"type": "object", "description": "The comprehensive design system specifications"}, "component_library": {"type": "array", "description": "List of components with specs"}, "wireframes": {"type": "array", "description": "Page layout descriptions"}}, "required": ["design_system"]},
    "github-suggestion-agent": {"type": "object", "properties": {"feature_additions": {"type": "array", "description": "Suggested new features"}, "feature_modifications": {"type": "array", "description": "Suggested improvements to existing features"}, "security_concerns": {"type": "array", "description": "Identified security vulnerabilities or bad practices"}}, "required": ["feature_additions"]}
}

with open('new_agents.json', 'r', encoding='utf-8') as f:
    agents = json.load(f)

for agent in agents:
    name = agent['name']
    if name in input_schemas:
        agent['input_schema'] = json.dumps(input_schemas[name])
    if name in output_schemas:
        agent['output_schema'] = json.dumps(output_schemas[name])

with open('new_agents.json', 'w', encoding='utf-8') as f:
    json.dump(agents, f, indent=2)

print("Added descriptions and schemas to new_agents.json")
