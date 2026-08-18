"""
P2.6.5 orchestrator — Spatial / Context-Aware Longitudinal Ambiguity Resolution.

Frozen P2.6.1 replay. P2.6.4 routing is observed and not modified.
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
from .evaluator import evaluate_replay, sensitivity_analysis  # noqa: E402
from .evidence import write_evidence  # noqa: E402
from .frozen_sample import load_frozen_candidates, load_frozen_manifest  # noqa: E402
from .geometry_loader import load_beam_scoped_index  # noqa: E402
from .hypothetical import apply_hypothetical  # noqa: E402
from .metrics import classify_gate  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .replay_runner import apply_gate_to_frozen  # noqa: E402
from .report_builder import write_reports  # noqa: E402
from .shadow_overlay import build_shadow_record  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _feature_row(d: Dict[str, Any]) -> Dict[str, Any]:
    spat = d.get("spatial_features") or {}
    feat = d.get("production_features") or {}
    return {
        "set_key": d.get("set_key"),
        "beam_id": d.get("beam_id"),
        "eval_stratum": d.get("eval_stratum"),
        "annotation_text": [p.get("text") for p in (d.get("per_annotation_spatial") or [])],
        "quantity": [p.get("quantity") for p in (d.get("per_annotation_spatial") or [])],
        "diameter": [p.get("diameter_mm") for p in (d.get("per_annotation_spatial") or [])],
        "role": [p.get("role") for p in (d.get("per_annotation_spatial") or [])],
        "populated_layer": spat.get("populated_layer"),
        "top_object_count": feat.get("long_top_object_count"),
        "bottom_object_count": feat.get("long_bottom_object_count"),
        "top_quantity": feat.get("top_quantity"),
        "bottom_quantity": feat.get("bottom_quantity"),
        "extra_object_count": feat.get("extra_object_count"),
        "unique_accepted_spec_count": feat.get("unique_accepted_spec_count"),
        "accepted_instance_count": feat.get("accepted_instance_count"),
        "accepted_matches_main": feat.get("accepted_matches_main"),
        "rejected_matching_populated": feat.get("rejected_matching_populated"),
        "quantity_shortfall_count": feat.get("quantity_shortfall_count"),
        "role_conflict_count": feat.get("role_conflict_count"),
        "diameter_conflict_count": feat.get("diameter_conflict_count"),
        "association": feat.get("association"),
        "longitudinal_coverage": d.get("longitudinal_coverage"),
        "role_gap_status": d.get("role_gap_status"),
        "role_gap_reason": d.get("role_gap_reason"),
        "annotation_xy_available": spat.get("annotation_xy_available"),
        "leader_geometry_available": spat.get("leader_geometry_available"),
        "physical_bar_geometry_available": spat.get("physical_bar_geometry_available"),
        "tip_layer_votes": spat.get("tip_layer_votes"),
        "max_repeat_dy": spat.get("max_repeat_dy"),
        "min_object_distance": spat.get("min_object_distance"),
        "context_status": d.get("context_status"),
        "evidence_codes": d.get("context_evidence_codes"),
        "observed_decision": d.get("observed_decision"),
        "hypothetical_decision": d.get("hypothetical_decision"),
    }


def run_phase_p265(
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
        _log("  LIVE mode requested; P2.6.5 still executes REPLAY_P261_CACHED only.")
        mode = MODE_REPLAY

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  GATE_VERSION: {GATE_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {mode}")
    _log("  Observed routing = P2.6.4 (unchanged). Spatial layer is shadow-only.")

    unit = {"success": True, "passed": 0, "total": 0, "skipped": not run_tests}
    unit_path = out_root / "unit_tests.json"
    if run_tests:
        unit = run_unit_tests()
        _dump(unit_path, unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.5 unit tests failed: {failed}")
    elif unit_path.exists():
        try:
            unit = json.loads(unit_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.5 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.5 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "fingerprints_before.json", before)

    regions, sample_summary = load_frozen_manifest(v10)
    frozen_candidates = load_frozen_candidates(v10)
    _log(f"  frozen sample {len(regions)} beams seed={sample_summary.get('seed')}")

    own_cache: Dict[str, Dict[str, Any]] = {}
    r13_cache: Dict[str, Dict[str, Any]] = {}
    scoped_cache: Dict[str, Dict[str, Any]] = {}
    decisions: list = []
    for row in regions:
        set_key = row["set_key"]
        beam_id = row["beam_id"]
        if set_key not in own_cache:
            own_cache[set_key] = load_ownership(v10, set_key).get("by_beam") or {}
            r13_cache[set_key] = load_r13_index(v10, set_key)
            scoped_cache[set_key] = load_beam_scoped_index(v10, set_key)
        rec = own_cache[set_key].get(beam_id) or {}
        model = r13_cache[set_key].get(beam_id)
        scoped = scoped_cache[set_key].get(beam_id) or {}
        decision = build_shadow_record(
            beam_id=beam_id,
            region_id=row.get("region_id") or f"P261::{set_key}::{beam_id}",
            rec=rec,
            model=model,
            scoped=scoped,
            set_key=set_key,
            source_set=row.get("source_set") or "",
            crop_path=row.get("crop_path"),
        )
        decision["eval_stratum"] = row.get("stratum")
        decisions.append(decision)
        _log(
            f"  {set_key}/{beam_id} [{row.get('stratum')}] "
            f"p264={decision['observed_decision']} ctx={decision.get('context_status')} "
            f"cov={decision.get('longitudinal_coverage')}"
        )

    hypo = apply_hypothetical(decisions)
    for obs, h in zip(decisions, hypo):
        obs["hypothetical_decision"] = h.get("hypothetical_decision")
        obs["hypothetical_reason"] = h.get("hypothetical_reason")

    gated, replay_summary = apply_gate_to_frozen(
        decisions=decisions, frozen_candidates=frozen_candidates
    )
    hypo_gated, hypo_replay = apply_gate_to_frozen(
        decisions=hypo, frozen_candidates=frozen_candidates
    )
    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "p264_artefacts_unchanged": fp_cmp.get("unchanged"),
        "p263_artefacts_unchanged": fp_cmp.get("unchanged"),
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
    hypo_eval = evaluate_replay(
        decisions=hypo,
        baseline_candidates=frozen_candidates,
        gated_candidates=hypo_gated,
        firewall_ok=bool(fw.get("ok")),
        leakage_ok=bool(leak.get("ok")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        hypothetical_metrics=None,
    )
    ev["recommendation"] = classify_gate(
        ev["metrics"],
        firewall_ok=bool(fw.get("ok")),
        leakage_ok=bool(leak.get("ok")),
        fingerprints_ok=bool(fp_cmp.get("unchanged")),
        hypothetical=hypo_eval["metrics"],
    )
    evidence = write_evidence(
        evidence_root=out_root / "evidence",
        decisions=decisions,
        gated_candidates=gated,
        baseline_candidates=frozen_candidates,
        false_skips=ev["false_skips"],
        false_calls=ev["false_calls"],
    )
    feature_rows = [_feature_row(d) for d in decisions]
    sens = sensitivity_analysis(decisions)

    gate_manifest = {
        "frozen": True,
        "resampled": False,
        "sample": sample_summary,
        "replay": replay_summary,
        "hypothetical_replay": hypo_replay,
        "gate_version": GATE_VERSION,
        "observed_routing": "P264_UNCHANGED",
        "cached_source": "PhaseP261_stratified_vision_candidate_recovery",
        "live_vision": False,
    }
    _dump(out_root / "gate_manifest.json", gate_manifest)
    _dump(out_root / "gate_decisions.json", decisions)
    _dump(out_root / "hypothetical_decisions.json", hypo)
    _dump(out_root / "false_skips.json", ev["false_skips"])
    _dump(out_root / "false_calls.json", ev["false_calls"])
    _dump(out_root / "metrics.json", ev["metrics"])
    _dump(out_root / "hypothetical_metrics.json", hypo_eval["metrics"])
    _dump(out_root / "gated_candidates.json", gated)
    _dump(out_root / "control_cases.json", ev.get("control_cases") or [])
    _dump(out_root / "features.json", feature_rows)
    _dump(out_root / "sensitivity.json", sens)

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
        "hypothetical_metrics": hypo_eval["metrics"],
        "recommendation": ev["recommendation"],
        "false_skips": ev["false_skips"],
        "false_calls": ev["false_calls"],
        "control_cases": ev.get("control_cases") or [],
        "feature_rows": feature_rows,
        "sensitivity": sens,
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
    om = ev["metrics"]
    hm = hypo_eval["metrics"]
    _log(
        f"  observed CALL={om.get('CALL_BEAMS')} SKIP={om.get('SKIP_BEAMS')} "
        f"ctx skip/call/amb="
        f"{om.get('CONTEXT_SUPPORTS_SKIP')}/{om.get('CONTEXT_SUPPORTS_CALL')}/{om.get('CONTEXT_AMBIGUOUS')}"
    )
    _log(
        f"  hypothetical CALL={hm.get('CALL_BEAMS')} SKIP={hm.get('SKIP_BEAMS')} "
        f"FS={hm.get('FALSE_SKIPS')} TR={hm.get('GATED_TRUE_RECOVERIES')}"
    )
    _log(f"  decision={result.get('decision')} strength={result.get('strength')}")
    return result


__all__ = ["run_phase_p265"]
