"""Build the master engineering improvement roadmap."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


FUTURE_PHASES = {
    "Phase L.2": {
        "phase": "Phase L.2",
        "title": "Accuracy Sprint 2 — Targeted Engineering Rule Implementation",
        "expected_improvements": [
            "Implement Bottom Main rule",
            "Implement Top Extra rule",
            "Implement Bottom Extra rule",
            "Implement Stirrup rule",
            "Run full Version6 Phase I pipeline",
            "Fix partial Top Main coverage",
        ],
        "expected_accuracy_improvement_percent": 60.0,
    },
    "Phase L.3": {
        "phase": "Phase L.3",
        "title": "Accuracy Improvement Validation",
        "expected_improvements": [
            "Validate L.2 improvements against benchmark",
            "Close remaining rule gaps",
            "Chair bar and minimum reinforcement rules",
            "Excel format alignment",
        ],
        "expected_accuracy_improvement_percent": 15.0,
    },
    "Phase M.1": {
        "phase": "Phase M.1",
        "title": "Estimator Equivalence Engine",
        "expected_improvements": [
            "Full estimator equivalence target",
            "Company-specific rules",
            "100% coverage goal",
        ],
        "expected_accuracy_improvement_percent": 20.0,
    },
}


class ImprovementTracker:
    """Produce improvement roadmap from ranked gaps."""

    def build(
        self,
        ranked_gaps: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()

        improvements: List[Dict[str, Any]] = []
        for gap in ranked_gaps:
            future_phase = str(gap.get("future_phase") or "Phase L.2")
            improvements.append({
                "improvement_id": f"IMP::{gap.get('gap_id', '').split('::')[-1]}",
                "gap_id": gap.get("gap_id"),
                "gap_category": gap.get("gap_category"),
                "title": gap.get("title"),
                "priority": gap.get("priority"),
                "priority_rank": gap.get("priority_rank"),
                "status": "PENDING",
                "future_phase": future_phase,
                "expected_steel_impact_kg": gap.get("estimated_steel_impact_kg", 0.0),
                "affected_roles": gap.get("affected_roles") or [],
                "affected_beams_count": len(gap.get("affected_beams") or []) or "ALL",
                "resolved": False,
                "resolved_version": None,
                "created_version": "6.3.0",
                "created_phase": "Phase L.1",
                "created_timestamp": now,
            })

        # Phase grouping
        by_phase: Dict[str, List[str]] = {}
        for imp in improvements:
            ph = str(imp.get("future_phase") or "Phase L.2")
            by_phase.setdefault(ph, []).append(str(imp.get("gap_id") or ""))

        phase_roadmap: List[Dict[str, Any]] = []
        for phase_key, gap_ids in sorted(by_phase.items()):
            ph_meta = FUTURE_PHASES.get(phase_key, {"phase": phase_key})
            phase_roadmap.append({
                **ph_meta,
                "gap_count": len(gap_ids),
                "gap_ids": gap_ids,
            })

        return {
            "model_version": "6.3.0",
            "phase": "Phase L.1",
            "created_timestamp": now,
            "benchmark_project": "Sobha Galera Clubhouse",
            "current_accuracy": {
                "steel_coverage_percent": statistics.get("steel_coverage_percent", 0.0),
                "row_coverage_percent": statistics.get("row_coverage_percent", 0.0),
                "beam_coverage_percent": statistics.get("beam_coverage_percent", 0.0),
                "estimator_equivalence_percent": statistics.get("estimator_equivalence_percent", 0.0),
            },
            "target_accuracy": {
                "steel_coverage_percent": 95.0,
                "row_coverage_percent": 95.0,
                "beam_coverage_percent": 100.0,
                "estimator_equivalence_percent": 95.0,
            },
            "total_improvements": len(improvements),
            "improvements": improvements,
            "phase_roadmap": phase_roadmap,
            "history": [],
        }
