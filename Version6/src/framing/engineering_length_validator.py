"""Validate Phase F.4 Engineering Length Model."""

from __future__ import annotations

from typing import Any, List


class EngineeringLengthValidator:
    """Verify engineering length completeness and consistency."""

    REQUIRED_FIELDS = (
        "centerline_length",
        "support_face_length",
        "bearing_length_left",
        "bearing_length_right",
        "clear_span",
        "effective_span",
        "design_span",
        "governing_span",
    )

    VALUE_FIELDS = (
        "centerline_length",
        "support_face_length",
        "clear_span",
        "effective_span",
        "design_span",
    )

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        beams = model.get("beams", [])

        checks.append(self._check_length_model_exists(beams))
        checks.append(self._check_required_fields(beams))
        checks.append(self._check_provenance(beams))
        checks.append(self._check_clear_span_le_centerline(beams))
        checks.append(self._check_non_negative(beams))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.4",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
            },
        }

    def _check_length_model_exists(self, beams: list) -> dict[str, Any]:
        with_model = sum(1 for b in beams if isinstance(b.get("length_model"), dict))
        ok = with_model == len(beams) and with_model > 0
        return {
            "name": "Length Model Exists",
            "status": "PASS" if ok else "FAIL",
            "with_model": with_model,
            "total": len(beams),
        }

    def _check_required_fields(self, beams: list) -> dict[str, Any]:
        missing = 0
        for beam in beams:
            lm = beam.get("length_model", {})
            for field in self.REQUIRED_FIELDS:
                if field not in lm:
                    missing += 1
        ok = missing == 0
        return {
            "name": "Required Length Fields",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_provenance(self, beams: list) -> dict[str, Any]:
        violations = 0
        for beam in beams:
            lm = beam.get("length_model", {})
            for field in self.VALUE_FIELDS:
                entry = lm.get(field, {})
                if not isinstance(entry, dict):
                    violations += 1
                    continue
                if "source" not in entry or "confidence" not in entry:
                    violations += 1
            gov = lm.get("governing_span", {})
            if "selected_from" not in gov or "confidence" not in gov:
                violations += 1
        ok = violations == 0
        return {
            "name": "Provenance Fields",
            "status": "PASS" if ok else "FAIL",
            "violations": violations,
        }

    def _check_clear_span_le_centerline(self, beams: list) -> dict[str, Any]:
        violations = 0
        for beam in beams:
            lm = beam.get("length_model", {})
            cl = lm.get("centerline_length", {}).get("value")
            cs = lm.get("clear_span", {}).get("value")
            if cl is None or cs is None:
                continue
            if float(cs) > float(cl) + 0.5:
                violations += 1
        ok = violations == 0
        return {
            "name": "Clear Span <= Centerline",
            "status": "PASS" if ok else "FAIL",
            "violations": violations,
        }

    def _check_non_negative(self, beams: list) -> dict[str, Any]:
        violations = 0
        for beam in beams:
            lm = beam.get("length_model", {})
            for field in (
                "centerline_length",
                "support_face_length",
                "bearing_length_left",
                "bearing_length_right",
                "clear_span",
                "effective_span",
                "design_span",
            ):
                value = lm.get(field, {}).get("value")
                if value is not None and float(value) < 0:
                    violations += 1
            gov = lm.get("governing_span", {}).get("value")
            if gov is not None and float(gov) < 0:
                violations += 1
        ok = violations == 0
        return {
            "name": "Non-Negative Lengths",
            "status": "PASS" if ok else "FAIL",
            "violations": violations,
        }
