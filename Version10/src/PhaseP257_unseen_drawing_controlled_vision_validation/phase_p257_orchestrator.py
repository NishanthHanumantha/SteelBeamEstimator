"""
P2.5.7 orchestrator — Unseen-Drawing Controlled Vision Validation.

LIVE Claude on Fifth Set. Selective shadow. Independent GT.
Deterministic P2.5.1 remains production authority. No production write.
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

from PhaseP256_controlled_field_level_vision_experiment.integrator import (  # noqa: E402
    evaluate_one,
)

from .candidate_builder import build_candidates  # noqa: E402
from .config import (  # noqa: E402
    CLAUDE_MODEL,
    ENGINEERING_CHANGES,
    MODE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    SCOPE,
    TEMPERATURE,
)
from .dataset import assert_unseen, build_dataset_manifest  # noqa: E402
from .gt_oracle import ground_truth_for_intent  # noqa: E402
from .live_observer import observe_live  # noqa: E402
from .metrics import compute_cost_metrics, compute_metrics  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
)
from .report_builder import write_reports  # noqa: E402
from .three_way import evaluate_candidate  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _audit_row(row: Dict[str, Any]) -> Dict[str, Any]:
    cand = row.get("candidate") or {}
    det = row.get("deterministic") or {}
    obs = row.get("vision_obs") or {}
    fr = row.get("field_result") or {}
    return {
        "candidate_id": cand.get("candidate_id"),
        "beam_id": cand.get("beam_id"),
        "annotation_id": cand.get("annotation_id"),
        "annotation_text": cand.get("raw_text"),
        "invoke_claude": row.get("invoke_claude"),
        "skip_reason": row.get("skip_reason"),
        "shadow_trigger_reason": cand.get("shadow_trigger_reason"),
        "deterministic_result": det.get("deterministic_result"),
        "deterministic_status": det.get("deterministic_status"),
        "vision_result": obs.get("validated_interpretation"),
        "vision_api_ok": obs.get("api_ok"),
        "vision_error": obs.get("error"),
        "field_comparisons": fr.get("field_comparisons"),
        "accepted_shadow_fields": row.get("accepted_shadow_fields") or [],
        "rejected_shadow_fields": row.get("rejected_shadow_fields") or [],
        "conflict_fields": row.get("conflict_fields") or [],
        "final_shadow_decision": row.get("final_shadow_decision"),
        "ground_truth": row.get("ground_truth"),
        "three_way": row.get("three_way"),
        "validation": obs.get("validation"),
        "prompt_fingerprint": obs.get("prompt_fingerprint"),
        "evidence_fingerprint": obs.get("evidence_fingerprint"),
        "model": obs.get("model"),
        "temperature": obs.get("temperature"),
        "prompt_version": obs.get("prompt_version") or PROMPT_VERSION,
        "schema_version": obs.get("schema_version") or SCHEMA_VERSION,
        "production_write": False,
        "production_mutation": False,
    }


def _decide(
    *,
    unseen: bool,
    unit_ok: bool,
    fw_ok: bool,
    reg_unchanged: bool,
    live_calls: int,
    failed_calls: int,
    writes_ok: bool,
    dangerous_rate: Optional[float],
    dangerous_count: int,
    leak_blocked: int,
) -> Dict[str, str]:
    if not unseen:
        return {"pass_fail": "BLOCKED", "decision": "BLOCKED — DATA_REQUIRED"}
    if leak_blocked:
        return {"pass_fail": "FAIL", "decision": "FAIL — VISION_NOT_SAFE"}
    if not writes_ok or not fw_ok:
        return {"pass_fail": "FAIL", "decision": "FAIL — VISION_NOT_SAFE"}
    if not unit_ok or not reg_unchanged:
        return {"pass_fail": "FAIL", "decision": "FAIL — VISION_NOT_SAFE"}
    if live_calls <= 0:
        return {"pass_fail": "BLOCKED", "decision": "BLOCKED — DATA_REQUIRED"}
    if failed_calls > 0 and failed_calls == live_calls:
        return {"pass_fail": "BLOCKED", "decision": "BLOCKED — DATA_REQUIRED"}
    if dangerous_rate is not None and dangerous_rate >= 0.25 and dangerous_count >= 5:
        return {"pass_fail": "FAIL", "decision": "FAIL — VISION_NOT_SAFE"}
    if failed_calls > 0:
        return {"pass_fail": "PASS_WITH_LIMITATIONS", "decision": "PASS_WITH_LIMITATIONS"}
    return {"pass_fail": "PASS", "decision": "READY_FOR_NEXT_CONTROLLED_EXPERIMENT"}


def run_phase_p257(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    live: bool = True,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (
        out_root,
        out_root / "manifest",
        out_root / "baseline",
        out_root / "vision",
        out_root / "field_level",
        out_root / "ground_truth",
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
    _log(f"  live={live}  output={out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "evaluation" / "unit_tests.json", unit)
        _log(f"  Unit tests P257: {unit['passed']}/{unit['total']}")
        p256u = unit.get("p256_unit_tests") or {}
        p255u = unit.get("p255_unit_tests") or {}
        p254u = unit.get("p254_unit_tests") or {}
        _log(f"  Unit tests P256: {p256u.get('passed')}/{p256u.get('total')}")
        _log(f"  Unit tests P255: {p255u.get('passed')}/{p255u.get('total')}")
        _log(f"  Unit tests P254: {p254u.get('passed')}/{p254u.get('total')}")
        if not unit.get("success"):
            return {
                "success": False,
                "pass_fail": "FAIL",
                "decision": "FAIL — VISION_NOT_SAFE",
                "unit_tests": unit,
                "output_root": str(out_root),
            }

    if not live:
        return {
            "success": False,
            "pass_fail": "FAIL",
            "decision": "FAIL — VISION_NOT_SAFE",
            "error": "P2.5.7 requires LIVE Claude calls; replay is not permitted",
            "unit_tests": unit,
            "output_root": str(out_root),
        }

    manifest = build_dataset_manifest(v10)
    _dump(out_root / "manifest" / "dataset_manifest.json", manifest)
    _dump(out_root / "dataset_manifest.json", manifest)
    unseen = bool(manifest.get("UNSEEN_SET_VERIFIED"))
    _log(f"  UNSEEN_SET_VERIFIED={unseen} set={manifest.get('drawing_set_id')}")
    if not unseen:
        summary = {
            "pass_fail": "BLOCKED",
            "decision": "BLOCKED — DATA_REQUIRED",
            "dataset": manifest,
            "metrics": {},
            "cost": {},
            "unit_tests": unit,
            "regression": {},
            "firewall": firewall_check(v10),
            "mode": MODE,
            "candidate_count": 0,
        }
        write_reports(out_root=out_root, summary=summary, rows=[])
        return {
            "success": False,
            "pass_fail": "BLOCKED",
            "decision": "BLOCKED — DATA_REQUIRED",
            "dataset": manifest,
            "output_root": str(out_root),
            "unit_tests": unit,
        }
    assert_unseen(manifest)

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)

    _log("  Building Fifth Set P2.5.1 candidates…")
    all_rows, eligible = build_candidates(v10)
    _log(f"  candidates={len(all_rows)} eligible_live={len(eligible)} skipped={len(all_rows) - len(eligible)}")

    det_snap = [
        {
            "candidate_id": r["candidate"]["candidate_id"],
            "invoke_claude": r["invoke_claude"],
            "skip_reason": r["skip_reason"],
            "shadow_trigger_reason": r["candidate"].get("shadow_trigger_reason"),
            "deterministic": r["deterministic"],
        }
        for r in all_rows
    ]
    _dump(out_root / "baseline" / "deterministic_snapshot.json", det_snap)
    _dump(out_root / "deterministic_snapshot.json", det_snap)

    rows: List[Dict[str, Any]] = []
    leak_blocked = 0
    for i, row in enumerate(all_rows, start=1):
        cand = row["candidate"]
        det = row["deterministic"]
        gt = ground_truth_for_intent(det.get("deterministic_result") or {}, cand.get("raw_text") or "")
        vision_obs: Dict[str, Any] = {
            "live_call": False,
            "api_ok": False,
            "vision_source": "NOT_INVOKED",
            "validated_interpretation": None,
            "validation": {"valid": False, "errors": [], "warnings": []},
            "usage": {},
            "replay": False,
        }
        p256: Dict[str, Any] = {}
        if row["invoke_claude"]:
            _log(
                f"  [{i}/{len(all_rows)}] LIVE {cand['candidate_id']} "
                f"text={cand.get('raw_text')!r} triggers={cand.get('shadow_trigger_reason')}"
            )
            vision_obs = observe_live(candidate=cand, version10_root=v10)
            if vision_obs.get("error") == "TRUTH_LEAK_BLOCKED":
                leak_blocked += 1
            p256 = evaluate_one(
                candidate=cand,
                deterministic=det,
                vision_obs=vision_obs,
                ground_truth=gt,
            )
            _dump(
                out_root / "vision" / "calls" / f"{cand['candidate_id'].replace('::', '__')}.json",
                {
                    "candidate_id": cand["candidate_id"],
                    "api_ok": vision_obs.get("api_ok"),
                    "error": vision_obs.get("error"),
                    "usage": vision_obs.get("usage"),
                    "prompt_fingerprint": vision_obs.get("prompt_fingerprint"),
                    "evidence_fingerprint": vision_obs.get("evidence_fingerprint"),
                    "validated_interpretation": vision_obs.get("validated_interpretation"),
                    "validation": vision_obs.get("validation"),
                },
            )
        accepted = p256.get("accepted_shadow_fields") or []
        tw = evaluate_candidate(
            deterministic=det,
            vision=(vision_obs.get("validated_interpretation") if vision_obs.get("api_ok") else None),
            ground_truth=gt,
            accepted_shadow_fields=accepted,
        )
        packed = {
            **row,
            "ground_truth": gt,
            "vision_obs": vision_obs,
            "field_result": p256.get("field_result"),
            "accepted_shadow_fields": accepted,
            "rejected_shadow_fields": p256.get("rejected_shadow_fields") or [],
            "conflict_fields": p256.get("conflict_fields") or [],
            "final_shadow_decision": p256.get("final_shadow_decision"),
            "three_way": tw,
            "production_write": False,
        }
        rows.append(packed)

    metrics = compute_metrics(rows)
    cost = compute_cost_metrics(
        vision_rows=rows,
        true_incremental_field_count=int(metrics.get("true_incremental_field_count") or 0),
        eligible_count=len(eligible),
    )
    fw = firewall_check(v10)
    after = capture_fingerprints(fp_paths)
    reg = compare_fingerprints(before, after)
    changed = reg.get("changed_keys") or []

    audits = [_audit_row(r) for r in rows]
    _dump(out_root / "vision" / "vision_results.json", audits)
    _dump(out_root / "vision_results.json", audits)
    _dump(
        out_root / "field_level" / "field_level_results.json",
        [{k: r[k] for k in ("candidate", "field_result", "three_way", "accepted_shadow_fields", "conflict_fields") if k in r} for r in rows],
    )
    _dump(out_root / "field_level_results.json", [r.get("field_result") for r in rows])
    _dump(
        out_root / "ground_truth" / "ground_truth_evaluation.json",
        [{"candidate_id": (r.get("candidate") or {}).get("candidate_id"), "ground_truth": r.get("ground_truth"), "three_way": r.get("three_way")} for r in rows],
    )
    _dump(out_root / "ground_truth_evaluation.json", [r.get("ground_truth") for r in rows])
    _dump(out_root / "evaluation" / "incremental_value_metrics.json", metrics)
    _dump(out_root / "evaluation" / "cost_metrics.json", cost)
    _dump(
        out_root / "evaluation" / "skipped_candidates.json",
        [
            {
                "candidate_id": r["candidate"]["candidate_id"],
                "raw_text": r["candidate"].get("raw_text"),
                "skip_reason": r.get("skip_reason"),
            }
            for r in rows
            if not r.get("invoke_claude")
        ],
    )
    _dump(out_root / "evaluation" / "candidates.json", audits)

    writes_ok = all((r.get("production_write") is False) for r in rows)
    zone_ok = all(
        "zone" not in (r.get("accepted_shadow_fields") or []) for r in rows
    )
    p251_ok = not any(str(k).startswith("p251") for k in changed)
    p254_ok = not any(str(k).startswith("p254") for k in changed)
    p255_ok = not any(str(k).startswith("p255") for k in changed)
    p256_ok = not any(str(k).startswith("p256") for k in changed)
    prod_changed = [
        k
        for k in changed
        if str(k).startswith("production")
        or str(k).startswith("fifth_")
        or str(k).startswith("fourth_")
    ]
    if prod_changed:
        writes_ok = False
        metrics["excel_difference"] = 1 if any("excel" in str(k).lower() for k in prod_changed) else 0
        metrics["bbs_difference"] = 1 if any("bbs" in str(k).lower() for k in prod_changed) else 0
        metrics["steel_quantity_difference"] = (
            1 if any("physical" in str(k).lower() or "r13" in str(k).lower() for k in prod_changed) else 0
        )
        metrics["production_mutation_count"] = len(prod_changed)

    decision = _decide(
        unseen=unseen,
        unit_ok=bool(unit.get("success")),
        fw_ok=bool(fw.get("ok")) and zone_ok,
        reg_unchanged=bool(reg.get("unchanged")) and p251_ok and p254_ok and p255_ok and p256_ok,
        live_calls=int(cost.get("live_claude_calls") or 0),
        failed_calls=int(cost.get("failed_calls") or 0),
        writes_ok=writes_ok,
        dangerous_rate=metrics.get("dangerous_vision_override_rate"),
        dangerous_count=int(metrics.get("dangerous_vision_override_count") or 0),
        leak_blocked=leak_blocked,
    )

    summary = {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "mode": MODE,
        "pass_fail": decision["pass_fail"],
        "decision": decision["decision"],
        "vision_source": "LIVE_P254_PROMPT",
        "claude_model": CLAUDE_MODEL,
        "temperature": TEMPERATURE,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "candidate_count": len(rows),
        "eligible_count": len(eligible),
        "skipped_count": len(rows) - len(eligible),
        "dataset": manifest,
        "metrics": metrics,
        "cost": cost,
        "regression": {
            "unchanged": reg.get("unchanged"),
            "changed_keys": changed,
            "p251_unchanged": p251_ok,
            "p254_unchanged": p254_ok,
            "p255_unchanged": p255_ok,
            "p256_unchanged": p256_ok,
        },
        "firewall": fw,
        "engineering_changes": ENGINEERING_CHANGES,
        "production_output_changes": "NONE" if not prod_changed else str(prod_changed),
        "unit_tests": unit,
        "leak_blocked": leak_blocked,
    }
    write_reports(out_root=out_root, summary=summary, rows=rows)
    _dump(out_root / "evaluation" / "regression.json", {"compare": {"unchanged": reg.get("unchanged"), "changed_keys": changed}})
    _dump(out_root / "evaluation" / "summary.json", summary)

    _log(f"  PASS/FAIL: {decision['pass_fail']}")
    _log(f"  Decision: {decision['decision']}")
    _log(f"  live={cost.get('live_claude_calls')} failed={cost.get('failed_calls')}")
    _log(f"  TRUE_INCREMENTAL={metrics.get('TRUE_VISION_INCREMENTAL_VALUE_RATE')}")
    _log(f"  combined={metrics.get('HYPOTHETICAL_COMBINED_ACCURACY')} delta={metrics.get('IMPROVEMENT_DELTA')}")
    return {
        "success": decision["pass_fail"] in ("PASS", "PASS_WITH_LIMITATIONS"),
        "pass_fail": decision["pass_fail"],
        "decision": decision["decision"],
        "output_root": str(out_root),
        "metrics": metrics,
        "cost": cost,
        "regression": summary["regression"],
        "firewall": fw,
        "dataset": manifest,
        "candidate_count": len(rows),
        "eligible_count": len(eligible),
        "skipped_count": len(rows) - len(eligible),
        "unit_tests": unit,
        "meta": {"model_version": MODEL_VERSION, "phase_id": PHASE_ID},
        "engineering_changes": ENGINEERING_CHANGES,
        "production_changes": "NONE",
    }


__all__ = ["run_phase_p257"]
