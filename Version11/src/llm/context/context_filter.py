"""Deterministic task-aware context filtering."""

from __future__ import annotations

from typing import Any, Dict, List

from src.llm.context.context_collector import build_section_payload
from src.llm.context.context_registry import PRIORITY_ORDER, ContextRegistry, SectionDefinition


class ContextFilter:
    """Filter collected engineering data to task-required sections."""

    def filter(self, task_type: str, collected: Dict[str, Any]) -> List[Dict[str, Any]]:
        definition = ContextRegistry.get(task_type)
        sections: List[Dict[str, Any]] = []
        seen_names: set[str] = set()

        for section_def in definition.sections:
            if section_def.section_name in seen_names:
                continue
            content = build_section_payload(
                section_def.section_name,
                section_def.required_objects,
                collected,
            )
            if content is None:
                continue
            seen_names.add(section_def.section_name)
            sections.append(
                {
                    "section_name": section_def.section_name,
                    "priority": section_def.priority,
                    "content": content,
                }
            )

        sections.sort(
            key=lambda item: (
                PRIORITY_ORDER.get(str(item["priority"]), 99),
                str(item["section_name"]),
            )
        )
        return sections
