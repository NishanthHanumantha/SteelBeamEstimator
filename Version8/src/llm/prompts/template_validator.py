"""Validate prompt template structure."""

from __future__ import annotations

import re

from src.llm.prompts.prompt_models import TemplateValidationError
from src.llm.prompts.template_renderer import TemplateRenderer

_OPEN_BRACE_PATTERN = re.compile(r"\{\{")
_CLOSE_BRACE_PATTERN = re.compile(r"\}\}")
_SINGLE_BRACE_PATTERN = re.compile(r"(?<!\{)\{(?!\{)|(?<!\})\}(?!\})")


class TemplateValidator:
    """Structural validation for markdown prompt templates."""

    @staticmethod
    def validate(
        template_body: str,
        variables: dict | None = None,
        *,
        require_resolved: bool = True,
    ) -> None:
        if not template_body or not template_body.strip():
            raise TemplateValidationError("Template body is empty.")

        try:
            template_body.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise TemplateValidationError("Template is not valid UTF-8.") from exc

        if _SINGLE_BRACE_PATTERN.search(template_body):
            raise TemplateValidationError("Template contains unsupported single-brace expressions.")

        opens = len(_OPEN_BRACE_PATTERN.findall(template_body))
        closes = len(_CLOSE_BRACE_PATTERN.findall(template_body))
        if opens != closes:
            raise TemplateValidationError("Template contains unbalanced {{ }} markers.")

        unresolved = TemplateRenderer.unresolved_variables(template_body, variables)
        if require_resolved and unresolved:
            raise TemplateValidationError(
                f"Template contains unresolved variables: {', '.join(unresolved)}"
            )

        if not any(ch.isalnum() for ch in template_body):
            raise TemplateValidationError("Template is not readable markdown content.")
