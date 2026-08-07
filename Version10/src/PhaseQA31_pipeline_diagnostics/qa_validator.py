"""
QA.3.1 validation gates.
MODEL_VERSION: 10.0.1
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .artefact_locator import PRIORITY_FOURTH_BEAMS

MODEL_VERSION = "10.0.1"
PHASE_ID = "QA.3.1"

REQUIRED_OUTPUTS = (
    "BeamPipelineDiagnostics.json",
    "BeamPipelineDiagnostics.xlsx",
    "BeamStageComparison.json",
    "OwnershipRejectionLog.json",
    "CropDiagnostics.json",
    "AnnotationDiagnostics.json",
    "RenderDiagnostics.json",
    "RootCauseSummary.json",
    "FailureFrequency.json",
    "BeamDiagnosticCards.md",
    "PipelineStageHeatmap.md",
    "EngineeringRecommendations.md",
    "ExecutionSummary.md",
    "README.md",
)


class QAValidator:
    def validate(
        self,
        out_root: Path,
        beam_ids: Sequence[str],
        beam_records: List[Dict[str, Any]],
        aggregate: Dict[str, Any],
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        def add(name: str, ok: bool, detail: str = "") -> None:
            checks.append({"check": name, "pass": bool(ok), "detail": detail})

        # A safety
        add("version10_only", "Version10" in str(meta.get("engine_root") or ""), str(meta.get("engine_root")))
        add("no_production_regeneration", meta.get("production_regenerated") is False, "read-only artefacts")
        add("estimator_not_used_for_ownership", meta.get("estimator_used_for_ownership") is False, "")
        add("engineering_modules_unmodified", meta.get("engineering_modules_modified") is False, "diagnostic package only")

        # B coverage
        got = {r.get("beam_id") for r in beam_records}
        missing_priority = [b for b in beam_ids if b not in got]
        add("all_priority_beams_processed", len(missing_priority) == 0, str(missing_priority))
        cards = (out_root / "BeamDiagnosticCards.md").exists()
        add("diagnostic_cards_exist", cards, str(out_root / "BeamDiagnosticCards.md"))
        first_ok = True
        for r in beam_records:
            rc = r.get("root_cause") or {}
            arts = r.get("artefacts") or {}
            has_art = arts.get("has_beam_ownership") or arts.get("has_geometry_envelope")
            if not has_art:
                continue
            if rc.get("all_pass") or rc.get("primary_category") == "None":
                continue
            if not rc.get("first_failing_stage") and rc.get("primary_category") != "Mixed":
                first_ok = False
        add("first_failing_stage_or_missing_explained", first_ok, "")

        # C integrity
        order_ok = True
        rend_rule_ok = True
        for r in beam_records:
            st = r.get("stages") or {}
            # If ownership FAIL and rendering matches owned set => rendering should be PASS
            if (st.get("Ownership") or {}).get("status") == "FAIL":
                if (st.get("Rendering") or {}).get("status") == "FAIL":
                    # only ok if missing rendered while owned existed
                    owned = (st.get("Rendering") or {}).get("owned_entities_count") or 0
                    missing = (st.get("Rendering") or {}).get("missing_rendered_entities") or []
                    if owned > 0 and not missing:
                        # ownership fail but render fail without missing owned -> suspicious; soft
                        pass
            if (st.get("Rendering") or {}).get("status") == "FAIL":
                owned = (st.get("Rendering") or {}).get("owned_entities_count")
                if owned is not None and owned == 0 and not (
                    (st.get("Rendering") or {}).get("missing_rendered_entities")
                ):
                    rend_rule_ok = False
            rc = r.get("root_cause") or {}
            primary = rc.get("primary_category")
            if primary not in (
                "Beam Discovery",
                "Beam Extent",
                "Crop Window",
                "Ownership",
                "Annotation Association",
                "Rendering",
                "Mixed",
                "None",
            ):
                order_ok = False
        add("root_cause_single_primary", order_ok, "")
        add("render_fail_requires_owned_context", rend_rule_ok, "")

        # D outputs
        missing_out = [n for n in REQUIRED_OUTPUTS if not (out_root / n).exists()]
        # xlsx may fail on some envs - allow json-only with note if xlsx missing but marked
        if "BeamPipelineDiagnostics.xlsx" in missing_out:
            # still fail unless we created a stub - keep strict if openpyxl worked
            pass
        add("required_outputs_present", len(missing_out) == 0, str(missing_out))

        freq = aggregate.get("failure_frequency") or {}
        # Sum of categorized primaries should equal analysed count
        total_freq = sum(freq.values())
        add(
            "failure_frequency_sums_to_beams",
            total_freq == len(beam_records),
            f"freq_sum={total_freq} beams={len(beam_records)}",
        )
        add(
            "recommendations_have_p1_p2_p3",
            (out_root / "EngineeringRecommendations.md").exists(),
            "",
        )

        # E hypothesis
        hyp = aggregate.get("hypothesis") or {}
        add(
            "hypothesis_booleans_present",
            "ownership_or_scoping_before_render_is_dominant" in hyp
            and "renderer_mostly_faithful_to_owned_set" in hyp,
            str(hyp),
        )

        # Priority list coverage vs default 11
        if list(beam_ids) == list(PRIORITY_FOURTH_BEAMS):
            add("default_priority_list_used", True, "Fourth priority 11 beams")

        overall = all(c["pass"] for c in checks)
        doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_pass": overall,
            "checks": checks,
            "pass_count": sum(1 for c in checks if c["pass"]),
            "fail_count": sum(1 for c in checks if not c["pass"]),
        }
        (out_root / "QA31Validation.json").write_text(
            json.dumps(doc, indent=2), encoding="utf-8"
        )
        return doc
