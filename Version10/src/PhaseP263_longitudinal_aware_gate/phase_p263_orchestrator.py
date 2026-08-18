"""
P2.6.3 orchestrator — Longitudinal-Aware Selective Vision Gate.

Frozen P2.6.1 replay by default. Deterministic production remains sole authority.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_SRC = Path(__file__).resolve().parents[1]
_V10 = Path(__file__).resolve().parents[2]
for p in (str(_SRC), str(_V10)):
    if p not in sys.path:
        sys.path.insert(0, p)

from PhaseP261_stratified_vision_candidate_recovery.set_artefacts import (  # noqa: E402
    load_ownership,
    load_r13_index,
)

from .config import (  # noqa: E402
    ENGINEERING_CHANGES,
    GATE_VERSION,
    MODE_LIVE,
    MODE_REPLAY,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
    SCOPE,
)
from .evaluator import evaluate_replay  # noqa: E402
from .evidence import write_evidence  # noqa: E402
from .frozen_sample import load_frozen_candidates, load_frozen_manifest  # noqa: E402
from .gate_decision import build_gate_decision  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .replay_runner import apply_gate_to_frozen  # noqa: E402
from .report_builder import write_reports  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def run_phase_p263(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_REPLAY,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (out_root, out_root / "evidence", out_root / "reports"):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode not in (MODE_REPLAY, MODE_LIVE):
        raise ValueError(f"unsupported mode {mode}")
    if mode == MODE_LIVE:
        _log("  LIVE mode requested; P2.6.3 still executes REPLAY_P261_CACHED only.")
        mode = MODE_REPLAY

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {mode}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  production_write={PRODUCTION_WRITE}")
    _log("  Gated replay using frozen P2.6.1 Vision responses.")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    unit_path = out_root / "unit_tests.json"
    if run_tests:
        unit = run_unit_tests()
        _dump(unit_path, unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.3 unit tests failed: {failed}")
    elif unit_path.exists():
        try:
            unit = json.loads(unit_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.3 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.3 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    regions, sample_summary = load_frozen_manifest(v10)
    frozen_candidates = load_frozen_candidates(v10)
    _log(f"  frozen sample {len(regions)} beams seed={sample_summary.get('seed')}")

    own_cache: Dict[str, Dict[str, Any]] = {}
    r13_cache: Dict[str, Dict[str, Any]] = {}
    decisions: list = []
    for row in regions:
        set_key = row["set_key"]
        beam_id = row["beam_id"]
        if set_key not in own_cache:
            own_cache[set_key] = (load_ownership(v10, set_key).get("by_beam") or {})
            r13_cache[set_key] = load_r13_index(v10, set_key)
        rec = own_cache[set_key].get(beam_id) or {}
        model = r13_cache[set_key].get(beam_id)
        decision = build_gate_decision(
            beam_id=beam_id,
            region_id=row.get("region_id") or f"P261::{set_key}::{beam_id}",
            rec=rec,
            model=model,
            set_key=set_key,
            source_set=row.get("source_set") or "",
            crop_path=row.get("crop_path"),
        )
        decision["eval_stratum"] = row.get("stratum")
        decisions.append(decision)
        _log(
            f"  {set_key}/{beam_id} [{row.get('stratum')}] "
            f"{decision['decision']} cov={decision.get('longitudinal_coverage')} "
            f"{decision['reason_codes']}"
        )

    gated, replay_summary = apply_gate_to_frozen(
        decisions=decisions, frozen_candidates=frozen_candidates
    )
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "p262_artefacts_unchanged": fp_cmp.get("unchanged"),
        "live_vision_invoked": False,
        "engineering_changes": ENGINEERING_CHANGES,
    }
    ev = evaluate_replay(
        decisions=decisions,
        baseline_candidates=frozen_candidates,
        gated_candidates=gated,
        firewall_ok=bool(fw.get("ok")),
        leakage_ok=bool(leak.get("ok")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
    )
    evidence = write_evidence(
        evidence_root=out_root / "evidence",
        decisions=decisions,
        gated_candidates=gated,
        baseline_candidates=frozen_candidates,
        false_skips=ev["false_skips"],
        false_calls=ev["false_calls"],
    )

    gate_manifest = {
        "frozen": True,
        "resampled": False,
        "sample": sample_summary,
        "replay": replay_summary,
        "gate_version": GATE_VERSION,
        "cached_source": "PhaseP261_stratified_vision_candidate_recovery",
        "live_vision": False,
    }
    _dump(out_root / "gate_manifest.json", gate_manifest)
    _dump(out_root / "gate_decisions.json", decisions)
    _dump(out_root / "false_skips.json", ev["false_skips"])
    _dump(out_root / "false_calls.json", ev["false_calls"])
    _dump(out_root / "metrics.json", ev["metrics"])
    _dump(out_root / "gated_candidates.json", gated)

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
            if unit.get("success") and fw.get("ok") and leak.get("ok") and fp_cmp.get("unchanged")
            else "FAIL"
        ),
        "output_root": str(out_root),
        "sample": sample_summary,
        "replay": replay_summary,
        "metrics": ev["metrics"],
        "recommendation": ev["recommendation"],
        "false_skips": ev["false_skips"],
        "false_calls": ev["false_calls"],
        "decisions": decisions,
        "evidence": evidence,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "decision": ev["recommendation"].get("decision"),
        "strength": ev["recommendation"].get("strength"),
        "live_cost_usd": "not run",
        "live_vision_invoked": False,
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    result_dump = dict(result)
    result_dump.pop("decisions", None)
    _dump(out_root / "result.json", result_dump)
    m = ev["metrics"]
    _log(
        f"  CALL={m.get('CALL_BEAMS')} SKIP={m.get('SKIP_BEAMS')} HOLD={m.get('HOLD_BEAMS')} "
        f"reduction={m.get('CALL_REDUCTION')} retention={m.get('RECOVERY_RETENTION_RATE')}"
    )
    _log(
        f"  stirrup={m.get('STIRRUP_GATED_TRUE_RECOVERIES')}/"
        f"{m.get('STIRRUP_BASELINE_TRUE_RECOVERIES')} "
        f"long={m.get('LONGITUDINAL_GATED_TRUE_RECOVERIES')}/"
        f"{m.get('LONGITUDINAL_BASELINE_TRUE_RECOVERIES')}"
    )
    _log(f"  decision={result.get('decision')} strength={result.get('strength')}")
    return result


__all__ = ["run_phase_p263"]
