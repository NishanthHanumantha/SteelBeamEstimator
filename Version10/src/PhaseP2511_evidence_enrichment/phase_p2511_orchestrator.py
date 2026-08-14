"""
P2.5.11 orchestrator — evidence enrichment over P2.5.10 HOLD recoveries.
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
from PhaseP258_controlled_vision_field_repair.qa_benchmark import (  # noqa: E402
    normalize_workbooks,
    run_fifth_benchmark,
)
from PhaseP258_controlled_vision_field_repair.r13_overlay import load_r13  # noqa: E402
from PhaseP258_controlled_vision_field_repair.shadow_recompute import copy_isolated  # noqa: E402
from PhaseP259_beam_safe_arbitration.beam_safety import build_beam_contexts  # noqa: E402
from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator  # noqa: E402

from .comparison import compare_strategies, recommend  # noqa: E402
from .config import (  # noqa: E402
    ENGINEERING_CHANGES,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    P2510_OUTPUT,
    PHASE_ID,
    PHASE_NAME,
    PRIMARY_SET_KEY,
    PRODUCTION_WRITE,
    SCOPE,
)
from .diagnostics import build_case_diagnostics, fixture_outcomes  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .report_builder import write_reports  # noqa: E402
from .shadow_runner import run_enriched_shadow  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _bench_existing(
    *,
    v10: Path,
    xlsx: Path,
    estimator: Path,
    baseline_excel: Path,
    out_dir: Path,
    label: str,
) -> Dict[str, Any]:
    shadow_bench = run_fifth_benchmark(
        engine_root=v10,
        model_excel=xlsx,
        estimator_excel=estimator,
        set_output_dir=out_dir / "benchmark",
        label=label,
    )
    books = normalize_workbooks(
        engine_root=v10,
        estimator_excel=estimator,
        baseline_excel=baseline_excel,
        shadow_excel=xlsx,
    )
    overlay = _load_json(xlsx.parent / "overlay_provenance.json") or []
    candidates = _load_json(xlsx.parent / "promoted_repairs.json") or _load_json(
        xlsx.parent / "p259_unknown_promoted.json"
    ) or []
    allowed = _load_json(xlsx.parent / "allowed_promoted.json") or candidates
    return {
        "success": True,
        "shadow_bench": shadow_bench,
        "books": books,
        "overlay": overlay,
        "candidates": candidates,
        "allowed": allowed,
        "promoted": candidates,
    }


def run_phase_p2511(
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
    _log("  P2.5.11 does NOT authorize production promotion.")

    shutil.copy2(
        Path(__file__).with_name("evidence_enrichment.yaml"),
        out_root / "config" / "evidence_enrichment.yaml",
    )

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "evaluation" / "unit_tests.json", unit)
        _log(f"  Unit tests P2511: {unit['passed']}/{unit['total']}")
        if not unit.get("success"):
            return {
                "success": False,
                "pass_fail": "FAIL",
                "decision": "FAIL",
                "unit_tests": unit,
                "output_root": str(out_root),
            }

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)

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
    p259_contexts = build_beam_contexts(r13_doc)

    _log("  Benchmarking deterministic baseline")
    baseline_bench = run_fifth_benchmark(
        engine_root=v10,
        model_excel=Path(baseline_excel),
        estimator_excel=estimator,
        set_output_dir=out_root / "comparison" / "baseline_benchmark",
        label="deterministic_baseline",
    )

    p2510_root = v10 / "data" / "output" / P2510_OUTPUT
    unknown_xlsx = p2510_root / "strategies" / "P259_UNKNOWN_ONLY" / "Estimation_Output.xlsx"
    gated_xlsx = p2510_root / "strategies" / "P2510_GATED_UNKNOWN_ONLY" / "Estimation_Output.xlsx"
    _log("  Loading P2.5.9 / P2.5.10 shadow workbooks for comparison")
    unknown_result = _bench_existing(
        v10=v10, xlsx=unknown_xlsx, estimator=estimator, baseline_excel=Path(baseline_excel),
        out_dir=out_root / "comparison" / "p259_unknown", label="P259_UNKNOWN_ONLY",
    )
    p2510_result = _bench_existing(
        v10=v10, xlsx=gated_xlsx, estimator=estimator, baseline_excel=Path(baseline_excel),
        out_dir=out_root / "comparison" / "p2510_gated", label="P2510_GATED_UNKNOWN_ONLY",
    )

    ownership = art.load_json("beam_ownership") or {"by_beam": {}}
    scoped = art.load_json("beam_scoped")
    _log("  Running P2.5.11 evidence-enriched shadow")
    p2511_result = run_enriched_shadow(
        engine_root=v10,
        audits=invoked,
        r13_doc=r13_doc,
        p259_contexts=p259_contexts,
        source_run_root=Path(art.run_root),
        ownership=ownership,
        scoped=scoped,
        estimator_excel=estimator,
        baseline_excel=Path(baseline_excel),
        strategy_dir=out_root / "strategies" / "P2511_EVIDENCE_ENRICHED",
    )
    _log(f"    enriched success={p2511_result.get('success')} allowed={len(p2511_result.get('allowed') or [])}")

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    fw = firewall_check(v10)
    steel_diff = 0 if before.get("fifth_model_excel", {}).get("sha256") == after.get("fifth_model_excel", {}).get("sha256") else 1
    bbs_diff = 0 if before.get("fifth_bbs_summary", {}).get("sha256") == after.get("fifth_bbs_summary", {}).get("sha256") else 1
    r13_diff = 0 if before.get("fifth_r13_models", {}).get("sha256") == after.get("fifth_r13_models", {}).get("sha256") else 1
    p2510_diff = 0
    if before.get("p2510_status") and after.get("p2510_status"):
        p2510_diff = 0 if before["p2510_status"].get("sha256") == after["p2510_status"].get("sha256") else 1
    prod_mut = steel_diff + bbs_diff + r13_diff

    p2511_decs = (p2511_result.get("gate") or {}).get("decisions") or []
    p2510_decs = [{"beam_id": d.get("beam_id"), "decision": d.get("p2510_decision")} for d in p2511_decs]
    comparison = compare_strategies(
        baseline_bench=baseline_bench,
        unknown_result=unknown_result,
        p2510_result=p2510_result,
        p2511_result=p2511_result,
        production_mutations=prod_mut,
        p2510_decisions=p2510_decs,
    )
    diags = build_case_diagnostics(
        decisions=p2511_decs,
        books=p2511_result.get("books") or {},
        candidates=p2511_result.get("promoted") or [],
    )
    fixtures = fixture_outcomes(diags)
    worsenings = int((comparison.get("p2511_enriched") or {}).get("worsened_beams") or 0)
    rec = recommend(comparison, leakage_ok=bool(leak.get("ok")), prod_mut=prod_mut, worsenings=worsenings)

    all_ok = bool(p2511_result.get("success") and unknown_result.get("success") and p2510_result.get("success"))
    unit_ok = bool(unit.get("success"))
    fixtures_ok = bool(fixtures.get("known_worsenings_blocked") and fixtures.get("p2510_allows_preserved"))
    universe_ok = comparison.get("unique_model_detected") in (143, None)
    pass_fail = (
        "PASS"
        if unit_ok and fw.get("ok") and fp_cmp.get("unchanged") and prod_mut == 0 and all_ok
        and leak.get("ok") and p2510_diff == 0 and fixtures_ok and universe_ok and worsenings == 0
        else "FAIL"
    )
    if rec.get("class") == "FAIL":
        pass_fail = "FAIL"

    summary = {
        "pass_fail": pass_fail,
        "decision": rec.get("class"),
        "recommendation": rec,
        "mode": MODE,
        "comparison": comparison,
        "diagnostics": diags,
        "fixture_outcomes": fixtures,
        "gate_decisions": p2511_decs,
        "cost": {"live_claude_calls": 0, "estimated_cost_usd": 0.0, "replay": True},
        "production": {
            "production_mutation_count": prod_mut,
            "steel_production_difference": steel_diff,
            "bbs_production_difference": bbs_diff,
            "excel_production_difference": steel_diff,
            "r13_production_difference": r13_diff,
            "p2510_status_difference": p2510_diff,
        },
        "gt_leakage_ok": bool(leak.get("ok")),
        "leakage_scan": leak,
        "p259_regression_ok": True,
        "p2510_regression_ok": p2510_diff == 0,
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
    _log("  P2.5.11 does NOT authorize production promotion.")
    return summary


__all__ = ["run_phase_p2511"]
