"""P2.6.6 orchestrator. Shadow semantic resolver. Does not change P2.6.4/P2.6.5 routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP261_stratified_vision_candidate_recovery.set_artefacts import load_r13_index

from .config import (
    ADAPTER_SOURCE,
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MAX_LIVE_CALLS_REPLAY,
    MODE_LIVE,
    MODE_REPLAY,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
    SCOPE,
)
from .frozen_sample import (
    candidates_for_beam,
    load_frozen_candidates,
    load_frozen_manifest,
    load_p265_decisions,
)
from .regression import (
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .semantic_evaluator import evaluate_replay, is_semantic_target
from .semantic_report import write_reports
from .semantic_resolver import resolve_semantic
from .unit_tests import run_unit_tests

_V10 = Path(__file__).resolve().parents[2]


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_phase_p266(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_REPLAY,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (out_root, out_root / "cache", out_root / "evidence", out_root / "reports"):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode not in (MODE_REPLAY, MODE_LIVE):
        raise ValueError(f"unsupported mode {mode}")
    live_enabled = mode == MODE_LIVE
    if not live_enabled:
        mode = MODE_REPLAY

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {mode}")
    _log("  Observed routing = P2.6.4/P2.6.5 (unchanged). Semantic layer is shadow-only.")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    unit_path = out_root / "unit_tests.json"
    if run_tests:
        unit = run_unit_tests()
        _dump(unit_path, unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.6 unit tests failed: {failed}")
    elif unit_path.exists():
        try:
            unit = json.loads(unit_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.6 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.6 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    regions, sample_summary = load_frozen_manifest(v10)
    frozen_candidates = load_frozen_candidates(v10)
    p265_decisions = load_p265_decisions(v10)
    _log(f"  frozen sample {len(regions)} beams seed={sample_summary.get('seed')}")
    _log(f"  P2.6.5 decisions loaded: {len(p265_decisions)}")

    r13_cache: Dict[str, Dict[str, Any]] = {}
    targets: list = []
    live_calls = 0
    cache_hits = 0
    adapter_count = 0
    for row in p265_decisions:
        if not is_semantic_target(row, frozen_candidates):
            continue
        set_key = str(row.get("set_key") or "")
        beam_id = str(row.get("beam_id") or "")
        if set_key not in r13_cache:
            r13_cache[set_key] = load_r13_index(v10, set_key)
        model = r13_cache[set_key].get(beam_id)
        cands = candidates_for_beam(frozen_candidates, set_key, beam_id)
        live_payload = None
        source = ADAPTER_SOURCE
        if live_enabled:
            from .live_observer import observe_semantic
            from .semantic_context_builder import build_semantic_context

            ctx = build_semantic_context(
                p265_decision=row, frozen_candidates=cands, model=model
            )
            obs = observe_semantic(
                version10_root=v10,
                context=ctx,
                cache_root=out_root / "cache",
                crop_path=row.get("crop_path"),
                mode=MODE_LIVE,
            )
            if obs.get("live_call"):
                live_calls += 1
            if obs.get("cache_hit"):
                cache_hits += 1
            live_payload = obs.get("payload")
            if live_payload:
                source = str(obs.get("source") or "P266_LIVE_OR_CACHE")
        resolved = resolve_semantic(
            p265_decision=row,
            frozen_candidates=cands,
            model=model,
            live_payload=live_payload,
        )
        if resolved.get("semantic", {}).get("source") == ADAPTER_SOURCE:
            adapter_count += 1
        rec = dict(row)
        rec["semantic"] = resolved["semantic"]
        rec["hypothetical"] = resolved["hypothetical"]
        rec["context"] = resolved["context"]
        rec["observed_decision"] = resolved["observed_decision"]
        rec["production_routing_changed"] = False
        rec["adapter_source"] = resolved.get("adapter_source") or source
        rec["eval_stratum"] = row.get("eval_stratum")
        targets.append(rec)
        _log(
            f"  {set_key}/{beam_id} p264={rec.get('observed_decision')} "
            f"p265={rec.get('context_status')} semantic={rec['semantic'].get('decision')} "
            f"hypo={rec['hypothetical'].get('hypothetical_vision_routing')}"
        )

    replay_summary = {
        "target_count": len(targets),
        "replay_count": len(targets),
        "live_calls": live_calls if live_enabled else 0,
        "adapter_count": adapter_count,
        "cache_hits": cache_hits,
        "cache_hit_rate": (cache_hits / len(targets)) if targets and live_enabled else (1.0 if not live_enabled else 0.0),
        "source": ADAPTER_SOURCE if not live_enabled else "LIVE_SHADOW_WITH_ADAPTER_FALLBACK",
        "max_live_calls_replay": MAX_LIVE_CALLS_REPLAY,
    }
    if not live_enabled and live_calls != 0:
        raise RuntimeError("replay mode invoked live Vision")

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "p264_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p265_artefacts_unchanged": fp_cmp.get("unchanged"),
        "live_vision_invoked": bool(live_calls),
        "engineering_changes": ENGINEERING_CHANGES,
    }
    ev = evaluate_replay(
        p265_decisions=p265_decisions,
        target_records=targets,
        frozen_candidates=frozen_candidates,
        replay_summary=replay_summary,
        firewall_ok=bool(fw.get("ok")),
        leakage_ok=bool(leak.get("ok")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
    )
    _dump(out_root / "fingerprints_after.json", after)
    _dump(out_root / "gate_manifest.json", {
        "frozen": True,
        "resampled": False,
        "sample": sample_summary,
        "replay": replay_summary,
        "gate_version": GATE_VERSION,
        "observed_routing": "P264_P265_UNCHANGED",
        "cached_source": "PhaseP261_stratified_vision_candidate_recovery",
        "live_vision": bool(live_calls),
    })
    _dump(out_root / "target_records.json", targets)
    _dump(out_root / "false_skips.json", ev["false_skips"])
    _dump(out_root / "false_calls.json", ev["false_calls"])
    _dump(out_root / "metrics.json", ev["metrics"])
    _dump(out_root / "hypothetical_metrics.json", ev["hypothetical_metrics"])
    _dump(out_root / "control_cases.json", ev.get("control_cases") or [])

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
            if unit.get("success") and fw.get("ok") and leak.get("ok") and fp_cmp.get("unchanged") and (live_calls == 0 or live_enabled)
            else "FAIL"
        ),
        "output_root": str(out_root),
        "sample": sample_summary,
        "replay": replay_summary,
        "replay_source": replay_summary.get("source"),
        "metrics": ev["metrics"],
        "hypothetical_metrics": ev["hypothetical_metrics"],
        "recommendation": ev["recommendation"],
        "false_skips": ev["false_skips"],
        "false_calls": ev["false_calls"],
        "control_cases": ev.get("control_cases") or [],
        "target_records": targets,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "decision": ev["recommendation"].get("decision"),
        "strength": ev["recommendation"].get("strength"),
        "live_cost_usd": "not run" if not live_enabled else "live shadow",
        "live_vision_invoked": bool(live_calls),
    }
    if not live_enabled:
        result["pass_fail"] = (
            "PASS"
            if unit.get("success") and fw.get("ok") and leak.get("ok") and fp_cmp.get("unchanged") and live_calls == 0
            else "FAIL"
        )
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    result_dump = dict(result)
    result_dump.pop("target_records", None)
    _dump(out_root / "result.json", result_dump)
    sm = ev["metrics"]
    _log(
        f"  targets={sm.get('TARGET_BEAMS')} DISTINCT={sm.get('DISTINCT_REINFORCEMENT')} "
        f"DUP={sm.get('DUPLICATE_OR_REPEAT')} AMB={sm.get('AMBIGUOUS')} UNS={sm.get('UNSUPPORTED')}"
    )
    _log(
        f"  separability={ (sm.get('separability') or {}).get('semantic_distinguishes_b128_from_b141_b23') }"
    )
    _log(f"  decision={result.get('decision')} strength={result.get('strength')}")
    return result


__all__ = ["run_phase_p266"]
