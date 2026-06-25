"""Phase D.3.1 — aggregate validation for beam group confidence scores."""

from typing import Any, Dict, List, Literal

from src.framing.beam_geometry import beam_mark_sort_key

ValidationStatus = Literal["PASS", "WARN", "FAIL"]


class BeamGroupValidatorV2:
    """Read-only validation of D.3 beam group confidence results."""

    def validate(
        self,
        confidence_results: List[dict[str, Any]],
    ) -> Dict[str, Any]:
        high = [r for r in confidence_results if r["confidence"] == "HIGH"]
        medium = [r for r in confidence_results if r["confidence"] == "MEDIUM"]
        low = [r for r in confidence_results if r["confidence"] == "LOW"]
        invalid = [
            r
            for r in confidence_results
            if any("INVALID_GROUP" in w for w in r.get("warnings", []))
        ]

        warnings: List[str] = []
        for result in confidence_results:
            if result["is_multi_beam"] and result["confidence"] == "LOW":
                warnings.append(
                    f"{result['group_id']}: low-confidence multi-beam group "
                    f"({', '.join(result['members'])})"
                )

        multi_low = [r for r in confidence_results if r["is_multi_beam"] and r["confidence"] == "LOW"]
        if multi_low:
            warnings.append(
                f"{len(multi_low)} multi-beam group(s) flagged LOW — review before shared ownership"
            )

        status: ValidationStatus = "PASS"
        if invalid:
            status = "WARN"
        if len(multi_low) >= 2:
            status = "WARN"
        if any(r["confidence_score"] < 40 for r in confidence_results):
            status = "FAIL"

        recommended_corrections = sorted(
            {
                r["recommendation"]
                for r in confidence_results
                if r.get("recommendation", "").startswith("SPLIT")
            }
        )

        parser_ready = status != "FAIL" and len(invalid) == 0

        return {
            "status": status,
            "total_groups": len(confidence_results),
            "high_confidence_count": len(high),
            "medium_confidence_count": len(medium),
            "low_confidence_count": len(low),
            "invalid_group_count": len(invalid),
            "high_confidence_groups": [
                {"group_id": r["group_id"], "members": r["members"], "score": r["confidence_score"]}
                for r in sorted(high, key=lambda x: beam_mark_sort_key(x["members"][0]))
            ],
            "low_confidence_groups": [
                {
                    "group_id": r["group_id"],
                    "members": r["members"],
                    "score": r["confidence_score"],
                    "recommendation": r.get("recommendation"),
                }
                for r in sorted(low, key=lambda x: beam_mark_sort_key(x["members"][0]))
            ],
            "invalid_groups": [
                {"group_id": r["group_id"], "members": r["members"]} for r in invalid
            ],
            "warnings": warnings,
            "recommended_corrections": recommended_corrections,
            "parser_ready": parser_ready,
        }
