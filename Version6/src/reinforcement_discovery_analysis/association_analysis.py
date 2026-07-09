"""Analyse reinforcement beam association."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


class AssociationAnalyzer:
    """Aggregate beam association outcomes."""

    def analyze(self, inventory: List[dict[str, Any]]) -> dict[str, Any]:
        total = len(inventory)
        associated = sum(1 for item in inventory if item.get("associated"))
        unknown_beam = sum(
            1 for item in inventory if item.get("classified") and not item.get("beam_association")
        )
        multiple_candidates = sum(
            1
            for item in inventory
            if item.get("association_source") == "MULTIPLE_CANDIDATES"
        )
        nearest_beam = sum(
            1 for item in inventory if item.get("association_source") == "NEAREST_BEAM"
        )
        region_conflict = sum(
            1 for item in inventory if item.get("association_source") == "REGION_CONFLICT"
        )
        missing_geometry = sum(
            1 for item in inventory if item.get("failure_reason") == "Missing geometry"
        )

        causes: Counter[str] = Counter()
        examples: Dict[str, List[dict[str, Any]]] = {}
        for item in inventory:
            if item.get("associated"):
                continue
            if not item.get("classified"):
                continue
            reason = "Unknown beam"
            source = str(item.get("association_source") or "")
            if source == "MULTIPLE_CANDIDATES":
                reason = "Multiple candidate beams"
            elif source == "NEAREST_BEAM":
                reason = "Nearest beam heuristic"
            elif source == "REGION_CONFLICT":
                reason = "Region conflict"
            elif not item.get("beam_association"):
                reason = "Unknown beam"
            causes[reason] += 1
            examples.setdefault(reason, [])
            if len(examples[reason]) < 5:
                examples[reason].append(
                    {
                        "discovery_id": item.get("discovery_id"),
                        "original_text": item.get("original_text"),
                        "coordinates": item.get("coordinates"),
                    }
                )

        return {
            "total_callouts": total,
            "associated": associated,
            "unknown_beam": unknown_beam,
            "multiple_candidate_beams": multiple_candidates,
            "nearest_beam_heuristic": nearest_beam,
            "region_conflict": region_conflict,
            "missing_geometry": missing_geometry,
            "association_success_percent": round((associated / total) * 100.0, 2) if total else 0.0,
            "causes": [
                {"reason": reason, "count": count, "examples": examples.get(reason, [])}
                for reason, count in causes.most_common()
            ],
        }
