"""P2.5.8 STATUS + required artefacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import ENGINEERING_CHANGES, MODEL_VERSION, PHASE_ID, PHASE_NAME


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _fmt(v: Any) -> str:
    if v is None:
        return "N/A"
    return str(v)


def write_reports(*, out_root: Path, summary: Dict[str, Any]) -> Dict[str, str]:
    out_root = Path(out_root)
    reports = out_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ds = summary.get("dataset") or {}
    vis = summary.get("vision") or {}
    cost = summary.get("cost") or {}
    field = summary.get("field_impact") or {}
    eng = summary.get("engineering") or {}
    stirrup = summary.get("stirrup") or {}
    beam = summary.get("beam_impact") or {}
    safety = summary.get("safety") or {}
    unit = summary.get("unit_tests") or {}
    reg = summary.get("regression") or {}
    prod = summary.get("production") or {}

    lines = [
        "# P2.5.8 STATUS",
        "",
        "---------------------------------------------------",
        "IDENTITY",
        "---------------------------------------------------",
        "",
        f"MODEL_VERSION: {MODEL_VERSION}",
        f"PHASE_ID: {PHASE_ID}",
        f"PHASE_NAME: {PHASE_NAME}",
        f"STATUS: {summary.get('pass_fail')}",
        f"FINAL_DECISION: {summary.get('decision')}",
        "",
        "---------------------------------------------------",
        "DATASET",
        "---------------------------------------------------",
        "",
        f"drawing sets: {ds.get('drawing_sets')}",
        f"DXF count: {ds.get('dxf_count')}",
        f"beam count: {ds.get('beam_count')}",
        f"candidate count: {ds.get('candidate_count')}",
        "",
        "---------------------------------------------------",
        "VISION",
        "---------------------------------------------------",
        "",
        f"candidates available: {vis.get('candidates_available')}",
        f"candidates eligible: {vis.get('candidates_eligible')}",
        f"fields promoted: {vis.get('fields_promoted')}",
        f"fields blocked: {vis.get('fields_blocked')}",
        f"Claude calls: {cost.get('live_claude_calls')}",
        f"Claude cost: {_fmt(cost.get('estimated_cost_usd'))}",
        f"mode: {summary.get('mode')}",
        "",
        "---------------------------------------------------",
        "FIELD IMPACT",
        "---------------------------------------------------",
        "",
    ]
    for fname in ("diameter", "legs", "spacing", "reinforcement_role"):
        rec = field.get(fname) or {}
        lines.append(
            f"- {fname}: before={rec.get('before_confirmed_or_known')} "
            f"after={rec.get('after_confirmed_or_repaired')} "
            f"promoted={rec.get('promoted')}"
        )
    lines += [
        "",
        "---------------------------------------------------",
        "ENGINEERING IMPACT",
        "---------------------------------------------------",
        "",
        f"baseline steel: {_fmt(eng.get('baseline_steel_kg'))} kg",
        f"Vision-assisted steel: {_fmt(eng.get('vision_assisted_steel_kg'))} kg",
        f"estimator steel: {_fmt(eng.get('estimator_steel_kg'))} kg",
        f"baseline accuracy: {_fmt(eng.get('baseline_accuracy'))}%",
        f"Vision-assisted accuracy: {_fmt(eng.get('vision_assisted_accuracy'))}%",
        f"improvement: {_fmt(eng.get('STEEL_ACCURACY_IMPROVEMENT'))} percentage points",
        f"error reduction: {_fmt(eng.get('error_reduction_percent'))}%",
        f"absolute steel error baseline: {_fmt(eng.get('absolute_steel_error_baseline'))}%",
        f"absolute steel error vision: {_fmt(eng.get('absolute_steel_error_vision'))}%",
        "",
        "---------------------------------------------------",
        "STIRRUP",
        "---------------------------------------------------",
        "",
        f"before steel: {_fmt(stirrup.get('baseline_stirrup_steel'))} kg",
        f"after steel: {_fmt(stirrup.get('shadow_stirrup_steel'))} kg",
        f"estimator steel: {_fmt(stirrup.get('ground_truth_stirrup_steel'))} kg",
        f"accuracy before: {_fmt(stirrup.get('stirrup_accuracy_before'))}%",
        f"accuracy after: {_fmt(stirrup.get('stirrup_accuracy_after'))}%",
        f"improvement: {_fmt(stirrup.get('improvement_pp'))} percentage points",
        f"quantity before: {_fmt(stirrup.get('baseline_stirrup_quantity'))}",
        f"quantity after: {_fmt(stirrup.get('shadow_stirrup_quantity'))}",
        f"quantity estimator: {_fmt(stirrup.get('ground_truth_stirrup_quantity'))}",
        "",
        "---------------------------------------------------",
        "BEAM IMPACT",
        "---------------------------------------------------",
        "",
        f"improved beams: {beam.get('beams_improved')}",
        f"unchanged beams: {beam.get('beams_unchanged')}",
        f"worsened beams: {beam.get('beams_worsened')}",
        f"newly resolved: {beam.get('beams_newly_resolved')}",
        f"still unresolved: {beam.get('beams_still_unresolved')}",
        "",
        "---------------------------------------------------",
        "SAFETY",
        "---------------------------------------------------",
        "",
        f"conflicts: {safety.get('conflicts')}",
        f"blocked fields: {safety.get('blocked_fields')}",
        f"validation failures: {safety.get('validation_failures')}",
        f"production mutations: {prod.get('production_mutation_count')}",
        f"production output difference: {prod.get('production_output_difference')}",
        f"steel production difference: {prod.get('steel_production_difference')}",
        f"BBS production difference: {prod.get('bbs_production_difference')}",
        f"Excel production difference: {prod.get('excel_production_difference')}",
        "",
        "---------------------------------------------------",
        "REGRESSION",
        "---------------------------------------------------",
        "",
        f"P2.5.1: {reg.get('p251')}",
        f"P2.5.4: {reg.get('p254')}",
        f"P2.5.5: {reg.get('p255')}",
        f"P2.5.6: {reg.get('p256')}",
        f"P2.5.7: {reg.get('p257')}",
        f"fingerprint unchanged: {reg.get('unchanged')}",
        "",
        "---------------------------------------------------",
        "COST",
        "---------------------------------------------------",
        "",
        f"new Claude calls: {cost.get('live_claude_calls')}",
        f"tokens in: {cost.get('input_tokens')}",
        f"tokens out: {cost.get('output_tokens')}",
        f"estimated cost: {_fmt(cost.get('estimated_cost_usd'))}",
        f"replay: {cost.get('replay')}",
        "",
        "---------------------------------------------------",
        "ENGINEERING CHANGES",
        "---------------------------------------------------",
        "",
        f"{ENGINEERING_CHANGES}",
        "",
        "---------------------------------------------------",
        "TESTS",
        "---------------------------------------------------",
        "",
        f"passed: {unit.get('passed')}/{unit.get('total')}",
        f"success: {unit.get('success')}",
        "",
        "---------------------------------------------------",
        "FINAL DECISION",
        "---------------------------------------------------",
        "",
        str(summary.get("decision") or ""),
        "",
        str(summary.get("recommendation") or ""),
        "",
    ]
    status_md = "\n".join(lines)
    (out_root / "P2.5.8_STATUS.md").write_text(status_md, encoding="utf-8")
    (reports / "P2.5.8_STATUS.md").write_text(status_md, encoding="utf-8")
    _dump(out_root / "evaluation" / "summary.json", summary)
    return {
        "status_md": str(out_root / "P2.5.8_STATUS.md"),
        "summary_json": str(out_root / "evaluation" / "summary.json"),
    }


__all__ = ["write_reports"]
