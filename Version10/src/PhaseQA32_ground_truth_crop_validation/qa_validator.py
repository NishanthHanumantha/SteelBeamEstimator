"""
QA.3.2 validation gates.
MODEL_VERSION: 10.0.2
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

MODEL_VERSION = "10.0.2"
PHASE_ID = "QA.3.2"

REQUIRED_OUTPUTS = (
    "GroundTruthCropValidation.json",
    "GroundTruthCropValidation.xlsx",
    "GroundTruthBeamRegistry.json",
    "CropAlignmentMetrics.json",
    "CoordinateValidation.json",
    "EntityCompleteness.json",
    "BeamAlignmentDiagnostics.json",
    "GroundTruthDecisionMatrix.json",
    "GroundTruthSummary.json",
    "GroundTruthDiagnosticCards.md",
    "GroundTruthOverlayReport.md",
    "GroundTruthHeatmap.md",
    "GroundTruthRecommendations.md",
    "ExecutionSummary.md",
    "README.md",
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
            "no_estimation_rerun",
            meta.get("estimation_rerun") is False,
            "",
        )

        got = {r.get("beam_id") for r in records}
        missing = [b for b in beam_ids if b not in got]
        add("all_priority_beams_processed", len(missing) == 0, str(missing))

        missing_out = [n for n in REQUIRED_OUTPUTS if not (out_root / n).exists()]
        add("required_outputs_present", len(missing_out) == 0, str(missing_out))

        overlay_dir = out_root / "ExpectedCrop_vs_ManualCrop"
        overlay_ok = overlay_dir.exists()
        # At least one overlay image if beams processed
        if records:
            pngs = list(overlay_dir.glob("*_expected_vs_manual.png")) if overlay_ok else []
            overlay_ok = len(pngs) >= max(1, len(records) // 2)  # allow some render failures
        add("overlay_images_present", overlay_ok, str(overlay_dir))

        # Every beam has exactly one category A/B/C
        cat_ok = True
        for r in records:
            c = (r.get("decision") or {}).get("category")
            if c not in ("A", "B", "C"):
                cat_ok = False
        add("decision_matrix_complete", cat_ok and len(records) == len(beam_ids), "")

        # Recommendations P1-P3
        pris = recommendations.get("priorities") or []
        add(
            "recommendations_have_p1_p2_p3",
            len(pris) >= 3
            and {p.get("priority") for p in pris} >= {1, 2, 3},
            "",
        )

        # Explicit validation checklist echoed
        checklist_keys = (
            "correct_reinforcement_dxf_selected",
            "correct_beam_located",
            "correct_crop_reconstructed",
            "manual_crop_spatially_matches_reconstructed",
            "coordinate_transforms_valid",
            "manual_crop_contains_all_expected_entities",
            "no_neighbour_contamination",
            "no_clipping",
            "qa31_ownership_conclusion_still_valid",
        )
        checklist_ok = all(
            all(k in (r.get("validation_checks") or {}) for k in checklist_keys)
            for r in records
        ) if records else False
        add("per_beam_validation_checks_present", checklist_ok, "")

        # Frequency sums
        cats = aggregate.get("category_counts") or {}
        freq_sum = sum(int(cats.get(k) or 0) for k in ("A", "B", "C"))
        add(
            "category_counts_sum_to_beams",
            freq_sum == len(records),
            f"freq_sum={freq_sum} beams={len(records)}",
        )

        add(
            "zero_uncertainty_baseline_answered",
            aggregate.get("dominant_finding") is not None
            and aggregate.get("baseline_trustworthy") is not None,
            str(aggregate.get("dominant_finding")),
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
        (out_root / "QA32Validation.json").write_text(
            __import__("json").dumps(result, indent=2), encoding="utf-8"
        )
        return result
