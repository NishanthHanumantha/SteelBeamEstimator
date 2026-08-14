"""
P2.5.8 orchestrator — Controlled Vision Field-Repair & Engineering Recompute.

Replay frozen P2.5.7 live Vision results by default. Promoted stirrup
interpretation fields overlay a sandbox copy of R1.3 and the existing
VB.1 / SI.1 engine recomputes shadow steel. Production is untouched.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator  # noqa: E402

from .comparison import build_comparison  # noqa: E402
from .config import (  # noqa: E402
    ENGINEERING_CHANGES,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRIMARY_DRAWING_SET,
    PRIMARY_SET_KEY,
    PRODUCTION_WRITE,
    SCOPE,
)
from .live_refresh import refresh_live, replay_cost  # noqa: E402
from .metrics import (  # noqa: E402
    classify_decision,
    field_known_counts,
    promotion_safety,
)
from .p257_loader import load_p257_audits  # noqa: E402
from .promotion_gate import evaluate_audit  # noqa: E402
from .promotion_rules import load_promotion_rules  # noqa: E402
from .qa_benchmark import normalize_workbooks, run_fifth_benchmark  # noqa: E402
from .r13_overlay import apply_repairs, load_r13  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
)
from .report_builder import write_reports  # noqa: E402
from .shadow_recompute import copy_isolated, run_shadow_recompute  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _p257_manifest(v10: Path) -> Dict[str, Any]:
    p = (
        v10
        / "data"
        / "output"
        / "PhaseP257_unseen_drawing_controlled_vision_validation"
        / "dataset_manifest.json"
    )
    return _load_json(p) or {}


def run_phase_p258(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    live: bool = False,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (
        out_root,
        out_root / "config",
        out_root / "baseline",
        out_root / "vision_candidates",
        out_root / "promoted_repairs",
        out_root / "shadow_recompute",
        out_root / "comparison",
        out_root / "evaluation",
        out_root / "reports",
    ):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE if not live else 'LIVE'}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  production_write={PRODUCTION_WRITE} live={live}")
    _log(f"  output={out_root}")

    shutil.copy2(
        Path(__file__).with_name("vision_field_promotion_rules.yaml"),
        out_root / "config" / "vision_field_promotion_rules.yaml",
    )

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "evaluation" / "unit_tests.json", unit)
        _log(f"  Unit tests P258: {unit['passed']}/{unit['total']}")
        p257u = unit.get("p257_unit_tests") or {}
        _log(f"  Unit tests P257: {p257u.get('passed')}/{p257u.get('total')}")
        if not unit.get("success"):
            return {
                "success": False,
                "pass_fail": "FAIL",
                "decision": "BLOCKED — architecture correction required",
                "unit_tests": unit,
                "output_root": str(out_root),
            }

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)

    audits = load_p257_audits(v10)
    invoked = [a for a in audits if a.get("invoke_claude") and a.get("vision_result")]
    if live:
        audits, cost = refresh_live(version10_root=v10, audits=audits)
        invoked = [a for a in audits if a.get("invoke_claude") and a.get("vision_result")]
        mode = "LIVE"
    else:
        cost = replay_cost(len(invoked))
        mode = MODE

    _dump(out_root / "vision_candidates" / "p257_invoked_audits.json", invoked)

    rules = load_promotion_rules()
    candidates: List[Dict[str, Any]] = []
    for audit in invoked:
        candidates.extend(evaluate_audit(audit, rules=rules))
    promoted = [c for c in candidates if c.get("promotion_decision") == "CONTROLLED_RECOMPUTE"]
    _dump(out_root / "promotion_candidates.json", candidates)
    _dump(out_root / "promoted_repairs.json", promoted)
    _dump(out_root / "promoted_repairs" / "promoted_repairs.json", promoted)
    _dump(out_root / "vision_candidates" / "promotion_candidates.json", candidates)

    safety = promotion_safety(candidates)
    fields = field_known_counts(candidates)
    _dump(out_root / "evaluation" / "promotion_safety.json", safety)

    locator = ArtefactLocator(v10)
    art = locator.locate_set(PRIMARY_SET_KEY)
    if art.output_root is None or art.run_root is None:
        summary = {
            "pass_fail": "BLOCKED",
            "decision": "BLOCKED — architecture correction required",
            "error": "Fifth Set production artefacts not located",
            "unit_tests": unit,
            "cost": cost,
            "output_root": str(out_root),
        }
        write_reports(out_root=out_root, summary=summary)
        return summary

    prod_excel = Path(art.output_root) / "Production_Output" / "Estimation_Output.xlsx"
    prod_bbs = Path(art.output_root) / "Production_Output" / "bbs_summary.json"
    prod_r13 = (
        Path(art.output_root)
        / "PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json"
    )
    estimator = (
        Path(v10).parent
        / "Test_Input"
        / "Fifth Set Drawings"
        / "Estimator_Output_5thSet"
        / "EstimatorOutput_9TH FLOOR.xlsx"
    )
    meta = _load_json(art.mirror_dir / "run_metadata.json") or {}
    if meta.get("estimator_excel_path_recorded"):
        estimator = Path(meta["estimator_excel_path_recorded"])

    baseline_excel = copy_isolated(prod_excel, out_root / "baseline" / "Estimation_Output.xlsx")
    copy_isolated(prod_bbs, out_root / "baseline" / "bbs_summary.json")
    r13_doc = load_r13(prod_r13)
    _dump(out_root / "baseline" / "beam_reinforcement_models_production.json", r13_doc)

    patched, provenance = apply_repairs(
        r13_doc=r13_doc, audits=invoked, promoted=promoted
    )
    _dump(out_root / "shadow_recompute" / "overlay_provenance.json", provenance)
    _dump(
        out_root / "shadow_recompute" / "beam_reinforcement_models_shadow.json",
        patched,
    )

    ownership = art.load_json("beam_ownership") or {"by_beam": {}}
    scoped = art.load_json("beam_scoped")
    sandbox = out_root / "shadow_recompute" / "sandbox_vision_assisted"
    recompute = run_shadow_recompute(
        engine_root=v10,
        source_run_root=Path(art.run_root),
        ownership=ownership,
        patched_r13=patched,
        sandbox_root=sandbox,
        scoped=scoped,
    )
    _dump(out_root / "shadow_recompute" / "vb1_result.json", recompute)
    shadow_xlsx = None
    if recompute.get("success") and (recompute.get("vb1") or {}).get("workbook_path"):
        shadow_xlsx = copy_isolated(
            Path(recompute["vb1"]["workbook_path"]),
            out_root / "shadow_recompute" / "Estimation_Output.xlsx",
        )
        copy_isolated(
            Path(recompute["vb1"]["workbook_path"]),
            out_root / "vision_assisted_engineering_output.xlsx",
        )

    recompute_ok = bool(recompute.get("success") and shadow_xlsx and Path(shadow_xlsx).exists())
    baseline_bench: Dict[str, Any] = {}
    shadow_bench: Dict[str, Any] = {}
    books: Dict[str, Any] = {}
    comparison: Dict[str, Any] = {}
    if recompute_ok and baseline_excel and estimator.exists():
        _log("  Benchmarking baseline production Excel vs estimator")
        baseline_bench = run_fifth_benchmark(
            engine_root=v10,
            model_excel=Path(baseline_excel),
            estimator_excel=estimator,
            set_output_dir=out_root / "comparison" / "baseline_benchmark",
            label="baseline",
        )
        _log("  Benchmarking Vision-assisted shadow Excel vs estimator")
        shadow_bench = run_fifth_benchmark(
            engine_root=v10,
            model_excel=Path(shadow_xlsx),
            estimator_excel=estimator,
            set_output_dir=out_root / "comparison" / "vision_assisted_benchmark",
            label="vision_assisted",
        )
        books = normalize_workbooks(
            engine_root=v10,
            estimator_excel=estimator,
            baseline_excel=Path(baseline_excel),
            shadow_excel=Path(shadow_xlsx),
        )
        _dump(out_root / "comparison" / "normalized_workbooks_totals.json", {
            k: {kk: vv for kk, vv in rec.items() if kk != "beams"}
            for k, rec in books.items()
        })
        comparison = build_comparison(
            baseline_bench=baseline_bench,
            shadow_bench=shadow_bench,
            books=books,
            overlay_provenance=provenance,
        )
        _dump(out_root / "engineering_comparison.json", comparison)
        _dump(out_root / "comparison" / "engineering_comparison.json", comparison)

    baseline_eng = {
        "label": "BASELINE",
        "excel": baseline_excel,
        "steel_kg": (baseline_bench.get("drawing_summary") or {}).get("model_kg"),
        "production_write": False,
        "source": "FIFTH_SET_PRODUCTION_EXCEL",
    }
    vision_eng = {
        "label": "VISION_ASSISTED_SHADOW",
        "excel": shadow_xlsx,
        "steel_kg": (shadow_bench.get("drawing_summary") or {}).get("model_kg"),
        "production_write": False,
        "source": "P258_SHADOW_VB1",
        "success": recompute_ok,
    }
    _dump(out_root / "baseline_engineering_output.json", baseline_eng)
    _dump(out_root / "vision_assisted_engineering_output.json", vision_eng)

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    fw = firewall_check(v10)

    steel_diff = 0 if before.get("fifth_model_excel", {}).get("sha256") == after.get("fifth_model_excel", {}).get("sha256") else 1
    bbs_diff = 0 if before.get("fifth_bbs_summary", {}).get("sha256") == after.get("fifth_bbs_summary", {}).get("sha256") else 1
    excel_diff = steel_diff
    r13_diff = 0 if before.get("fifth_r13_models", {}).get("sha256") == after.get("fifth_r13_models", {}).get("sha256") else 1
    prod_mut = steel_diff + bbs_diff + r13_diff

    writes_ok = (
        Path(out_root).resolve().as_posix().endswith(OUTPUT_DIRNAME)
        or OUTPUT_DIRNAME in Path(out_root).as_posix()
    )
    unit_ok = bool(unit.get("success"))
    fw_ok = bool(fw.get("ok"))
    reg_ok = bool(fp_cmp.get("unchanged"))
    pass_fail = "PASS" if (unit_ok and fw_ok and reg_ok and writes_ok and prod_mut == 0 and recompute_ok) else (
        "BLOCKED" if not recompute_ok else "FAIL"
    )

    improvement = comparison.get("STEEL_ACCURACY_IMPROVEMENT")
    beam_impact = comparison.get("beam_impact") or {}
    decision_class, recommendation = classify_decision(
        recompute_ok=recompute_ok,
        accuracy_improvement_pp=improvement,
        worsened_beams=int(beam_impact.get("beams_worsened") or 0),
        dangerous_overrides=0,
        production_mutations=prod_mut,
    )
    if pass_fail != "PASS" and decision_class != "BLOCKED":
        # Experiment measured, but a required gate failed.
        if not recompute_ok:
            decision_class, recommendation = classify_decision(
                recompute_ok=False,
                accuracy_improvement_pp=improvement,
                worsened_beams=int(beam_impact.get("beams_worsened") or 0),
                dangerous_overrides=0,
                production_mutations=prod_mut,
            )

    manifest = _p257_manifest(v10)
    summary = {
        "pass_fail": pass_fail,
        "decision": decision_class,
        "recommendation": recommendation,
        "mode": mode,
        "dataset": {
            "drawing_sets": [PRIMARY_DRAWING_SET],
            "dxf_count": manifest.get("dxf_count"),
            "beam_count": manifest.get("number_of_beams") or 143,
            "candidate_count": len(audits),
        },
        "vision": {
            "candidates_available": len(invoked),
            "candidates_eligible": safety.get("eligible_repair_candidates"),
            "fields_promoted": safety.get("promoted_shadow_fields"),
            "fields_blocked": safety.get("blocked_fields"),
        },
        "cost": cost,
        "field_impact": fields,
        "engineering": comparison,
        "stirrup": comparison.get("STIRRUP_ACCURACY") or {},
        "beam_impact": beam_impact,
        "safety": safety,
        "production": {
            "production_mutation_count": prod_mut,
            "production_output_difference": prod_mut,
            "steel_production_difference": steel_diff,
            "bbs_production_difference": bbs_diff,
            "excel_production_difference": excel_diff,
            "r13_production_difference": r13_diff,
        },
        "regression": {
            "unchanged": fp_cmp.get("unchanged"),
            "changed_keys": fp_cmp.get("changed_keys"),
            "p251": "PASS" if "p251_matrix" not in (fp_cmp.get("changed_keys") or []) else "FAIL",
            "p254": "PASS",
            "p255": "PASS",
            "p256": "PASS",
            "p257": "PASS" if "p257_status" not in (fp_cmp.get("changed_keys") or []) else "FAIL",
        },
        "unit_tests": unit,
        "firewall": fw,
        "recompute": {"success": recompute_ok, "error": None if recompute_ok else recompute},
        "output_root": str(out_root),
        "meta": {
            "model_version": MODEL_VERSION,
            "phase_id": PHASE_ID,
            "phase_name": PHASE_NAME,
            "engineering_changes": ENGINEERING_CHANGES,
            "production_write": False,
        },
    }
    if not fp_cmp.get("unchanged"):
        summary["regression"]["p254"] = (
            "FAIL" if any(str(k).startswith("p254") for k in (fp_cmp.get("changed_keys") or [])) else "PASS"
        )
        summary["regression"]["p255"] = (
            "FAIL" if any(str(k).startswith("p255") for k in (fp_cmp.get("changed_keys") or [])) else "PASS"
        )
        summary["regression"]["p256"] = (
            "FAIL" if any(str(k).startswith("p256") for k in (fp_cmp.get("changed_keys") or [])) else "PASS"
        )

    write_reports(out_root=out_root, summary=summary)
    _dump(out_root / "evaluation" / "regression.json", fp_cmp)
    _log(f"  promoted={len(promoted)} blocked={safety.get('blocked_fields')}")
    _log(
        f"  baseline_acc={comparison.get('baseline_accuracy')} "
        f"vision_acc={comparison.get('vision_assisted_accuracy')} "
        f"improvement={comparison.get('STEEL_ACCURACY_IMPROVEMENT')}"
    )
    _log(f"  decision={decision_class} status={pass_fail}")
    return summary


__all__ = ["run_phase_p258"]
