import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.core.database import get_db_connection


@dataclass
class RAGChunk:
    id: str
    source: str
    content: str
    score: float
    metadata: Dict[str, Any]


class VectorRuntime:
    """Chroma-compatible RAG runtime with a SQLite lexical fallback.

    If chromadb is installed and reachable, this class can be extended to use it.
    The fallback keeps the feature usable in dev/test without adding a hard dependency.
    """

    def _tokens(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9_#+.-]+", (text or "").lower())

    def _score(self, query: str, content: str) -> float:
        q = self._tokens(query)
        c = self._tokens(content)
        if not q or not c:
            return 0.0
        q_set = set(q)
        c_set = set(c)
        overlap = len(q_set & c_set)
        return overlap / math.sqrt(max(1, len(q_set)) * max(1, len(c_set)))

    def query(
        self, node: Dict[str, Any], query: str, workflow_id: Optional[str] = None
    ) -> List[RAGChunk]:
        config = node.get("config") or {}
        top_k = int(config.get("topK") or 5)
        threshold = float(config.get("scoreThreshold") or 0.0)
        collection = str(config.get("collectionName") or "default")

        rows: List[Dict[str, Any]] = []
        conn = get_db_connection()
        try:
            # Static knowledge base
            try:
                for row in conn.execute(
                    "SELECT id, title, content, category, tags FROM knowledge_base"
                ).fetchall():
                    rows.append(
                        {
                            "id": row["id"],
                            "source": row["title"],
                            "content": row["content"],
                            "metadata": {
                                "category": row["category"],
                                "tags": self._safe_json(row["tags"]),
                                "source_table": "knowledge_base",
                            },
                        }
                    )
            except Exception:
                pass

            # Workflow/vector indexed documents
            try:
                sql = """
                    SELECT vd.id, vd.title, vd.content, vd.metadata_json, vc.name as collection_name
                    FROM vector_documents vd
                    JOIN vector_collections vc ON vc.id = vd.collection_id
                    WHERE vc.name = ? OR vc.chroma_collection_name = ?
                """
                for row in conn.execute(sql, (collection, collection)).fetchall():
                    rows.append(
                        {
                            "id": str(row["id"]),
                            "source": row["title"] or f"Vector Document {row['id']}",
                            "content": row["content"],
                            "metadata": {
                                **self._safe_json(row["metadata_json"]),
                                "collection": row["collection_name"],
                                "source_table": "vector_documents",
                            },
                        }
                    )
            except Exception:
                pass
        finally:
            conn.close()

        chunks: List[RAGChunk] = []
        for row in rows:
            score = self._score(query, row.get("content", ""))
            if score >= threshold:
                chunks.append(
                    RAGChunk(
                        row["id"],
                        row["source"],
                        row.get("content", ""),
                        score,
                        row.get("metadata") or {},
                    )
                )
        chunks.sort(key=lambda chunk: chunk.score, reverse=True)
        return chunks[:top_k]

    def index_agent_output(
        self,
        workflow_id: str,
        node: Dict[str, Any],
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        config = node.get("config") or {}
        collection_name = str(config.get("collectionName") or "default")
        conn = get_db_connection()
        try:
            collection_id = self._ensure_collection(
                conn, workflow_id, collection_name, config
            )
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO vector_documents (collection_id, source_type, source_id, title, content, content_hash, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    collection_id,
                    "agent_output",
                    str(node.get("id")),
                    title,
                    content,
                    content_hash,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _ensure_collection(
        self, conn, workflow_id: str, name: str, config: Dict[str, Any]
    ) -> int:
        row = conn.execute(
            "SELECT id FROM vector_collections WHERE workflow_id = ? AND name = ?",
            (workflow_id, name),
        ).fetchone()
        if row:
            return int(row["id"])
        cursor = conn.execute(
            """
            INSERT INTO vector_collections (workflow_id, name, chroma_collection_name, scope, config_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                workflow_id,
                name,
                name,
                str(config.get("scope") or "workflow"),
                json.dumps(config),
            ),
        )
        return int(cursor.lastrowid)

    def _safe_json(self, value: Any) -> Any:
        if not value:
            return [] if value == "" else {}
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return {}


def format_rag_prompt(chunks: List[RAGChunk]) -> str:
    if not chunks:
        return "## RAG Context\n\nNo relevant RAG snippets were retrieved. Do not invent facts that are not present elsewhere."
    lines = [
        "## RAG Context",
        "",
        "You have access to retrieved knowledge from the connected Chroma DB / vector store.",
        "Use these snippets when relevant and prefer higher-score snippets.",
        "",
    ]
    for idx, chunk in enumerate(chunks, 1):
        lines.append(f"{idx}. Source: {chunk.source}")
        lines.append(f"   Score: {chunk.score:.3f}")
        lines.append(f"   Content: {chunk.content[:1800]}")
        lines.append("")
    return "\n".join(lines).strip()
