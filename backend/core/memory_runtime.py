import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.database import get_db_connection


@dataclass
class MemoryReadResult:
    node_id: str
    memory_type: str
    path: str
    content: str
    prompt_section: str


class MemoryRuntime:
    """Markdown-backed workflow memory with optional SQLite audit entries."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(
            workspace_root or os.getenv("WORKSPACE_ROOT", ".workspace")
        ).resolve()
        self.memory_root = (self.workspace_root / "memory").resolve()
        self.memory_root.mkdir(parents=True, exist_ok=True)

    def _safe_file_path(
        self, workflow_id: str, session_id: str, node: Dict[str, Any]
    ) -> Path:
        config = node.get("config") or {}
        memory_type = str(node.get("type", "memory"))
        scope = str(
            config.get("scope")
            or ("session" if memory_type == "buffer_memory" else "workflow")
        )
        raw_file = str(config.get("filePath") or f"{memory_type}.md")
        filename = Path(raw_file).name or f"{memory_type}.md"

        if scope == "session":
            base = self.memory_root / workflow_id / session_id
        elif scope == "agent":
            base = (
                self.memory_root
                / workflow_id
                / session_id
                / str(node.get("id", "agent"))
            )
        elif scope == "project":
            base = self.memory_root / "project"
        elif scope == "user":
            base = self.memory_root / "user"
        elif scope == "organization":
            base = self.memory_root / "organization"
        else:
            base = self.memory_root / workflow_id

        base.mkdir(parents=True, exist_ok=True)
        resolved = (base / filename).resolve()
        if not str(resolved).startswith(str(self.memory_root)):
            raise ValueError("Invalid memory file path")
        return resolved

    def read_memory(
        self, workflow_id: str, session_id: str, node: Dict[str, Any]
    ) -> MemoryReadResult:
        path = self._safe_file_path(workflow_id, session_id, node)
        if not path.exists():
            path.write_text(
                f"# {node.get('label') or node.get('type') or 'Memory'}\n\n",
                encoding="utf-8",
            )
        content = path.read_text(encoding="utf-8")
        memory_type = str(node.get("type", "memory"))
        prompt_section = self._format_prompt_section(memory_type, content)
        self._upsert_memory_store(workflow_id, node, path)
        return MemoryReadResult(
            str(node.get("id")), memory_type, str(path), content, prompt_section
        )

    def append_memory(
        self,
        workflow_id: str,
        session_id: str,
        node: Dict[str, Any],
        title: str,
        content: str,
        agent_id: Optional[int] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> None:
        config = node.get("config") or {}
        memory_type = str(node.get("type", "memory"))
        writable = config.get("writable", config.get("allowWrites", True))
        if writable is False:
            return

        path = self._safe_file_path(workflow_id, session_id, node)
        timestamp = datetime.utcnow().isoformat() + "Z"
        excerpt = self._compact_text(
            content,
            int(config.get("maxSummaryTokens") or config.get("maxTokens") or 1200),
        )
        block = f"\n\n## {title}\n\n- Time: {timestamp}\n- Type: {memory_type}\n\n{excerpt}\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(block)
        self._insert_memory_entry(
            workflow_id, session_id, node, excerpt, agent_id, importance, tags or []
        )

    def update_after_agent_run(
        self,
        workflow_id: str,
        session_id: str,
        connected_memories: List[Dict[str, Any]],
        agent_name: str,
        output: str,
        status: str,
        agent_id: Optional[int] = None,
    ) -> None:
        for node in connected_memories:
            memory_type = node.get("type")
            config = node.get("config") or {}
            if memory_type == "buffer_memory":
                self.append_memory(
                    workflow_id,
                    session_id,
                    node,
                    f"{agent_name} temporary output",
                    output,
                    agent_id,
                    0.35,
                    [status],
                )
            elif memory_type == "summary_memory":
                if (
                    status == "success"
                    and config.get("updateOnComplete", True) is False
                ):
                    continue
                if status != "success" and config.get("updateOnFailure", True) is False:
                    continue
                self.append_memory(
                    workflow_id,
                    session_id,
                    node,
                    f"{agent_name} step summary ({status})",
                    output,
                    agent_id,
                    0.65,
                    [status],
                )
            elif memory_type == "hippocampus_memory":
                # Long-term memory is intentionally conservative: only persist explicit important facts.
                durable_facts = self._extract_remember_facts(output)
                for fact in durable_facts:
                    self.append_memory(
                        workflow_id,
                        session_id,
                        node,
                        f"Important thing to remember from {agent_name}",
                        fact,
                        agent_id,
                        0.9,
                        ["hippocampus", status],
                    )

    def _format_prompt_section(self, memory_type: str, content: str) -> str:
        if memory_type == "buffer_memory":
            header = "## Buffer Memory\n\nThis is short-term workflow memory stored in markdown. Use it for recent state and temporary decisions."
        elif memory_type == "summary_memory":
            header = "## Summary Memory\n\nThis is a durable summary of what has happened in this workflow. Use it to maintain continuity."
        elif memory_type == "hippocampus_memory":
            header = "## Important Things to Remember\n\nThese are durable facts and preferences. Treat them as high-priority context unless the user overrides them."
        else:
            header = "## Connected Memory"
        return f"{header}\n\n{self._compact_text(content, 2500)}".strip()

    def _compact_text(self, text: str, max_tokens: int) -> str:
        max_chars = max(1000, max_tokens * 4)
        if len(text) <= max_chars:
            return text
        return (
            text[: max_chars // 2]
            + "\n\n... [memory compacted] ...\n\n"
            + text[-max_chars // 2 :]
        )

    def _extract_remember_facts(self, output: str) -> List[str]:
        facts: List[str] = []
        for line in output.splitlines():
            lowered = line.lower()
            if (
                "remember:" in lowered
                or "important:" in lowered
                or "important thing" in lowered
            ):
                cleaned = line.strip(" -*#\t")
                if len(cleaned) > 12:
                    facts.append(cleaned)
        return facts[:5]

    def _upsert_memory_store(
        self, workflow_id: str, node: Dict[str, Any], path: Path
    ) -> None:
        try:
            conn = get_db_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_stores (id, workflow_id, node_id, type, scope, file_path, config_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    str(node.get("id")),
                    workflow_id,
                    str(node.get("id")),
                    str(node.get("type")),
                    str((node.get("config") or {}).get("scope", "workflow")),
                    str(path),
                    json.dumps(node.get("config") or {}),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            print(f"Failed to upsert memory store: {exc}")

    def _insert_memory_entry(
        self,
        workflow_id: str,
        session_id: str,
        node: Dict[str, Any],
        content: str,
        agent_id: Optional[int],
        importance: float,
        tags: List[str],
    ) -> None:
        try:
            conn = get_db_connection()
            store_id = str(node.get("id"))
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO memory_entries (store_id, session_id, agent_id, content, content_hash, importance, confidence, tags_json, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    store_id,
                    session_id,
                    agent_id,
                    content,
                    content_hash,
                    importance,
                    0.8,
                    json.dumps(tags),
                    workflow_id,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            print(f"Failed to insert memory entry: {exc}")
