"""Token estimation and budget allocation."""

from __future__ import annotations

from typing import Any, Dict, List

from src.llm.context.context_registry import PRIORITY_ORDER, ContextRegistry
from src.llm.context.context_serializer import ContextSerializer


class TokenBudgetManager:
    """Estimate and enforce deterministic token budgets."""

    def __init__(self, default_budget: int | None = None) -> None:
        self._default_budget = default_budget

    def apply_budget(self, task_type: str, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        definition = ContextRegistry.get(task_type)
        budget = self._default_budget or definition.token_budget
        enriched = self._annotate_sections(sections)

        total = sum(section["token_estimate"] for section in enriched)
        if total <= budget:
            return enriched

        removable = [
            section
            for section in enriched
            if section["priority"] != "Critical"
        ]
        removable.sort(
            key=lambda item: (
                -PRIORITY_ORDER.get(str(item["priority"]), 99),
                -int(item["token_estimate"]),
                str(item["section_name"]),
            )
        )

        trimmed = list(enriched)
        current_total = total
        for section in removable:
            if current_total <= budget:
                break
            trimmed = [item for item in trimmed if item["section_name"] != section["section_name"]]
            current_total = sum(item["token_estimate"] for item in trimmed)

        trimmed.sort(
            key=lambda item: (
                PRIORITY_ORDER.get(str(item["priority"]), 99),
                str(item["section_name"]),
            )
        )
        return trimmed

    def estimate_total(self, sections: List[Dict[str, Any]]) -> int:
        return sum(int(section.get("token_estimate", 0)) for section in sections)

    def _annotate_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        annotated: List[Dict[str, Any]] = []
        for section in sections:
            serialized = ContextSerializer.serialize(section.get("content"))
            text = ContextSerializer.to_text(serialized)
            annotated.append(
                {
                    "section_name": section["section_name"],
                    "priority": section["priority"],
                    "content": serialized,
                    "token_estimate": ContextSerializer.estimate_tokens(text),
                }
            )
        return annotated
