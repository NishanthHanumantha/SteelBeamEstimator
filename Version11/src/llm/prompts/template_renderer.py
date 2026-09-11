"""Deterministic template variable rendering."""

from __future__ import annotations

import re
from typing import Any, Dict

_VARIABLE_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")


class TemplateRenderer:
    """Replace {{variable}} placeholders with supplied values."""

    @staticmethod
    def render(template_body: str, variables: Dict[str, Any] | None = None) -> str:
        values = variables or {}

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in values:
                return match.group(0)
            return str(values[key])

        return _VARIABLE_PATTERN.sub(_replace, template_body)

    @staticmethod
    def unresolved_variables(template_body: str, variables: Dict[str, Any] | None = None) -> list[str]:
        values = variables or {}
        found = _VARIABLE_PATTERN.findall(template_body)
        return sorted({name for name in found if name not in values})
