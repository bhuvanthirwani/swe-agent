import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.core.database import get_db_connection
from backend.core.guardrails import GuardrailRuntime
from backend.core.memory_runtime import MemoryReadResult, MemoryRuntime
from backend.core.vector_runtime import RAGChunk, VectorRuntime, format_rag_prompt
from backend.core.workflow_graph import WorkflowGraph
from backend.models.interfaces import LLMConfig, ToolConfig


@dataclass
class PromptBundle:
    system_prompt: str
    user_prompt: str
    llm: LLMConfig
    tool_names: List[str] = field(default_factory=list)
    memory_nodes: List[Dict[str, Any]] = field(default_factory=list)
    guardrail_nodes: List[Dict[str, Any]] = field(default_factory=list)
    rag_chunks: List[RAGChunk] = field(default_factory=list)
    compacted: bool = False
    component_events: List[Dict[str, Any]] = field(default_factory=list)


class PromptContextAssembler:
    def __init__(self, workflow_id: str, session_id: str, graph: WorkflowGraph):
        self.workflow_id = workflow_id
        self.session_id = session_id
        self.graph = graph
        self.memory_runtime = MemoryRuntime()
        self.vector_runtime = VectorRuntime()
        self.guardrail_runtime = GuardrailRuntime()

    def assemble(
        self,
        agent_node: Dict[str, Any],
        agent_config,
        context: Dict[str, Any],
    ) -> PromptBundle:
        events: List[Dict[str, Any]] = []
        resource_nodes = self._resource_nodes(agent_node)
        model_node = self._first_by_type(resource_nodes, {"model"})
        tool_nodes = [node for node in resource_nodes if node.get("type") == "tool"]
        memory_nodes = [
            node
            for node in resource_nodes
            if node.get("type")
            in {"buffer_memory", "summary_memory", "hippocampus_memory"}
        ]
        rag_nodes = [node for node in resource_nodes if node.get("type") == "rag"]
        guardrail_nodes = [
            node for node in resource_nodes if node.get("type") == "guardrail"
        ]

        llm = self._resolve_llm(agent_config.llm, model_node, agent_node)
        tool_configs = self._resolve_tools(agent_config.tools, tool_nodes, agent_node)
        memory_reads = self._read_memories(memory_nodes, events)
        rag_chunks = self._retrieve_rag(rag_nodes, context, events)

        sections = [
            "# Agent Identity",
            agent_config.system_prompt or "You are a helpful workflow agent.",
            "",
            "# Workflow Role",
            f"You are executing node `{agent_node.get('label') or agent_node.get('id')}` in workflow `{self.workflow_id}`.",
            "Use connected resources only when relevant. Respect guardrails and output requirements.",
            "",
        ]

        tool_section = self._format_tools(tool_configs)
        if tool_section:
            sections.extend([tool_section, ""])

        if memory_reads:
            sections.extend(["# Connected Memory"])
            for read in memory_reads:
                sections.extend([read.prompt_section, ""])

        if rag_nodes:
            sections.extend([format_rag_prompt(rag_chunks), ""])

        guardrail_section = self.guardrail_runtime.prompt_section(guardrail_nodes)
        if guardrail_section:
            sections.extend([guardrail_section, ""])

        if agent_node.get("useCompaction", False):
            sections.extend(
                [
                    "## Context Compaction",
                    "Use compaction when the context is too large. Preserve guardrails, tool instructions, current requirement, key decisions, and unresolved tasks.",
                    "",
                ]
            )

        user_prompt = json.dumps(
            {
                "original_requirement": context.get("requirement"),
                "workflow_context": context,
                "node_config": agent_node.get("config") or {},
                "predecessor_context_keys": self.graph.predecessor_context_keys(
                    str(agent_node.get("id"))
                ),
            },
            ensure_ascii=False,
        )

        system_prompt = "\n".join(sections).strip()
        compacted, system_prompt, user_prompt = self._compact_if_needed(
            agent_node, system_prompt, user_prompt
        )

        return PromptBundle(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm=llm,
            tool_names=[tool.name for tool in tool_configs],
            memory_nodes=memory_nodes,
            guardrail_nodes=guardrail_nodes,
            rag_chunks=rag_chunks,
            compacted=compacted,
            component_events=events,
        )

    def _resource_nodes(self, agent_node: Dict[str, Any]) -> List[Dict[str, Any]]:
        node_id = str(agent_node.get("id"))
        return [node for node, _edge in self.graph.connected_resource_nodes(node_id)]

    def _first_by_type(
        self, nodes: List[Dict[str, Any]], types: set
    ) -> Optional[Dict[str, Any]]:
        return next((node for node in nodes if node.get("type") in types), None)

    def _resolve_llm(
        self,
        default_llm: LLMConfig,
        model_node: Optional[Dict[str, Any]],
        agent_node: Dict[str, Any],
    ) -> LLMConfig:
        config = (model_node or {}).get("config") or {}
        if not config and agent_node.get("chatModel"):
            config = {"modelName": agent_node.get("chatModel")}
        if not config:
            return default_llm

        provider = str(config.get("provider") or default_llm.provider_name)
        model_name = str(
            config.get("modelName") or config.get("model") or default_llm.model_name
        )
        api_key = config.get("apiKey") or config.get("api_key")
        base_url = config.get("baseUrl") or config.get("base_url")

        if not api_key:
            matched = self._lookup_llm_config(provider, model_name)
            if matched:
                return matched

        return LLMConfig(
            id=default_llm.id,
            provider_name=provider,
            model_name=model_name,
            api_key=str(api_key) if api_key else default_llm.api_key,
            base_url=str(base_url) if base_url else default_llm.base_url,
        )

    def _lookup_llm_config(self, provider: str, model_name: str) -> Optional[LLMConfig]:
        try:
            conn = get_db_connection()
            row = conn.execute(
                """
                SELECT l.id, l.model_name, l.api_key, p.name as provider_name, p.base_url
                FROM llm_configs l
                JOIN llm_providers p ON p.id = l.provider_id
                WHERE p.name = ? AND l.model_name = ?
                LIMIT 1
                """,
                (provider, model_name),
            ).fetchone()
            conn.close()
            if row:
                return LLMConfig(**dict(row))
        except Exception:
            return None
        return None

    def _resolve_tools(
        self,
        assigned_tools: List[ToolConfig],
        tool_nodes: List[Dict[str, Any]],
        agent_node: Dict[str, Any],
    ) -> List[ToolConfig]:
        tools: Dict[str, ToolConfig] = {tool.name: tool for tool in assigned_tools}
        configured_names = list(agent_node.get("tools") or [])
        for node in tool_nodes:
            config = node.get("config") or {}
            name = str(config.get("toolName") or node.get("label") or "").strip()
            if name:
                configured_names.append(name)

        if not configured_names:
            return list(tools.values())

        try:
            conn = get_db_connection()
            for name in configured_names:
                if name in tools:
                    continue
                row = conn.execute(
                    "SELECT * FROM tools WHERE name = ?", (name,)
                ).fetchone()
                if row:
                    tools[name] = ToolConfig(**dict(row))
                else:
                    tools[name] = ToolConfig(
                        id=0,
                        name=name,
                        description=f"Configured workflow tool `{name}`.",
                        code_reference=None,
                    )
            conn.close()
        except Exception:
            for name in configured_names:
                tools.setdefault(
                    name,
                    ToolConfig(
                        id=0,
                        name=name,
                        description=f"Configured workflow tool `{name}`.",
                        code_reference=None,
                    ),
                )

        return list(tools.values())

    def _format_tools(self, tools: List[ToolConfig]) -> str:
        if not tools:
            return ""
        lines = [
            "## Available Tools",
            "",
            "You have access to these tools. Only use tools listed here and provide valid arguments.",
            "Do not claim to have used a tool unless a tool execution is actually performed.",
            "",
        ]
        for tool in tools:
            lines.append(
                f"- {tool.name}: {tool.description or 'No description provided.'}"
            )
            if tool.code_reference:
                lines.append(f"  Code reference: {tool.code_reference}")
        return "\n".join(lines).strip()

    def _read_memories(
        self, memory_nodes: List[Dict[str, Any]], events: List[Dict[str, Any]]
    ) -> List[MemoryReadResult]:
        reads: List[MemoryReadResult] = []
        for node in memory_nodes:
            try:
                read = self.memory_runtime.read_memory(
                    self.workflow_id, self.session_id, node
                )
                reads.append(read)
                events.append(
                    {
                        "type": "memory_read",
                        "nodeId": read.node_id,
                        "memoryType": read.memory_type,
                        "path": read.path,
                    }
                )
            except Exception as exc:
                events.append(
                    {
                        "type": "memory_error",
                        "nodeId": node.get("id"),
                        "error": str(exc),
                    }
                )
        return reads

    def _retrieve_rag(
        self,
        rag_nodes: List[Dict[str, Any]],
        context: Dict[str, Any],
        events: List[Dict[str, Any]],
    ) -> List[RAGChunk]:
        chunks: List[RAGChunk] = []
        query = self._build_rag_query(context)
        for node in rag_nodes:
            events.append(
                {
                    "type": "rag_query_started",
                    "nodeId": node.get("id"),
                    "query": query[:200],
                }
            )
            node_chunks = self.vector_runtime.query(node, query, self.workflow_id)
            chunks.extend(node_chunks)
            events.append(
                {
                    "type": "rag_query_completed",
                    "nodeId": node.get("id"),
                    "count": len(node_chunks),
                }
            )
        # Deduplicate by id while preserving score order.
        chunks.sort(key=lambda chunk: chunk.score, reverse=True)
        deduped: List[RAGChunk] = []
        seen = set()
        for chunk in chunks:
            if chunk.id in seen:
                continue
            seen.add(chunk.id)
            deduped.append(chunk)
        return deduped[:10]

    def _build_rag_query(self, context: Dict[str, Any]) -> str:
        parts = [str(context.get("requirement") or "")]
        for key, value in context.items():
            if key.endswith("_output"):
                parts.append(str(value)[:1200])
        return "\n".join(part for part in parts if part).strip()

    def _compact_if_needed(
        self, agent_node: Dict[str, Any], system_prompt: str, user_prompt: str
    ):
        use_compaction = bool(agent_node.get("useCompaction"))
        max_tokens = int(agent_node.get("maxContextTokens") or 12000)
        estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4
        if not use_compaction or estimated_tokens <= max_tokens:
            return False, system_prompt, user_prompt

        max_chars = max_tokens * 4
        preserved_system = system_prompt[: int(max_chars * 0.72)]
        compact_user = user_prompt[: int(max_chars * 0.2)]
        notice = "\n\n## Context Compaction Notice\n\nContext was compacted to fit the configured context budget. Preserve explicit constraints and current task state."
        return (
            True,
            preserved_system + notice,
            compact_user + "\n... [user context compacted]",
        )
