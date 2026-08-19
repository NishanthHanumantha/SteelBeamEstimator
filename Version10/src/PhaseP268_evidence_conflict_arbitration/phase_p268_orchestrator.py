"""P2.6.8 orchestrator. Shadow diagnostic. Does not change production routing."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional

from .arbitration import arbitrate
from .config import (
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MODE_LIVE,
    MODE_OFFLINE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
    SCOPE,
    TARGET_BEAMS,
)
from .dataset import load_p266_targets, load_p267_live_index
from .evidence import build_evidence_record
from .evaluator import classify_phase, evaluate_controls, production_invariants
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .report import write_reports
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_phase_p268(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_OFFLINE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (out_root, out_root / "reports"):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode == MODE_LIVE:
        raise RuntimeError(
            "P2.6.8 default is OFFLINE_ARBITRATION. LIVE_CLASSIFY is not enabled in this phase "
            "because P2.6.7 already showed unconstrained live DISTINCT/DUPLICATE is unsafe. "
            "Refusing to silently convert to a new live recovery strategy."
        )
    if mode != MODE_OFFLINE:
        raise RuntimeError(f"unsupported P2.6.8 mode {mode!r}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {mode}")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.8 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.8 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.8 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    targets = load_p266_targets(v10)
    live_idx = load_p267_live_index(v10)
    _log(f"  loaded P2.6.6 targets: {len(targets)} (expected {TARGET_BEAMS})")
    _log(f"  loaded P2.6.7 live index: {len(live_idx)}")

    records = []
    for i, target in enumerate(targets, start=1):
        set_key = str(target.get("set_key") or "")
        beam_id = str(target.get("beam_id") or "")
        live = live_idx.get((set_key, beam_id))
        evidence = build_evidence_record(target, live=live)
        decision = arbitrate(evidence)
        records.append(decision)
        _log(
            f"  [{i}/{len(targets)}] {set_key}/{beam_id} "
            f"conflict={decision.get('conflict_type')} arb={decision.get('arbitration_result')}"
        )

    inv = production_invariants(records)
    controls = evaluate_controls(records)
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "p264_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p265_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p266_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p267_artefacts_unchanged": fp_cmp.get("unchanged"),
        "all_shadow_only": inv.get("all_shadow_only"),
        "all_no_change": inv.get("all_no_change"),
        "engineering_changes": ENGINEERING_CHANGES,
        "steel_quantity_delta": 0,
        "bbs_delta": 0,
        "workbook_delta": 0,
        "live_vision_invoked": False,
    }
    recommendation = classify_phase(
        controls=controls,
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        production_mutation=int(production["production_mutation_count"]),
        tests_ok=bool(unit.get("success")),
        all_shadow=bool(inv.get("all_shadow_only")),
        all_no_change=bool(inv.get("all_no_change")),
    )
    metrics = {
        "target_beams": len(targets),
        "conflict_distribution": dict(Counter(r.get("conflict_type") for r in records)),
        "arbitration_distribution": dict(Counter(r.get("arbitration_result") for r in records)),
        "controls": controls,
        "production_invariants": inv,
        "LIVE_VISION_CALLS": 0,
    }
    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "gate_version": GATE_VERSION,
        "scope": SCOPE,
        "mode": mode,
        "production_write": PRODUCTION_WRITE,
        "engineering_changes": ENGINEERING_CHANGES,
        "pass_fail": (
            "PASS"
            if unit.get("success")
            and fw.get("ok")
            and leak.get("ok")
            and fp_cmp.get("unchanged")
            and inv.get("all_shadow_only")
            and inv.get("all_no_change")
            else "FAIL"
        ),
        "output_root": str(out_root),
        "metrics": metrics,
        "recommendation": recommendation,
        "records": records,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "decision": recommendation.get("decision"),
        "strength": recommendation.get("strength"),
        "live_vision_invoked": False,
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    dump = dict(result)
    dump.pop("records", None)
    _dump(out_root / "result.json", dump)
    _dump(out_root / "fingerprints_after.json", after)
    _log(f"  decision={result.get('decision')} strength={result.get('strength')}")
    return result


__all__ = ["run_phase_p268"]
