"""Engineering reasoning engine public API."""

from __future__ import annotations

from typing import Any, Dict

from reasoning_manager import ReasoningManager
from reasoning_models import EngineeringReasoningResult


class EngineeringReasoningEngine:
    """First AI-powered engineering reasoning capability."""

    def __init__(self, manager: ReasoningManager | None = None) -> None:
        self._manager = manager or ReasoningManager()

    def reason(
        self,
        task_type: str,
        engineering_objects: Dict[str, Any],
        variables: Dict[str, Any] | None = None,
        system_template: str = "ENGINEERING_SYSTEM",
    ) -> EngineeringReasoningResult:
        """Build context, execute Claude reasoning, validate, cache, and persist outputs."""
        return self._manager.execute(
            task_type,
            engineering_objects,
            variables=variables,
            system_template=system_template,
        )
