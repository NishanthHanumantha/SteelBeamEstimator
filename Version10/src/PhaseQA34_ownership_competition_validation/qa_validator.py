"""
QA.3.4 acceptance gates.
MODEL_VERSION: 10.0.4
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

MODEL_VERSION = "10.0.4"
PHASE_ID = "QA.3.4"

REQUIRED = (
    "OwnershipCompetitionRegistry.json",
    "CompetitionMatrix.json",
    "OwnershipMigration.json",
    "DroppedEntities.json",
    "BeamCompetitionSummary.json",
    "GlobalCompetitionStatistics.json",
    "CompetitionValidation.json",
    "RegressionReport.json",
    "ArchitectureSummary.md",
    "ValidationSummary.md",
    "ExecutionSummary.md",
    "README.md",
)

CATEGORIES = {
    "OWNED_ELSEWHERE",
    "LEADER_FAILURE",
    "GEOMETRY_FAILURE",
    "SEARCH_ENVELOPE_FAILURE",
    "CONFLICT_FAILURE",
    "UNKNOWN",
}


class QAValidator:
    def validate(
        self,
        out_root: Path,
        beam_ids: Sequence[str],
        all_classified: List[Dict[str, Any]],
        global_stats: Dict[str, Any],
        regression: Dict[str, Any],
        meta: Dict[str, Any],
        recommendations: Dict[str, Any],
    ) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        def add(name: str, ok: bool, detail: str = "") -> None:
            checks.append({"check": name, "pass": bool(ok), "detail": detail})

        add("version10_only", "Version10" in str(meta.get("engine_root") or ""), str(meta.get("engine_root")))
        add("no_production_regeneration", meta.get("production_regenerated") is False, "")
        add("engineering_modules_unmodified", meta.get("engineering_modules_modified") is False, "")
        add("ownership_decisions_not_mutated", meta.get("ownership_decisions_mutated") is False, "")
        add("regression_gate_pass", bool(regression.get("overall_pass")), str(regression.get("ownership_decisions_changed")))

        missing = [n for n in REQUIRED if not (out_root / n).exists()]
        add("required_outputs_present", len(missing) == 0, str(missing))
        add("visualisations_dir_present", (out_root / "Visualisations").is_dir(), "")

        # Every rejected entity: exactly one category + OwnedElsewhere or Dropped
        class_ok = True
        final_ok = True
        unknown_n = 0
        total_rows = 0
        for c in all_classified:
            for r in c.get("rejected_records") or []:
                total_rows += 1
                if r.get("category") not in CATEGORIES:
                    class_ok = False
                if r.get("final_state") not in ("OwnedElsewhere", "Dropped"):
                    final_ok = False
                if r.get("category") == "UNKNOWN":
                    unknown_n += 1
        add("exactly_one_classification", class_ok and total_rows > 0, f"rows={total_rows}")
        add("every_reject_owned_elsewhere_or_dropped", final_ok, "")
        add(
            "unknown_not_dominant",
            unknown_n <= max(1, total_rows // 5),
            f"unknown={unknown_n}/{total_rows}",
        )

        # Stats consistency
        oe = int(global_stats.get("owned_elsewhere") or 0)
        dr = int(global_stats.get("dropped") or 0)
        tot = int(global_stats.get("total_rejected") or 0)
        add(
            "owned_elsewhere_plus_dropped_equals_rejected",
            oe + dr == tot,
            f"{oe}+{dr}=={tot}",
        )

        # Competition winners recorded for OwnedElsewhere
        winners_ok = True
        for c in all_classified:
            for r in c.get("rejected_records") or []:
                if r.get("final_state") == "OwnedElsewhere" and not r.get("winning_beam"):
                    winners_ok = False
        add("owned_elsewhere_has_winner", winners_ok, "")

        # Disappearing entities identified
        dropped_path = out_root / "DroppedEntities.json"
        dropped_ok = False
        if dropped_path.exists():
            d = json.loads(dropped_path.read_text(encoding="utf-8"))
            dropped_ok = int(d.get("count") or 0) == dr
        add("disappearing_entities_identified", dropped_ok, f"dropped={dr}")

        pris = recommendations.get("priorities") or []
        add(
            "recommendations_have_p1_p2_p3",
            len(pris) >= 3 and {p.get("priority") for p in pris} >= {1, 2, 3},
            "",
        )
        add("beams_processed", len(all_classified) == len(beam_ids), f"{len(all_classified)}/{len(beam_ids)}")

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
        (out_root / "QA34Validation.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result
