import re

RULES = [
    {"id": "no-eval", "severity": "error", "pattern": re.compile(r"\\beval\\s*\\("), "message": "Avoid eval() — severe security risk"},
    {"id": "no-inner-html", "severity": "warning", "pattern": re.compile(r"\\.innerHTML\\s*="), "message": "innerHTML assignment risks XSS"},
    {"id": "no-dangerously-html", "severity": "warning", "pattern": re.compile(r"dangerouslySetInnerHTML"), "message": "dangerouslySetInnerHTML can expose XSS"},
    {"id": "no-hardcoded-secret", "severity": "error", "pattern": re.compile(r"(?:api_?key|secret|password|token)\\s*[:=]\\s*[\"'][^\"']{6,}", re.IGNORECASE), "message": "Hardcoded secret detected"},
    {"id": "no-console", "severity": "info", "pattern": re.compile(r"console\\.(log|warn|error|debug)\\("), "message": "Remove console.log before production"},
    {"id": "no-todo", "severity": "info", "pattern": re.compile(r"//\\s*TODO|//\\s*FIXME|//\\s*HACK", re.IGNORECASE), "message": "Unaddressed TODO comment found"},
    {"id": "no-any", "severity": "warning", "pattern": re.compile(r":\\s*any\\b"), "message": "TypeScript any type weakens type safety"},
    {"id": "no-var", "severity": "warning", "pattern": re.compile(r"\\bvar\\s+"), "message": "Use const/let instead of var"},
]

def lint_code(code: str, filename: str = "code") -> str:
    \"\"\"
    Statically analyzes code for common anti-patterns.
    \"\"\"
    lines = code.split('\\n')
    issues = []
    
    for rule in RULES:
        for idx, line in enumerate(lines):
            if rule["pattern"].search(line):
                issues.append({
                    "line": idx + 1,
                    "severity": rule["severity"],
                    "rule": rule["id"],
                    "message": rule["message"]
                })
                
    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    
    score = max(0, 100 - (errors * 20) - (warnings * 5) - (len(issues) - errors - warnings))
    
    if not issues:
        return f"✅ No issues found in {filename}. Score: {score}/100"
        
    summary = f"Found {errors} error(s), {warnings} warning(s), {len(issues) - errors - warnings} info(s) in {filename}. Score: {score}/100\\n\\n"
    
    for issue in issues:
        prefix = "❌" if issue["severity"] == "error" else "⚠️" if issue["severity"] == "warning" else "ℹ️"
        summary += f"{prefix} [{issue['rule']}] L{issue['line']}: {issue['message']}\\n"
        
    return summary
