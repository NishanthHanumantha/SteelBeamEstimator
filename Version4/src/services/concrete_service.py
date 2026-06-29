"""Concrete volume engineering calculations."""

from __future__ import annotations

from typing import Any, Optional


class ConcreteService:
    """Concrete volume from beam section and length model."""

    def compute_volume_mm3(
        self,
        beam_section: dict[str, Any],
        length_model: dict[str, Any],
        length_field: str = "clear_span",
    ) -> Optional[float]:
        width = self._dim_value(beam_section.get("width", {}))
        depth = self._dim_value(beam_section.get("depth", {}))
        length = self._dim_value(length_model.get(length_field, {}))
        if length_field == "clear_span" and length is None:
            length = self._dim_value(length_model.get("governing_span", {}))
        if width is None or depth is None or length is None:
            return None
        return width * depth * length

    def compute_volume_m3(
        self,
        beam_section: dict[str, Any],
        length_model: dict[str, Any],
        length_field: str = "clear_span",
    ) -> Optional[float]:
        mm3 = self.compute_volume_mm3(beam_section, length_model, length_field)
        if mm3 is None:
            return None
        return mm3 / 1_000_000_000.0

    @staticmethod
    def _dim_value(data: dict[str, Any]) -> Optional[float]:
        val = data.get("value")
        if val is None:
            return None
        return float(val)

    def to_registry_entry(self) -> dict[str, Any]:
        return {
            "service_id": "concrete",
            "description": "Concrete volume from section and span",
            "rule_reference": "RULE::PROJECT",
            "status": "READY",
        }
