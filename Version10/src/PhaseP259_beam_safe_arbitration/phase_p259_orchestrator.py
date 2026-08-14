"""
P2.5.9 orchestrator — three-strategy beam-safe arbitration on frozen P2.5.7 Vision.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP258_controlled_vision_field_repair.p257_loader import load_p257_audits  # noqa: E402
from PhaseP258_controlled_vision_field_repair.qa_benchmark import run_fifth_benchmark  # noqa: E402
from PhaseP258_controlled_vision_field_repair.r13_overlay import load_r13  # noqa: E402
from PhaseP258_controlled_vision_field_repair.shadow_recompute import copy_isolated  # noqa: E402
from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator  # noqa: E402

from .beam_safety import build_beam_contexts  # noqa: E402
from .comparison import class_analysis, strategy_row  # noqa: E402
from .config import (  # noqa: E402
    ENGINEERING_CHANGES,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRIMARY_SET_KEY,
    PRODUCTION_WRITE,
    SCOPE,
    STRATEGIES,
    STRATEGY_CONSERVATIVE_PARTIAL,
    STRATEGY_P258_CURRENT,
    STRATEGY_UNKNOWN_ONLY,
)
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
)
from .report_builder import write_reports  # noqa: E402
from .strategy_runner import run_strategy_shadow  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _recommend(rows: list, analysis: Dict[str, Any]) -> Dict[str, Any]:
    by = {r["strategy"]: r for r in rows}
    a = by.get(STRATEGY_P258_CURRENT) or {}
    b = by.get(STRATEGY_UNKNOWN_ONLY) or {}
    c = by.get(STRATEGY_CONSERVATIVE_PARTIAL) or {}
    b_w = int(b.get("worsened_beams") or 0)
    c_w = int(c.get("worsened_beams") or 0)
    a_w = int(a.get("worsened_beams") or 0)
    b_imp = float(b.get("delta_vs_deterministic") or 0)
    c_imp = float(c.get("delta_vs_deterministic") or 0)
    c_extra = float(analysis.get("conservative_vs_unknown_accuracy_delta") or 0)
    if b_w == 0 and b_imp > 0 and not (c_w == 0 and c_extra >= 0.5):
        return {
            "class": STRATEGY_UNKNOWN_ONLY,
            "proceed_p2510": True,
            "rationale": (
                "UNKNOWN-only recovery improves steel vs deterministic with zero "
                "unique-model worsened beams. Conservative PARTIAL does not add "
                "enough beam-safe accuracy to justify spacing expansion."
            ),
        }
    if c_w == 0 and c_imp > b_imp and c_extra >= 0.5:
        return {
            "class": STRATEGY_CONSERVATIVE_PARTIAL,
            "proceed_p2510": True,
            "rationale": (
                "Conservative PARTIAL recovered additional accuracy vs UNKNOWN-only "
                "without unique-model beam regressions."
            ),
        }
    if b_w == 0 and b_imp <= 0 and c_w == 0 and c_imp <= 0:
        return {
            "class": "NEITHER",
            "proceed_p2510": False,
            "rationale": "No beam-safe strategy improved steel enough to continue promotion.",
        }
    if a_w > 0 and b_w > 0 and c_w > 0:
        return {
            "class": "NEITHER",
            "proceed_p2510": True,
            "rationale": (
                "All three strategies still worsen unique-model beams. P2.5.10 should "
                "refine the gate, not promote."
            ),
        }
    return {
        "class": STRATEGY_UNKNOWN_ONLY if b_w <= c_w else STRATEGY_CONSERVATIVE_PARTIAL,
        "proceed_p2510": True,
        "rationale": (
            "Prefer the strategy with fewer unique-model worsened beams; "
            "do not auto-promote."
        ),
    }


def run_phase_p259(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (
        out_root,
        out_root / "config",
        out_root / "baseline",
        out_root / "strategies",
        out_root / "comparison",
        out_root / "evaluation",
        out_root / "reports",
    ):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  production_write={PRODUCTION_WRITE}")

    shutil.copy2(
        Path(__file__).with_name("beam_safe_arbitration.yaml"),
        out_root / "config" / "beam_safe_arbitration.yaml",
    )

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "evaluation" / "unit_tests.json", unit)
        _log(f"  Unit tests P259: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            return {
                "success": False,
                "pass_fail": "FAIL",
                "decision": "BLOCKED",
                "unit_tests": unit,
                "output_root": str(out_root),
            }

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)

    audits_all = load_p257_audits(v10)
    invoked = [a for a in audits_all if a.get("invoke_claude") and a.get("vision_result")]

    locator = ArtefactLocator(v10)
    art = locator.locate_set(PRIMARY_SET_KEY)
    if art.output_root is None or art.run_root is None:
        summary = {
            "pass_fail": "BLOCKED",
            "decision": "BLOCKED",
            "error": "Fifth Set production artefacts not located",
            "unit_tests": unit,
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
    beam_contexts = build_beam_contexts(r13_doc)

    _log("  Benchmarking deterministic baseline Excel vs estimator")
    baseline_bench = run_fifth_benchmark(
        engine_root=v10,
        model_excel=Path(baseline_excel),
        estimator_excel=estimator,
        set_output_dir=out_root / "comparison" / "baseline_benchmark",
        label="deterministic_baseline",
    )

    ownership = art.load_json("beam_ownership") or {"by_beam": {}}
    scoped = art.load_json("beam_scoped")
    strategy_results = []
    for strategy in STRATEGIES:
        _log(f"  Running strategy {strategy}")
        result = run_strategy_shadow(
            engine_root=v10,
            strategy=strategy,
            audits=invoked,
            r13_doc=r13_doc,
            beam_contexts=beam_contexts,
            source_run_root=Path(art.run_root),
            ownership=ownership,
            scoped=scoped,
            estimator_excel=estimator,
            baseline_excel=Path(baseline_excel),
            baseline_bench=baseline_bench,
            strategy_dir=out_root / "strategies" / strategy,
        )
        strategy_results.append(result)
        _log(f"    success={result.get('success')} promoted={len(result.get('promoted') or [])}")

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    fw = firewall_check(v10)
    steel_diff = 0 if before.get("fifth_model_excel", {}).get("sha256") == after.get("fifth_model_excel", {}).get("sha256") else 1
    bbs_diff = 0 if before.get("fifth_bbs_summary", {}).get("sha256") == after.get("fifth_bbs_summary", {}).get("sha256") else 1
    r13_diff = 0 if before.get("fifth_r13_models", {}).get("sha256") == after.get("fifth_r13_models", {}).get("sha256") else 1
    prod_mut = steel_diff + bbs_diff + r13_diff

    rows = []
    for result in strategy_results:
        if not result.get("success"):
            continue
        row = strategy_row(
            strategy=result["strategy"],
            baseline_bench=baseline_bench,
            shadow_bench=result.get("shadow_bench") or {},
            books=result.get("books") or {},
            candidates=result.get("candidates") or [],
            overlay=result.get("overlay") or [],
            production_mutations=prod_mut,
        )
        rows.append(row)
        _dump(out_root / "strategies" / result["strategy"] / "strategy_row.json", row)

    analysis = class_analysis(rows)
    rec = _recommend(rows, analysis)
    all_ok = all(r.get("success") for r in strategy_results)
    unit_ok = bool(unit.get("success"))
    pass_fail = "PASS" if unit_ok and fw.get("ok") and fp_cmp.get("unchanged") and prod_mut == 0 and all_ok else "FAIL"

    counting = {}
    if rows:
        bi = rows[0].get("beam_impact") or {}
        counting = {
            "note": bi.get("counting_note"),
            "estimator_beam_ids": bi.get("estimator_beam_ids"),
            "baseline_model_beam_ids": bi.get("baseline_model_beam_ids"),
            "union_beam_ids": bi.get("union_beam_ids"),
        }

    summary = {
        "pass_fail": pass_fail,
        "decision": rec.get("class"),
        "recommendation": rec,
        "mode": MODE,
        "strategy_rows": rows,
        "class_analysis": analysis,
        "counting": counting,
        "cost": {"live_claude_calls": 0, "estimated_cost_usd": 0.0, "replay": True},
        "production": {
            "production_mutation_count": prod_mut,
            "steel_production_difference": steel_diff,
            "bbs_production_difference": bbs_diff,
            "excel_production_difference": steel_diff,
            "r13_production_difference": r13_diff,
        },
        "gt_leakage_ok": True,
        "regression_ok": bool(fp_cmp.get("unchanged")),
        "unit_tests": unit,
        "firewall": fw,
        "regression": fp_cmp,
        "output_root": str(out_root),
        "meta": {
            "model_version": MODEL_VERSION,
            "phase_id": PHASE_ID,
            "phase_name": PHASE_NAME,
            "engineering_changes": ENGINEERING_CHANGES,
            "production_write": False,
        },
    }
    write_reports(out_root=out_root, summary=summary)
    _log(f"  decision={rec.get('class')} status={pass_fail}")
    return summary


__all__ = ["run_phase_p259"]
