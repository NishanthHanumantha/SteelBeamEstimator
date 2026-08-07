"""
QA.3.3 validation gates.
MODEL_VERSION: 10.0.3
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

MODEL_VERSION = "10.0.3"
PHASE_ID = "QA.3.3"

REQUIRED_OUTPUTS = (
    "CandidateDiscovery.json",
    "CandidateDiscovery.xlsx",
    "OwnershipScores.json",
    "ConflictResolution.json",
    "EntityDecisionTrace.json",
    "OwnershipCoverage.json",
    "OwnershipFailureClassification.json",
    "OwnershipStatistics.json",
    "BeamOwnershipCards.md",
    "OwnershipDecisionTrees.md",
    "OwnershipHeatmaps.md",
    "EngineeringRecommendations.md",
    "ExecutionSummary.md",
    "README.md",
)

REQUIRED_DIRS = (
    "CandidateEnvelopeOverlays",
    "CompetingBeamOverlays",
    "DecisionFlowCharts",
)


class QAValidator:
    def validate(
        self,
        out_root: Path,
        beam_ids: Sequence[str],
        records: List[Dict[str, Any]],
        aggregate: Dict[str, Any],
        meta: Dict[str, Any],
        recommendations: Dict[str, Any],
    ) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        def add(name: str, ok: bool, detail: str = "") -> None:
            checks.append({"check": name, "pass": bool(ok), "detail": detail})

        add(
            "version10_only",
            "Version10" in str(meta.get("engine_root") or ""),
            str(meta.get("engine_root")),
        )
        add(
            "no_production_regeneration",
            meta.get("production_regenerated") is False,
            "read-only artefacts",
        )
        add(
            "engineering_modules_unmodified",
            meta.get("engineering_modules_modified") is False,
            "diagnostic package only",
        )
        add(
            "ownership_decisions_not_mutated",
            meta.get("ownership_decisions_mutated") is False,
            "explainability only",
        )

        got = {r.get("beam_id") for r in records}
        missing = [b for b in beam_ids if b not in got]
        add("all_priority_beams_processed", len(missing) == 0, str(missing))

        missing_out = [n for n in REQUIRED_OUTPUTS if not (out_root / n).exists()]
        add("required_outputs_present", len(missing_out) == 0, str(missing_out))

        missing_dirs = [n for n in REQUIRED_DIRS if not (out_root / n).is_dir()]
        add("visual_directories_present", len(missing_dirs) == 0, str(missing_dirs))

        # Every beam has decision traces
        traces_ok = all(
            ((r.get("stage4_decision_traces") or {}).get("trace_count") or 0) >= 0
            and "traces" in (r.get("stage4_decision_traces") or {})
            for r in records
        )
        add("decision_traces_present", traces_ok and len(records) > 0, "")

        # Failure classification exactly one primary
        causes = {
            "Candidate Discovery",
            "Search Envelope",
            "Candidate Filtering",
            "Ownership Scoring",
            "Conflict Resolution",
            "Annotation Dependency",
            "Topology",
            "Mixed",
        }
        class_ok = True
        for r in records:
            pc = (r.get("stage6_failure_classification") or {}).get("primary_cause")
            if pc not in causes:
                class_ok = False
        add("failure_classification_valid", class_ok, "")

        freq = aggregate.get("failure_frequency_by_category") or {}
        freq_sum = sum(int(v) for v in freq.values())
        add(
            "failure_frequency_sums_to_beams",
            freq_sum == len(records),
            f"freq_sum={freq_sum} beams={len(records)}",
        )

        pris = recommendations.get("priorities") or []
        add(
            "recommendations_have_p1_p2_p3",
            len(pris) >= 3 and {p.get("priority") for p in pris} >= {1, 2, 3},
            "",
        )

        # Explainability completeness: scored entities have breakdown
        score_ok = True
        for r in records:
            for s in (r.get("stage2_ownership_scoring") or {}).get("t18_scored_entities") or []:
                if "score_breakdown" not in s and s.get("accepted") is not None:
                    score_ok = False
        add("score_breakdowns_exposed", score_ok, "")

        add(
            "black_box_removed_signal",
            aggregate.get("most_common_rejection_reason") is not None
            or aggregate.get("failure_frequency_by_category") is not None,
            str(aggregate.get("most_common_rejection_reason")),
        )

        overall = all(c["pass"] for c in checks)
        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_pass": overall,
            "checks": checks,
            "pass_count": sum(1 for c in checks if c["pass"]),
            "fail_count": sum(1 for c in checks if not c["pass"]),
        }
        (out_root / "QA33Validation.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result
