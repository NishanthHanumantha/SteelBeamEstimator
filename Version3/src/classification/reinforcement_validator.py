"""Phase D.4.1 — validation for reinforcement classification."""

from typing import Any, Dict, List, Literal

ValidationStatus = Literal["PASS", "WARN", "FAIL"]


class ReinforcementValidator:
    """Validate classification completeness."""

    def validate(
        self,
        engineering_objects: List[dict[str, Any]],
        classified: List[dict[str, Any]],
    ) -> Dict[str, Any]:
        success_objects = [
            o for o in engineering_objects if o.get("parser_status") == "SUCCESS"
        ]
        longitudinal = [
            c for c in classified
            if c.get("engineering_type") == "LONGITUDINAL_BAR"
        ]
        stirrups = [c for c in classified if c.get("estimator_category") == "STIRRUP"]
        anchorage = [
            c for c in classified
            if c.get("estimator_category") in ("ANCHORAGE", "HOOK")
        ]
        sfr = [
            c for c in classified
            if c.get("estimator_category") == "SIDE_FACE_REINFORCEMENT"
        ]

        missing_position = [
            c for c in longitudinal
            if c.get("position") not in ("TOP", "BOTTOM", "UNKNOWN")
        ]
        missing_continuity = [
            c for c in longitudinal
            if c.get("continuity") not in ("CONTINUOUS", "PARTIAL", "UNKNOWN")
        ]
        unclassified_bars = [
            c for c in longitudinal
            if c.get("estimator_category") == "UNCLASSIFIED"
        ]

        warnings: List[str] = []
        if unclassified_bars:
            warnings.append(
                f"{len(unclassified_bars)} longitudinal bar(s) UNCLASSIFIED"
            )
        if len(classified) < len(success_objects):
            warnings.append("Classification count below parsed object count")

        status: ValidationStatus = "PASS"
        if unclassified_bars:
            status = "WARN"

        return {
            "status": status,
            "parsed_object_count": len(success_objects),
            "classified_count": len(classified),
            "longitudinal_bar_count": len(longitudinal),
            "stirrup_count": len(stirrups),
            "anchorage_count": len(anchorage),
            "sfr_count": len(sfr),
            "unclassified_longitudinal_count": len(unclassified_bars),
            "warnings": warnings,
            "parser_ready": status != "FAIL",
        }
