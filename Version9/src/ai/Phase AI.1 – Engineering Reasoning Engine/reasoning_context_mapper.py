"""Map engineering context into reasoning prompt variables."""

from __future__ import annotations

from typing import Any, Dict

from prompt_templates import build_reasoning_variables
from src.llm.context.context_models import EngineeringContext
from src.llm.context.engineering_context_builder import EngineeringContextBuilder


class ReasoningContextMapper:
    """Translate engineering context into deterministic prompt variables."""

    def __init__(self, context_builder: EngineeringContextBuilder | None = None) -> None:
        self._context_builder = context_builder or EngineeringContextBuilder()

    def map(
        self,
        context: EngineeringContext,
        variables: Dict[str, Any] | None = None,
        *,
        task_type: str,
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        merged.update(self._context_builder.to_prompt_variables(context))
        merged.update(self._section_variables(context))
        merged.update(build_reasoning_variables(task_type))
        if variables:
            merged.update(variables)
        return merged

    @staticmethod
    def _section_variables(context: EngineeringContext) -> Dict[str, Any]:
        mapped: Dict[str, Any] = {}
        for section in context.sections:
            key = f"context_{section.section_name}"
            mapped[key] = section.content
        return mapped

    @staticmethod
    def extract_section(context: EngineeringContext, section_name: str) -> Any:
        for section in context.sections:
            if section.section_name == section_name:
                return section.content
        return None
