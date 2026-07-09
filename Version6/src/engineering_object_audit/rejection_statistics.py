"""Aggregate engineering object rejection statistics."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from src.engineering_object_audit.audit_collector import REJECTION_CODES, round_pct


IMPACT_BY_CODE = {
    "MISSING_SPECIFICATION": "Very High",
    "DUPLICATE_SUPPRESSED": "High",
    "MISSING_GEOMETRY": "High",
    "MISSING_POSITION": "High",
    "MISSING_BAR_ROLE": "Medium",
    "MISSING_DIAMETER": "Medium",
    "MISSING_QUANTITY": "Medium",
    "ENGINEERING_RULE_CONFLICT": "Medium",
    "NORMALIZATION_FAILED": "Medium",
    "AMBIGUOUS_CALLOUT": "Low",
    "UNSUPPORTED_NOTATION": "Low",
    "UNKNOWN": "Low",
}


class RejectionStatistics:
    """Rank rejection codes by engineering impact."""

    def build(
        self,
        audits: List[dict[str, Any]],
        inventory_count: int,
    ) -> dict[str, Any]:
        rejected = [item for item in audits if not item.get("engineering_object_created")]
        primary_counts: Counter[str] = Counter()
        secondary_counts: Counter[str] = Counter()
        for item in rejected:
            code = item.get("primary_rejection_code") or "UNKNOWN"
            primary_counts[code] += 1
            for secondary in item.get("secondary_codes") or []:
                secondary_counts[secondary] += 1

        ranked = []
        for code, count in primary_counts.most_common():
            ranked.append(
                {
                    "rejection_code": code,
                    "count": count,
                    "percentage": round_pct(count, inventory_count),
                    "engineering_impact": IMPACT_BY_CODE.get(code, "Medium"),
                }
            )

        return {
            "total_annotations": inventory_count,
            "rejected_count": len(rejected),
            "accepted_count": inventory_count - len(rejected),
            "acceptance_rate_percent": round_pct(inventory_count - len(rejected), inventory_count),
            "primary_rejection_codes": ranked,
            "secondary_rejection_codes": [
                {"rejection_code": code, "count": count}
                for code, count in secondary_counts.most_common()
            ],
            "valid_codes": list(REJECTION_CODES),
        }
