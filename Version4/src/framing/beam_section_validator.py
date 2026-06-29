"""Validate Phase F.3 BeamSection engineering objects."""

from __future__ import annotations



class BeamSectionValidator:
    """Verify BeamSection properties and derived geometry."""

    def __init__(self, config: dict[str, Any]) -> None:
        sb = config.get("beam_section", {})
        self._deep_ratio = float(sb.get("deep_section_ratio", 2.0))
        self._tolerance = float(sb.get("property_tolerance", 0.5))

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        beams = model.get("beams", [])

        checks.append(self._check_section_exists(beams))
        checks.append(self._check_shape_and_classification(beams))
        checks.append(self._check_area(beams))
        checks.append(self._check_perimeter(beams))
        checks.append(self._check_aspect_ratio(beams))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase F.3",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "beam_count": len(beams),
            },
        }

    def _check_section_exists(self, beams: list) -> dict[str, Any]:
        with_section = sum(1 for b in beams if isinstance(b.get("beam_section"), dict))
        ok = with_section == len(beams) and with_section > 0
        return {
            "name": "BeamSection Exists",
            "status": "PASS" if ok else "FAIL",
            "with_section": with_section,
            "total": len(beams),
        }

    def _check_shape_and_classification(self, beams: list) -> dict[str, Any]:
        missing = 0
        for beam in beams:
            section = beam.get("beam_section", {})
            if not section.get("shape") or not section.get("classification"):
                missing += 1
        ok = missing == 0
        return {
            "name": "Shape and Classification",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_area(self, beams: list) -> dict[str, Any]:
        errors = 0
        for beam in beams:
            section = beam.get("beam_section", {})
            w = section.get("width", {}).get("value")
            d = section.get("depth", {}).get("value")
            area = section.get("cross_section_area", {}).get("value")
            if w is None or d is None:
                continue
            expected = float(w) * float(d)
            if area is None or abs(float(area) - expected) > self._tolerance:
                errors += 1
        ok = errors == 0
        return {
            "name": "Cross Section Area",
            "status": "PASS" if ok else "FAIL",
            "errors": errors,
        }

    def _check_perimeter(self, beams: list) -> dict[str, Any]:
        errors = 0
        for beam in beams:
            section = beam.get("beam_section", {})
            w = section.get("width", {}).get("value")
            d = section.get("depth", {}).get("value")
            perimeter = section.get("perimeter", {}).get("value")
            if w is None or d is None:
                continue
            expected = 2.0 * (float(w) + float(d))
            if perimeter is None or abs(float(perimeter) - expected) > self._tolerance:
                errors += 1
        ok = errors == 0
        return {
            "name": "Perimeter",
            "status": "PASS" if ok else "FAIL",
            "errors": errors,
        }

    def _check_aspect_ratio(self, beams: list) -> dict[str, Any]:
        errors = 0
        for beam in beams:
            section = beam.get("beam_section", {})
            w = section.get("width", {}).get("value")
            d = section.get("depth", {}).get("value")
            ratio = section.get("aspect_ratio", {}).get("value")
            if w is None or d is None or float(w) <= 0:
                continue
            expected = float(d) / float(w)
            if ratio is None or abs(float(ratio) - expected) > 0.01:
                errors += 1
            classification = section.get("classification")
            if classification == "DEEP_SECTION" and expected < self._deep_ratio:
                errors += 1
            if classification == "NORMAL_SECTION" and expected >= self._deep_ratio:
                errors += 1
        ok = errors == 0
        return {
            "name": "Aspect Ratio",
            "status": "PASS" if ok else "FAIL",
            "errors": errors,
        }
