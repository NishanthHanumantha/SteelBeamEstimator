"""Validate Phase F.2 resolved beam section dimensions."""

from __future__ import annotations

from typing import Any, List


class BeamDimensionValidator:
    """Verify resolved beam section completeness and confidence rules."""

    def __init__(self, config: dict[str, Any]) -> None:
        dr = config.get("dimension_resolution", {})
        self._min_width = float(dr.get("minimum_reasonable_width", 100))
        self._max_width = float(dr.get("maximum_reasonable_width", 600))
        self._min_depth = float(dr.get("minimum_reasonable_depth", 150))
        self._max_depth = float(dr.get("maximum_reasonable_depth", 1500))

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        beams = model.get("beams", [])

        checks.append(self._check_section_object(beams))
        checks.append(self._check_width_depth_fields(beams))
        checks.append(self._check_confidence_rules(beams))
        checks.append(self._check_dimension_limits(beams))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
            },
        }

    def _check_section_object(self, beams: list) -> dict[str, Any]:
        with_section = sum(
            1 for b in beams if isinstance(b.get("dimensions", {}).get("section"), dict)
        )
        ok = with_section == len(beams) and with_section > 0
        return {
            "name": "Section Object",
            "status": "PASS" if ok else "FAIL",
            "with_section": with_section,
            "total": len(beams),
        }

    def _check_width_depth_fields(self, beams: list) -> dict[str, Any]:
        complete = 0
        for beam in beams:
            section = beam.get("dimensions", {}).get("section", {})
            w = section.get("width", {})
            d = section.get("depth", {})
            if all(k in w for k in ("value", "unit", "status", "source", "confidence")):
                if all(k in d for k in ("value", "unit", "status", "source", "confidence")):
                    complete += 1
        ok = complete == len(beams)
        return {
            "name": "Width/Depth Fields",
            "status": "PASS" if ok else "FAIL",
            "complete_count": complete,
        }

    def _check_confidence_rules(self, beams: list) -> dict[str, Any]:
        violations = 0
        for beam in beams:
            section = beam.get("dimensions", {}).get("section", {})
            for dim_key in ("width", "depth"):
                dim = section.get(dim_key, {})
                status = dim.get("status")
                conf = dim.get("confidence", -1)
                if status == "KNOWN" and conf <= 0:
                    violations += 1
                if status == "UNKNOWN" and conf != 0:
                    violations += 1
        ok = violations == 0
        return {
            "name": "Confidence Rules",
            "status": "PASS" if ok else "FAIL",
            "violations": violations,
        }

    def _check_dimension_limits(self, beams: list) -> dict[str, Any]:
        out_of_range = 0
        for beam in beams:
            section = beam.get("dimensions", {}).get("section", {})
            w = section.get("width", {})
            d = section.get("depth", {})
            if w.get("status") == "KNOWN" and w.get("value") is not None:
                val = float(w["value"])
                if not (self._min_width <= val <= self._max_width):
                    out_of_range += 1
            if d.get("status") == "KNOWN" and d.get("value") is not None:
                val = float(d["value"])
                if not (self._min_depth <= val <= self._max_depth):
                    out_of_range += 1
        ok = out_of_range == 0
        return {
            "name": "Dimension Limits",
            "status": "PASS" if ok else "FAIL",
            "out_of_range": out_of_range,
        }
