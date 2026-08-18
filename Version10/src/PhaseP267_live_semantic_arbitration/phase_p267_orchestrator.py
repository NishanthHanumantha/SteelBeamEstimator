"""P2.6.7 orchestrator. Live shadow benchmark. Does not change production routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import (
    ENGINEERING_CHANGES,
    EXPECTED_LIVE_CALLS,
    GATE_VERSION,
    MODE_LIVE,
    MODE_REPARSE,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PASS_PRIMARY,
    PASS_REPEAT,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
    SCOPE,
    TARGET_BEAMS,
)
from .dataset import load_p266_targets, reference_class, resolve_crop_path
from .evaluator import (
    SEPARABILITY_TRIPLE,
    attach_eval_fields,
    classify_phase,
    critical_repeatability,
    evaluate_accuracy,
    evaluate_critical,
    fully_covered_untouched,
)
from .live_caller import live_observe, require_api_key, sanitize_text
from .live_context import build_live_context
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .repeatability import compute_repeatability
from .reparse import load_and_reparse
from .report import write_reports
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _write_raw(raw_root: Path, rec: Dict[str, Any], pass_id: str, obs: Dict[str, Any]) -> None:
    name = f"{pass_id}__{rec.get('set_key')}__{rec.get('beam_id')}.json"
    _dump(
        raw_root / name,
        sanitize_text(
            {
                "set_key": rec.get("set_key"),
                "beam_id": rec.get("beam_id"),
                "pass_id": pass_id,
                "ok": obs.get("ok"),
                "error_class": obs.get("error_class"),
                "error": obs.get("error"),
                "retry_count": obs.get("retry_count"),
                "latency_s": obs.get("latency_s"),
                "usage": obs.get("usage"),
                "raw_response": obs.get("raw_response"),
                "payload": obs.get("payload"),
                "cache_hit": obs.get("cache_hit"),
                "source": obs.get("source"),
            }
        ),
    )


def _base_record(target: Dict[str, Any], *, v10: Path) -> Dict[str, Any]:
    set_key = str(target.get("set_key") or "")
    beam_id = str(target.get("beam_id") or "")
    crop = resolve_crop_path(v10, target)
    return {
        "set_key": set_key,
        "beam_id": beam_id,
        "region_id": target.get("region_id"),
        "longitudinal_coverage": target.get("longitudinal_coverage"),
        "observed_decision": target.get("observed_decision") or target.get("decision"),
        "p265_context_status": target.get("context_status") or target.get("p265_context_status"),
        "p266_reference": reference_class(target),
        "production_routing_changed": False,
        "crop_path": str(crop),
    }


def _count_pass(records: List[Dict[str, Any]], key: str) -> Tuple[int, int, int, int, int, int]:
    ok_n = 0
    fail_n = 0
    live_n = 0
    reparsed_n = 0
    cache_n = 0
    retries = 0
    for rec in records:
        obs = rec.get(key) or {}
        if obs.get("ok"):
            ok_n += 1
        else:
            fail_n += 1
        if obs.get("live_call"):
            live_n += 1
        if obs.get("schema_reparsed"):
            reparsed_n += 1
        if obs.get("cache_hit"):
            cache_n += 1
        retries += int(obs.get("retry_count") or 0)
    return ok_n, fail_n, live_n, reparsed_n, cache_n, retries


def _finalize(
    *,
    out_root: Path,
    mode: str,
    unit: Dict[str, Any],
    fw: Dict[str, Any],
    leak: Dict[str, Any],
    before: Dict[str, Any],
    fp_paths: Dict[str, Path],
    targets: List[Dict[str, Any]],
    records: List[Dict[str, Any]],
    live_attempts: int,
    cache_hits: int,
    retries: int,
    primary_ok: int,
    repeat_ok: int,
    primary_fail: int,
    repeat_fail: int,
    schema_reparsed_primary: int,
    schema_reparsed_repeat: int,
    log,
) -> Dict[str, Any]:
    records = attach_eval_fields(records)
    accuracy = evaluate_accuracy(records)
    repeatability = compute_repeatability(records)
    critical = evaluate_critical(records)
    crit_rep = critical_repeatability(records, list(SEPARABILITY_TRIPLE))
    recommendation = classify_phase(
        accuracy=accuracy,
        repeat=repeatability,
        critical=critical,
        live_ok=live_attempts > 0 and cache_hits == 0,
        fingerprints_ok=True,
        production_mutation=0,
        successful_primary=primary_ok,
        successful_repeat=repeat_ok,
    )

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "p264_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p265_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p266_artefacts_unchanged": fp_cmp.get("unchanged"),
        "live_vision_invoked": mode == MODE_LIVE and live_attempts > 0,
        "stored_live_raw_reparsed": mode == MODE_REPARSE,
        "engineering_changes": ENGINEERING_CHANGES,
        "fully_covered_untouched": fully_covered_untouched(records),
    }
    if not fp_cmp.get("unchanged"):
        recommendation = {
            "decision": "LIVE_BENCHMARK_FAILED",
            "strength": "PRODUCTION_MUTATION",
            "note": f"Fingerprint change: {fp_cmp.get('changed_keys')}",
        }

    metrics = {
        "target_beams": len(targets),
        "primary_live_calls": len(targets),
        "repeat_live_calls": len(targets),
        "total_live_calls": live_attempts,
        "successful_primary": primary_ok,
        "successful_repeat": repeat_ok,
        "failed_primary": primary_fail,
        "failed_repeat": repeat_fail,
        "retry_count_total": retries,
        "cache_hits": cache_hits,
        "expected_live_calls": EXPECTED_LIVE_CALLS,
        "schema_reparsed_primary": schema_reparsed_primary,
        "schema_reparsed_repeat": schema_reparsed_repeat,
        "schema_reparsed_total": schema_reparsed_primary + schema_reparsed_repeat,
        "api_failures_remaining": sum(
            1
            for r in records
            for key in ("primary", "repeat")
            if not (r.get(key) or {}).get("ok")
            and str((r.get(key) or {}).get("error_class") or "") == "api_failure"
        ),
        "accuracy": accuracy,
        "repeatability": repeatability,
        "critical": critical,
        "critical_repeatability": crit_rep,
        "LIVE_VISION_CALLS": live_attempts,
    }
    interpretation = (
        f"Live Claude primary split strong={critical.get('strong_split')}; "
        f"B128 duplicate failure={critical.get('b128_duplicate_failure')}; "
        f"repeatability={repeatability.get('semantic_repeatability_rate')}; "
        f"false DUPLICATE={accuracy.get('false_DUPLICATE')}. "
        "This does not change production routing and is not PRODUCTION_READY."
    )
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
            and live_attempts == EXPECTED_LIVE_CALLS
            and cache_hits == 0
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
        "interpretation": interpretation,
        "live_vision_invoked": mode == MODE_LIVE,
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    dump = dict(result)
    dump.pop("records", None)
    _dump(out_root / "result.json", dump)
    _dump(out_root / "fingerprints_after.json", after)
    log(f"  live_attempts={live_attempts} primary_ok={primary_ok} repeat_ok={repeat_ok}")
    log(f"  decision={result.get('decision')} strength={result.get('strength')}")
    return result


def run_phase_p267(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_LIVE,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    raw_root = out_root / "raw_responses"
    for d in (out_root, raw_root, out_root / "reports"):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode not in (MODE_LIVE, MODE_REPARSE):
        raise RuntimeError(
            f"P2.6.7 supported modes: {MODE_LIVE}, {MODE_REPARSE}. "
            f"Received {mode!r}. Refusing to silently convert to replay."
        )

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {mode}")
    _log("  Observed routing = P2.6.4/P2.6.5 unchanged. Live semantic is shadow-only.")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.7 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.7 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.7 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    targets = load_p266_targets(v10)
    _log(f"  loaded P2.6.6 targets: {len(targets)} (expected {TARGET_BEAMS})")

    if mode == MODE_REPARSE:
        _log("  REPARSE_STORED_LIVE_RAW: no new API calls; re-validating stored Claude text only.")
        records: list = []
        for i, target in enumerate(targets, start=1):
            rec = _base_record(target, v10=v10)
            set_key = rec["set_key"]
            beam_id = rec["beam_id"]
            _log(f"  [{i}/{len(targets)}] {set_key}/{beam_id} reparse stored primary/repeat...")
            rec["primary"] = load_and_reparse(
                raw_root, set_key=set_key, beam_id=beam_id, pass_id=PASS_PRIMARY
            )
            rec["repeat"] = load_and_reparse(
                raw_root, set_key=set_key, beam_id=beam_id, pass_id=PASS_REPEAT
            )
            records.append(rec)
            prim = rec["primary"]
            rpt = rec["repeat"]
            _log(
                f"    primary={((prim.get('payload') or {}).get('decision') if prim.get('ok') else prim.get('error_class'))} "
                f"repeat={((rpt.get('payload') or {}).get('decision') if rpt.get('ok') else rpt.get('error_class'))}"
            )
        primary_ok, primary_fail, live_p, repar_p, cache_p, retries_p = _count_pass(records, "primary")
        repeat_ok, repeat_fail, live_r, repar_r, cache_r, retries_r = _count_pass(records, "repeat")
        return _finalize(
            out_root=out_root,
            mode=mode,
            unit=unit,
            fw=fw,
            leak=leak,
            before=before,
            fp_paths=fp_paths,
            targets=targets,
            records=records,
            live_attempts=live_p + live_r,
            cache_hits=cache_p + cache_r,
            retries=retries_p + retries_r,
            primary_ok=primary_ok,
            repeat_ok=repeat_ok,
            primary_fail=primary_fail,
            repeat_fail=repeat_fail,
            schema_reparsed_primary=repar_p,
            schema_reparsed_repeat=repar_r,
            log=_log,
        )

    try:
        require_api_key(v10)
    except Exception as exc:
        raise RuntimeError(
            f"P2.6.7 LIVE_API cannot execute: {type(exc).__name__}: {exc}. "
            "Refusing to fall back to P2.6.1 replay or P2.6.6 cached semantic decisions."
        ) from exc

    records = []
    primary_ok = 0
    repeat_ok = 0
    primary_fail = 0
    repeat_fail = 0
    live_attempts = 0
    retries = 0
    cache_hits = 0
    for i, target in enumerate(targets, start=1):
        rec = _base_record(target, v10=v10)
        set_key = rec["set_key"]
        beam_id = rec["beam_id"]
        context = build_live_context(target)
        crop = Path(rec["crop_path"])
        _log(f"  [{i}/{len(targets)}] {set_key}/{beam_id} PRIMARY live...")
        prim = live_observe(
            version10_root=v10,
            context=context,
            crop=crop,
            pass_id=PASS_PRIMARY,
            bypass_cache=True,
        )
        live_attempts += 1 if prim.get("live_call") else 0
        retries += int(prim.get("retry_count") or 0)
        cache_hits += 1 if prim.get("cache_hit") else 0
        if prim.get("ok"):
            primary_ok += 1
        else:
            primary_fail += 1
        _write_raw(raw_root, rec, PASS_PRIMARY, prim)

        _log(f"  [{i}/{len(targets)}] {set_key}/{beam_id} REPEAT live...")
        rpt = live_observe(
            version10_root=v10,
            context=context,
            crop=crop,
            pass_id=PASS_REPEAT,
            bypass_cache=True,
        )
        live_attempts += 1 if rpt.get("live_call") else 0
        retries += int(rpt.get("retry_count") or 0)
        cache_hits += 1 if rpt.get("cache_hit") else 0
        if rpt.get("ok"):
            repeat_ok += 1
        else:
            repeat_fail += 1
        _write_raw(raw_root, rec, PASS_REPEAT, rpt)

        rec["primary"] = prim
        rec["repeat"] = rpt
        records.append(rec)
        _log(
            f"    primary={((prim.get('payload') or {}).get('decision') if prim.get('ok') else prim.get('error_class'))} "
            f"repeat={((rpt.get('payload') or {}).get('decision') if rpt.get('ok') else rpt.get('error_class'))}"
        )

    return _finalize(
        v10=v10,
        out_root=out_root,
        mode=mode,
        unit=unit,
        fw=fw,
        leak=leak,
        before=before,
        fp_paths=fp_paths,
        targets=targets,
        records=records,
        live_attempts=live_attempts,
        cache_hits=cache_hits,
        retries=retries,
        primary_ok=primary_ok,
        repeat_ok=repeat_ok,
        primary_fail=primary_fail,
        repeat_fail=repeat_fail,
        schema_reparsed_primary=0,
        schema_reparsed_repeat=0,
        log=_log,
    )


__all__ = ["run_phase_p267"]
