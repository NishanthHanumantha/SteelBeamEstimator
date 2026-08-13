"""
P2.5.5 orchestrator — Controlled Shadow Integration.

Deterministic P2.5.1 is captured first and treated as immutable.
Claude Vision is a shadow observer. No production writes.
The P2.5.4 41-candidate benchmark is loaded frozen — never rebuilt.
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

from .config import (  # noqa: E402
    DEFAULT_ELIGIBILITY,
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
from .deterministic_snapshot import capture_deterministic  # noqa: E402
from .frozen_loader import load_frozen_benchmark, load_frozen_p251_index  # noqa: E402
from .integrator import integrate_one  # noqa: E402
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
from .vision_observer import observe_vision  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def run_phase_p255(
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
        _log(f"  Unit tests P255: {unit['passed']}/{unit['total']}")
        p254u = unit.get("p254_unit_tests") or {}
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

    _dump(baseline_root / "benchmark_manifest_fingerprint.json", {
        "source": "P254_FROZEN",
        "count": len(candidates),
        "note": "Manifest copied by reference only; P2.5.4 files are not rewritten.",
        "candidate_ids": [c.get("candidate_id") for c in candidates],
    })

    rows: List[Dict[str, Any]] = []
    mismatches: List[str] = []
    vision_source = VISION_SOURCE_LIVE if live else VISION_SOURCE_REPLAY

    for c in candidates:
        cid = c["candidate_id"]
        beam_id = c["beam_id"]
        ann_id = c["annotation_id"]
        frozen_intent = p251_index.get((beam_id, ann_id))
        det = capture_deterministic(
            version10_root=v10,
            beam_id=beam_id,
            annotation_id=ann_id,
            frozen_intent=frozen_intent,
        )
        if frozen_intent is not None and det.get("matches_frozen_matrix") is False:
            mismatches.append(cid)
            _log(f"  STOP: deterministic snapshot mismatch {cid}")
            break

        cand_dir = cid.replace("::", "__")
        _dump(baseline_root / "candidates" / cand_dir / "deterministic_snapshot.json", det)

        _log(f"  Shadow: {cid} ({c.get('raw_text')}) det={det.get('deterministic_type')}/{det.get('deterministic_status')}")
        vision_obs = observe_vision(candidate=c, version10_root=v10, live=live)
        integrated = integrate_one(
            candidate=c,
            deterministic=det,
            vision_obs=vision_obs,
            ground_truth=gt_map.get(cid),
            eligibility_mode=DEFAULT_ELIGIBILITY,
        )
        _dump(shadow_root / "candidates" / cand_dir / "shadow_result.json", integrated["shadow"])
        _dump(
            shadow_root / "candidates" / cand_dir / "vision_observer.json",
            {
                "vision_source": vision_obs.get("vision_source"),
                "api_ok": vision_obs.get("api_ok"),
                "validation": vision_obs.get("validation"),
                "usage": vision_obs.get("usage"),
                "model": vision_obs.get("model"),
                "temperature": vision_obs.get("temperature"),
                "evidence_fingerprint": vision_obs.get("evidence_fingerprint"),
                "prompt_fingerprint": vision_obs.get("prompt_fingerprint"),
                "live_call": vision_obs.get("live_call"),
            },
        )
        rows.append(integrated)
        _log(
            f"    -> op={integrated.get('operational_class')} "
            f"cmp={integrated.get('comparison_class')} "
            f"act={integrated.get('arbitration_action')} "
            f"conflicts={integrated.get('conflict_fields')}"
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

    b58 = next(
        (
            r
            for r in rows
            if (r.get("shadow") or {}).get("candidate_id") == "VC::B58::ANN-a0c82bbe"
        ),
        None,
    )
    b58_ok = False
    if b58:
        sh = b58["shadow"]
        b58_ok = (
            sh.get("deterministic_type") == "STIRRUP"
            and sh.get("deterministic_role") == "STIRRUP"
            and sh.get("production_write") is False
            and sh.get("operational_class") == "VISION_CONFLICT"
            and sh.get("comparison_class") == "VISION_WRONG"
            and sh.get("arbitration_action") == "KEEP_DETERMINISTIC_FLAG_VISION_ERROR"
        )

    known_conflicts = []
    for r in rows:
        sh = r.get("shadow") or {}
        if sh.get("operational_class") == "VISION_CONFLICT" or sh.get("comparison_class") == "VISION_WRONG":
            known_conflicts.append(
                f"- {sh.get('candidate_id')} text=`{sh.get('annotation_text')}` "
                f"det={sh.get('deterministic_type')}/{sh.get('deterministic_role')} "
                f"vis={sh.get('vision_type')}/{sh.get('vision_role')} "
                f"op={sh.get('operational_class')} cmp={sh.get('comparison_class')} "
                f"fields={sh.get('conflict_flags')}"
            )
    if not known_conflicts:
        known_conflicts = ["- none"]

    p254_keys = [k for k in (reg.get("changed_keys") or []) if str(k).startswith("p254")]
    p251_keys = [k for k in (reg.get("changed_keys") or []) if str(k).startswith("p251")]
    prod_keys = [
        k
        for k in (reg.get("changed_keys") or [])
        if str(k).startswith("production") or str(k) in ("physical_bars", "r13_models", "estimator_excel")
    ]

    hard_fail = (
        not unit.get("success")
        or not fw.get("ok")
        or not reg.get("unchanged", False)
        or not b58_ok
        or len(rows) != FROZEN_BENCHMARK_COUNT
        or bool(mismatches)
    )
    pass_fail = "FAIL" if hard_fail else "PASS"
    if pass_fail == "PASS":
        decision = "READY_FOR_CONTROLLED_NEXT_EXPERIMENT"
    else:
        decision = "BLOCKED"

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
            "changed_keys": reg.get("changed_keys"),
            "p254_unchanged": len(p254_keys) == 0,
            "p251_unchanged": len(p251_keys) == 0,
        },
        "regression_status": "PASS" if reg.get("unchanged") else "FAIL",
        "firewall": fw,
        "engineering_changes": ENGINEERING_CHANGES,
        "production_output_changes": "NONE" if not prod_keys else str(prod_keys),
        "estimated_api_cost_usd": est_cost,
        "estimated_cost_note": (
            "Approx Claude Sonnet list rates $3/MTok in + $15/MTok out; "
            "replay uses frozen P2.5.4 token usage (no new live spend unless --live)."
        ),
        "unit_tests": unit,
        "b58_ok": b58_ok,
        "known_conflicts": known_conflicts,
        "claude_model": next(
            ((r.get("vision_obs") or {}).get("model") for r in rows if (r.get("vision_obs") or {}).get("model")),
            "claude-sonnet-4-5",
        ),
        "temperature": next(
            (
                (r.get("vision_obs") or {}).get("temperature")
                for r in rows
                if (r.get("vision_obs") or {}).get("temperature") is not None
            ),
            0,
        ),
    }
    write_reports(out_root=out_root, summary=summary, rows=rows)
    _dump(out_root / "evaluation" / "regression.json", {"before": fp_before, "after": fp_after, "compare": {
        "unchanged": reg.get("unchanged"),
        "changed_keys": reg.get("changed_keys"),
    }})

    _log(f"  PASS/FAIL: {pass_fail}")
    _log(f"  Decision: {decision}")
    _log(f"  B58 protection: {b58_ok}")
    return {
        "success": pass_fail == "PASS",
        "pass_fail": pass_fail,
        "decision": decision,
        "output_root": str(out_root),
        "metrics": metrics,
        "regression": summary["regression"],
        "firewall": fw,
        "unit_tests": unit,
        "b58_ok": b58_ok,
        "candidate_count": len(rows),
        "vision_source": vision_source,
        "estimated_api_cost_usd": est_cost,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
        "known_conflicts": known_conflicts,
    }


__all__ = ["run_phase_p255"]
