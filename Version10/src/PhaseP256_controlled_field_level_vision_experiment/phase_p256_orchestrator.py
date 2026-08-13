"""
P2.5.6 orchestrator — Controlled Field-Level Vision Experiment.

Reuses P2.5.5 deterministic snapshot + Vision observer.
Does not rebuild P2.5.4. Does not overwrite P2.5.5 artefacts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP255_controlled_shadow_integration.deterministic_snapshot import (  # noqa: E402
    capture_deterministic,
)
from PhaseP255_controlled_shadow_integration.frozen_loader import (  # noqa: E402
    load_frozen_benchmark,
    load_frozen_p251_index,
)
from PhaseP255_controlled_shadow_integration.vision_observer import observe_vision  # noqa: E402

from .config import (  # noqa: E402
    ENGINEERING_CHANGES,
    FROZEN_BENCHMARK_COUNT,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    SCOPE,
    VISION_SOURCE_LIVE,
    VISION_SOURCE_REPLAY,
)
from .integrator import evaluate_one  # noqa: E402
from .metrics import compute_metrics  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    fourth_set_production_paths,
)
from .report_builder import write_reports  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _case_ok(rows: List[Dict[str, Any]], cid: str, *, must_conflict: List[str], must_accept: List[str]) -> bool:
    for r in rows:
        fr = r.get("field_result") or {}
        if fr.get("candidate_id") != cid:
            continue
        conflicts = set(fr.get("conflict_fields") or [])
        accepted = set(fr.get("accepted_shadow_fields") or [])
        if any(f not in conflicts for f in must_conflict):
            return False
        if any(f not in accepted for f in must_accept):
            return False
        if fr.get("production_write") is not False:
            return False
        if "zone" in accepted:
            return False
        return True
    return False


def run_phase_p256(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    live: bool = False,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    baseline_root = out_root / "baseline"
    shadow_root = out_root / "shadow"
    for d in (out_root, baseline_root, shadow_root, out_root / "evaluation", out_root / "reports"):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {MODE}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  vision: {'LIVE' if live else 'REPLAY_P254_FROZEN'}")
    _log(f"  output: {out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "evaluation" / "unit_tests.json", unit)
        _log(f"  Unit tests P256: {unit['passed']}/{unit['total']}")
        p255u = unit.get("p255_unit_tests") or {}
        p254u = unit.get("p254_unit_tests") or {}
        _log(f"  Unit tests P255: {p255u.get('passed')}/{p255u.get('total')}")
        _log(f"  Unit tests P254: {p254u.get('passed')}/{p254u.get('total')}")
        if not unit.get("success"):
            return {
                "success": False,
                "pass_fail": "FAIL",
                "decision": "BLOCKED",
                "unit_tests": unit,
                "output_root": str(out_root),
            }

    try:
        prod_paths = fourth_set_production_paths(v10)
    except Exception as exc:  # noqa: BLE001
        _log(f"  Production path locate warning: {exc}")
        prod_paths = {}
    fp_paths = fingerprint_paths(v10, prod_paths)
    fp_before = capture_fingerprints(fp_paths)
    fw = firewall_check(v10)

    candidates, gt_map = load_frozen_benchmark(v10)
    p251_index = load_frozen_p251_index(v10)
    if len(candidates) != FROZEN_BENCHMARK_COUNT:
        return {
            "success": False,
            "pass_fail": "FAIL",
            "decision": "BLOCKED",
            "error": "frozen_benchmark_size_changed",
            "output_root": str(out_root),
        }

    _dump(
        baseline_root / "benchmark_manifest_fingerprint.json",
        {
            "source": "P254_FROZEN",
            "count": len(candidates),
            "note": "P2.5.4/P2.5.5 artefacts are not rewritten.",
            "candidate_ids": [c.get("candidate_id") for c in candidates],
        },
    )

    rows: List[Dict[str, Any]] = []
    mismatches: List[str] = []
    vision_source = VISION_SOURCE_LIVE if live else VISION_SOURCE_REPLAY

    for c in candidates:
        cid = c["candidate_id"]
        frozen_intent = p251_index.get((c["beam_id"], c["annotation_id"]))
        det = capture_deterministic(
            version10_root=v10,
            beam_id=c["beam_id"],
            annotation_id=c["annotation_id"],
            frozen_intent=frozen_intent,
        )
        if frozen_intent is not None and det.get("matches_frozen_matrix") is False:
            mismatches.append(cid)
            _log(f"  STOP: deterministic snapshot mismatch {cid}")
            break
        cand_dir = cid.replace("::", "__")
        _dump(baseline_root / "candidates" / cand_dir / "deterministic_snapshot.json", det)
        _log(f"  Fields: {cid} ({c.get('raw_text')})")
        vision_obs = observe_vision(candidate=c, version10_root=v10, live=live)
        integrated = evaluate_one(
            candidate=c,
            deterministic=det,
            vision_obs=vision_obs,
            ground_truth=gt_map.get(cid),
        )
        _dump(shadow_root / "candidates" / cand_dir / "field_level_result.json", integrated["field_result"])
        rows.append(integrated)
        fr = integrated["field_result"]
        _log(
            f"    -> accept={fr.get('accepted_shadow_fields')} "
            f"reject={fr.get('rejected_shadow_fields')} "
            f"conflict={fr.get('conflict_fields')} "
            f"dec={fr.get('final_shadow_decision')}"
        )

    if mismatches:
        return {
            "success": False,
            "pass_fail": "FAIL",
            "decision": "BLOCKED",
            "error": "deterministic_baseline_changed",
            "mismatches": mismatches,
            "output_root": str(out_root),
            "unit_tests": unit,
            "firewall": fw,
        }

    fp_after = capture_fingerprints(fp_paths)
    reg = compare_fingerprints(fp_before, fp_after)
    metrics = compute_metrics(rows)
    usage = metrics.get("token_usage") or {}
    est_cost = round(
        (float(usage.get("input_tokens") or 0) / 1_000_000.0) * 3.0
        + (float(usage.get("output_tokens") or 0) / 1_000_000.0) * 15.0,
        4,
    )

    b46_ok = _case_ok(
        rows, "VC::B46::ANN-a09ab748",
        must_conflict=[],
        must_accept=["diameter", "legs", "spacing"],
    )
    b58_ok = _case_ok(
        rows, "VC::B58::ANN-a0c82bbe",
        must_conflict=["semantic_type", "reinforcement_role"],
        must_accept=[],
    )
    b120_ok = _case_ok(
        rows, "VC::B120::ANN-f4213b73",
        must_conflict=["spacing"],
        must_accept=[],
    )
    zone_ok = all(
        "zone" not in ((r.get("field_result") or {}).get("accepted_shadow_fields") or [])
        and (r.get("field_result") or {}).get("zone_promotable") is False
        for r in rows
    )
    writes_ok = all((r.get("field_result") or {}).get("production_write") is False for r in rows)

    changed = reg.get("changed_keys") or []
    p254_ok = not any(str(k).startswith("p254") for k in changed)
    p255_ok = not any(str(k).startswith("p255") for k in changed)
    p251_ok = not any(str(k).startswith("p251") for k in changed)
    prod_keys = [
        k
        for k in changed
        if str(k).startswith("production") or str(k) in ("physical_bars", "r13_models", "estimator_excel")
    ]

    hard_fail = (
        not unit.get("success")
        or not fw.get("ok")
        or not reg.get("unchanged", False)
        or not b46_ok
        or not b58_ok
        or not b120_ok
        or not zone_ok
        or not writes_ok
        or len(rows) != FROZEN_BENCHMARK_COUNT
        or bool(mismatches)
    )
    pass_fail = "FAIL" if hard_fail else "PASS"
    decision = "READY_FOR_NEXT_CONTROLLED_EXPERIMENT" if pass_fail == "PASS" else "BLOCKED"

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "pass_fail": pass_fail,
        "decision": decision,
        "vision_source": vision_source,
        "candidate_count": len(rows),
        "metrics": metrics,
        "regression": {
            "unchanged": reg.get("unchanged"),
            "changed_keys": changed,
            "p254_unchanged": p254_ok,
            "p255_unchanged": p255_ok,
            "p251_unchanged": p251_ok,
        },
        "firewall": fw,
        "engineering_changes": ENGINEERING_CHANGES,
        "production_output_changes": "NONE" if not prod_keys else str(prod_keys),
        "estimated_api_cost_usd": est_cost,
        "estimated_cost_note": (
            "Approx Claude Sonnet list rates $3/MTok in + $15/MTok out; "
            "replay uses frozen P2.5.4 token usage (no new live spend unless --live)."
        ),
        "unit_tests": unit,
        "b46_ok": b46_ok,
        "b58_ok": b58_ok,
        "b120_ok": b120_ok,
        "zone_ok": zone_ok,
    }
    write_reports(out_root=out_root, summary=summary, rows=rows)
    _dump(
        out_root / "evaluation" / "regression.json",
        {"compare": {"unchanged": reg.get("unchanged"), "changed_keys": changed}},
    )
    _log(f"  PASS/FAIL: {pass_fail}")
    _log(f"  Decision: {decision}")
    _log(f"  B46/B58/B120: {b46_ok}/{b58_ok}/{b120_ok}")
    return {
        "success": pass_fail == "PASS",
        "pass_fail": pass_fail,
        "decision": decision,
        "output_root": str(out_root),
        "metrics": metrics,
        "regression": summary["regression"],
        "firewall": fw,
        "unit_tests": unit,
        "b46_ok": b46_ok,
        "b58_ok": b58_ok,
        "b120_ok": b120_ok,
        "candidate_count": len(rows),
        "vision_source": vision_source,
        "estimated_api_cost_usd": est_cost,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
    }


__all__ = ["run_phase_p256"]
