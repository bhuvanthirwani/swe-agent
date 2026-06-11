import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from backend.core.database import get_db_connection


@dataclass
class GuardrailResult:
    allowed: bool
    action: str
    violations: List[str]
    sanitized_text: str


class GuardrailRuntime:
    SECRET_PATTERNS = [
        re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
        re.compile(r"gsk_[A-Za-z0-9_\-]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(
            r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"
        ),
    ]
    PII_PATTERNS = [
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ]
    PROMPT_INJECTION_HINTS = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "reveal your system prompt",
        "developer message",
        "hidden prompt",
    ]

    def parse_policies(self, node: Dict[str, Any]) -> List[str]:
        config = node.get("config") or {}
        policies = config.get("policies") or ["secrets", "pii", "prompt_injection"]
        if isinstance(policies, str):
            return [p.strip().lower() for p in policies.split(",") if p.strip()]
        if isinstance(policies, list):
            return [str(p).strip().lower() for p in policies if str(p).strip()]
        return []

    def check(
        self,
        text: str,
        guardrail_nodes: List[Dict[str, Any]],
        phase: str,
        session_id: str = None,
        agent_run_id: int = None,
    ) -> GuardrailResult:
        sanitized = text or ""
        violations: List[str] = []
        final_action = "allow"

        for node in guardrail_nodes:
            config = node.get("config") or {}
            node_phase = str(config.get("phase") or "both")
            if node_phase not in ("both", phase):
                continue
            action = str(config.get("action") or "block")
            node_violations, sanitized = self._check_node(
                sanitized, self.parse_policies(node), action
            )
            if node_violations:
                violations.extend(
                    [
                        f"{node.get('label') or node.get('id')}: {v}"
                        for v in node_violations
                    ]
                )
                final_action = self._stronger_action(final_action, action)
                self._log_result(
                    session_id, agent_run_id, node, phase, action, node_violations
                )

        allowed = final_action not in ("block", "route_to_human") or not violations
        if final_action == "redact":
            allowed = True
        if final_action == "warn":
            allowed = True
        return GuardrailResult(allowed, final_action, violations, sanitized)

    def prompt_section(self, guardrail_nodes: List[Dict[str, Any]]) -> str:
        if not guardrail_nodes:
            return ""
        lines = [
            "## Guardrails",
            "",
            "You must comply with all connected guardrails. Runtime checks will also enforce these rules.",
            "If a request violates a guardrail, follow the configured action instead of proceeding normally.",
            "",
        ]
        for node in guardrail_nodes:
            config = node.get("config") or {}
            lines.append(f"- {node.get('label') or 'Guardrail'}")
            lines.append(f"  Phase: {config.get('phase', 'both')}")
            lines.append(f"  Policies: {', '.join(self.parse_policies(node))}")
            lines.append(f"  Action: {config.get('action', 'block')}")
        return "\n".join(lines).strip()

    def _check_node(
        self, text: str, policies: List[str], action: str
    ) -> Tuple[List[str], str]:
        sanitized = text
        violations: List[str] = []
        if "secrets" in policies or "secret" in policies:
            for pattern in self.SECRET_PATTERNS:
                if pattern.search(sanitized):
                    violations.append("possible secret or private key detected")
                    if action == "redact":
                        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        if "pii" in policies:
            for pattern in self.PII_PATTERNS:
                if pattern.search(sanitized):
                    violations.append("possible PII detected")
                    if action == "redact":
                        sanitized = pattern.sub("[REDACTED_PII]", sanitized)
        if "prompt_injection" in policies or "injection" in policies:
            lower = sanitized.lower()
            for hint in self.PROMPT_INJECTION_HINTS:
                if hint in lower:
                    violations.append(f"prompt injection hint detected: {hint}")
                    break
        return violations, sanitized

    def _stronger_action(self, current: str, candidate: str) -> str:
        order = [
            "allow",
            "warn",
            "redact",
            "retry_with_feedback",
            "block",
            "route_to_human",
        ]
        return candidate if order.index(candidate) > order.index(current) else current

    def _log_result(
        self,
        session_id: str,
        agent_run_id: int,
        node: Dict[str, Any],
        phase: str,
        action: str,
        violations: List[str],
    ) -> None:
        if not session_id:
            return
        try:
            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO guardrail_results (session_id, agent_run_id, node_id, policy_id, phase, status, action_taken, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    agent_run_id,
                    str(node.get("id")),
                    None,
                    phase,
                    "failed",
                    action,
                    json.dumps({"violations": violations}),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            print(f"Failed to log guardrail result: {exc}")
