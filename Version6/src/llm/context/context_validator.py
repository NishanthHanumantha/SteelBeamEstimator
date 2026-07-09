"""Validate engineering context structure."""

from __future__ import annotations

from typing import Iterable, List

from src.llm.context.context_models import ContextSection, ContextValidationError, EngineeringContext
from src.llm.context.context_registry import PRIORITY_ORDER


class ContextValidator:
    """Validate deterministic engineering context output."""

    VALID_PRIORITIES = set(PRIORITY_ORDER.keys())

    def validate(self, context: EngineeringContext) -> None:
        if not context.context_id:
            raise ContextValidationError("context_id is required.")
        if not context.context_version:
            raise ContextValidationError("context_version is required.")
        if not context.task_type:
            raise ContextValidationError("task_type is required.")
        if not context.sections:
            raise ContextValidationError("Engineering context must contain at least one section.")
        if context.estimated_tokens <= 0:
            raise ContextValidationError("estimated_tokens must be greater than zero.")
        if not context.checksum:
            raise ContextValidationError("checksum is required.")

        names: List[str] = []
        for section in context.sections:
            self._validate_section(section)
            names.append(section.section_name)

        if len(names) != len(set(names)):
            raise ContextValidationError("Section names must be unique.")

        expected_order = sorted(
            context.sections,
            key=lambda item: (PRIORITY_ORDER.get(item.priority, 99), item.section_name),
        )
        if list(context.sections) != expected_order:
            raise ContextValidationError("Sections are not in deterministic priority order.")

    def _validate_section(self, section: ContextSection) -> None:
        if not section.section_name:
            raise ContextValidationError("section_name is required.")
        if section.priority not in self.VALID_PRIORITIES:
            raise ContextValidationError(f"Invalid section priority: {section.priority}")
        if not section.content:
            raise ContextValidationError(f"Section '{section.section_name}' content is empty.")
        if section.token_estimate <= 0:
            raise ContextValidationError(
                f"Section '{section.section_name}' token_estimate must be greater than zero."
            )
        if not section.checksum:
            raise ContextValidationError(f"Section '{section.section_name}' checksum is required.")
