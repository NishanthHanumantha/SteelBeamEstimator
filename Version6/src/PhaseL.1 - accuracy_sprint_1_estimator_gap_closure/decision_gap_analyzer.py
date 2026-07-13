"""Decision-level gap analysis — what decisions cover vs what estimator expects."""

from __future__ import annotations

from typing import Any, Dict, List


class DecisionGapAnalyzer:
    """Measure engineering decision coverage against estimator ground truth."""

    def analyze(
        self,
        snapshot: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        decisions = snapshot.get("decisions") or []
        decisions_by_beam = snapshot.get("decisions_by_beam") or {}
        decisions_by_category = snapshot.get("decisions_by_category") or {}
        est = snapshot.get("estimator_data") or {}
        est_beams = set(est.get("beam_blocks", {}).keys())
        per_beam_comp = comparison.get("per_beam") or []

        # Beam-level decision presence
        beams_with_decisions = set(decisions_by_beam.keys())
        beams_covered = est_beams & beams_with_decisions
        beams_no_decisions = est_beams - beams_with_decisions

        # Category distribution
        category_dist: List[Dict[str, Any]] = []
        for cat, dec_list in sorted(decisions_by_category.items()):
            beams_for_cat = {str(d.get("beam_id") or "") for d in dec_list if d.get("beam_id")}
            category_dist.append({
                "category": cat,
                "decision_count": len(dec_list),
                "beam_count": len(beams_for_cat),
                "estimator_equivalent_role": self._cat_to_role(cat),
                "in_estimator": self._is_in_estimator(cat),
            })

        # Per-beam decision gap
        per_beam_gap: List[Dict[str, Any]] = []
        for beam_mark in sorted(est_beams):
            dec = decisions_by_beam.get(beam_mark, [])
            est_block = (est.get("beam_blocks") or {}).get(beam_mark, {})
            est_rows = est_block.get("row_count", 0)
            per_beam_gap.append({
                "beam_mark": beam_mark,
                "decision_count": len(dec),
                "estimator_rows": est_rows,
                "decision_categories": sorted({str(d.get("decision_category") or "") for d in dec}),
                "gap_assessment": "NO_DECISIONS" if not dec else (
                    "PARTIAL" if est_rows > len(dec) else "ADEQUATE"
                ),
            })

        # Execution gate
        exec_ids = snapshot.get("execution_allowed_ids") or set()
        exec_allowed = len(exec_ids)
        exec_blocked = len(decisions) - exec_allowed

        return {
            "total_decisions": len(decisions),
            "decisions_by_category": category_dist,
            "beam_decision_coverage_percent": round(
                100 * len(beams_covered) / max(len(est_beams), 1), 2
            ),
            "beams_with_decisions": len(beams_covered),
            "beams_without_decisions": len(beams_no_decisions),
            "beams_no_decisions_list": sorted(beams_no_decisions),
            "execution_allowed": exec_allowed,
            "execution_blocked": exec_blocked,
            "execution_allowed_percent": round(
                100 * exec_allowed / max(len(decisions), 1), 2
            ),
            "per_beam_gap": per_beam_gap,
            "missing_categories": [
                c for c in (
                    "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA", "STIRRUP",
                    "SIDE_FACE", "SPACER_BAR", "CHAIR_BAR",
                )
                if c not in decisions_by_category
            ],
        }

    @staticmethod
    def _cat_to_role(cat: str) -> str:
        c = cat.upper()
        if "SUPPORT_REINFORCEMENT" in c and "CONTINUOUS" not in c:
            return "BOTTOM_MAIN"
        if "CONTINUOUS" in c:
            return "TOP_MAIN"
        if "SUPPLEMENTARY" in c:
            return "TOP_MAIN/SUPPLEMENTARY"
        return "UNKNOWN"

    @staticmethod
    def _is_in_estimator(cat: str) -> bool:
        return cat.startswith("SUPPLEMENTARY_") or "SUPPORT" in cat
