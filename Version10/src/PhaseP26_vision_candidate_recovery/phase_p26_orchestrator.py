"""
P2.6 orchestrator — Vision Candidate Recovery Pilot.

Isolated shadow pipeline. Deterministic production remains sole authority.
GT is loaded only after Vision candidate generation.
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

from PhaseP258_controlled_vision_field_repair.r13_overlay import load_r13  # noqa: E402
from PhaseP257_unseen_drawing_controlled_vision_validation.regression import (  # noqa: E402
    fifth_set_production_paths,
)

from .candidate_gap_analyzer import select_pilot_regions  # noqa: E402
from .config import (  # noqa: E402
    CLAUDE_MODEL,
    ENGINEERING_CHANGES,
    MODE,
    MODE_CACHE_ONLY,
    MODE_LIVE_API,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PILOT_SET,
    PILOT_TARGET_REGIONS,
    PRODUCTION_WRITE,
    SCOPE,
    TEMPERATURE,
)
from .deterministic_comparator import apply_comparison  # noqa: E402
from .evidence_store import write_evidence  # noqa: E402
from .ground_truth_matcher import (  # noqa: E402
    evaluate_candidates,
    load_gt_universe,
    missed_count_for_beams,
)
from .metrics import classify_pilot, compute_metrics  # noqa: E402
from .region_builder import build_region_package  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .report_builder import write_reports  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402
from .vision_observer import observe_region  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ownership(v10: Path) -> Dict[str, Any]:
    p = (
        v10
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / "Fifth_Set_Drawings"
        / "EngineeringSummaries"
        / "BeamOwnership.json"
    )
    return _load_json(p)


def _strip_images(region: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(region)
    images = []
    for im in region.get("images") or []:
        images.append(
            {
                "role": im.get("role"),
                "path": im.get("path"),
                "sha256": im.get("sha256"),
                "size_bytes": im.get("size_bytes"),
                "media_type": im.get("media_type"),
            }
        )
    out["images"] = images
    return out


def run_phase_p26(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_LIVE_API,
    target_regions: int = PILOT_TARGET_REGIONS,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (
        out_root,
        out_root / "pilot",
        out_root / "candidates",
        out_root / "evidence",
        out_root / "cache",
        out_root / "reports",
        out_root / "config",
    ):
        d.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        print(msg, flush=True)

    if mode not in (MODE_LIVE_API, MODE_CACHE_ONLY):
        raise ValueError(f"unsupported mode {mode}")

    _log(f"[{PHASE_ID}] {PHASE_NAME}")
    _log(f"  MODEL_VERSION: {MODEL_VERSION}")
    _log(f"  SCOPE: {SCOPE} MODE: {mode}")
    _log(f"  ENGINEERING_CHANGES: {ENGINEERING_CHANGES}")
    _log(f"  production_write={PRODUCTION_WRITE} vision={CLAUDE_MODEL} temp={TEMPERATURE}")
    _log(f"  output={out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "pilot" / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "pilot" / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "pilot" / "fingerprints_before.json", before)

    selected, sel_summary = select_pilot_regions(version10_root=v10, target=target_regions)
    _dump(out_root / "pilot" / "selected_regions.json", {"summary": sel_summary, "regions": selected})
    _log(f"  selected {len(selected)} regions from {sel_summary.get('eligible_with_crop')} eligible")

    own = _ownership(v10).get("by_beam") or {}
    r13_path = fifth_set_production_paths(v10).get("fifth_r13_models")
    r13_doc = load_r13(r13_path) if r13_path and Path(r13_path).exists() else {"models": []}
    r13_index = {m.get("beam_id"): m for m in (r13_doc.get("models") or []) if isinstance(m, dict)}

    observations: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []
    regions_by_id: Dict[str, Dict[str, Any]] = {}
    cache_root = out_root / "cache"

    for row in selected:
        beam_id = row["beam_id"]
        region_id = row["region_id"]
        pkg = build_region_package(
            beam_id=beam_id,
            region_id=region_id,
            ownership_rec=own.get(beam_id) or {},
            r13_model=r13_index.get(beam_id),
            crop_path=Path(row["crop_path"]),
            gap_reasons=row.get("gap_reasons") or [],
        )
        regions_by_id[region_id] = pkg
        _dump(out_root / "pilot" / "regions" / f"{beam_id}.json", _strip_images(pkg))
        obs = observe_region(
            version10_root=v10,
            region=pkg,
            cache_root=cache_root,
            mode=mode,
        )
        compared = apply_comparison(obs.get("candidates") or [], r13_model=r13_index.get(beam_id))
        obs["candidates"] = compared
        slim = dict(obs)
        slim.pop("raw_response", None)
        observations.append(slim)
        _dump(out_root / "pilot" / "observations" / f"{beam_id}.json", slim)
        for cand in compared:
            cand["gap_reasons"] = row.get("gap_reasons") or []
            cand["region_bbox"] = pkg.get("region_bbox")
            candidates.append(cand)
            _dump(
                out_root / "candidates" / f"{str(cand['candidate_id']).replace('::', '__')}.json",
                cand,
            )
        _log(
            f"  {beam_id}: cache_hit={obs.get('cache_hit')} api_ok={obs.get('api_ok')} "
            f"cands={len(compared)} error={obs.get('error')}"
        )

    _dump(out_root / "pilot" / "observations.json", observations)

    # GT evaluation ONLY after Vision candidate generation.
    universe = load_gt_universe(v10)
    evaluated = evaluate_candidates(candidates, universe=universe)
    _dump(out_root / "candidates" / "all_candidates.json", evaluated)
    beam_ids = [r["beam_id"] for r in selected]
    missed = missed_count_for_beams(universe, beam_ids)
    metrics = compute_metrics(
        observations=observations,
        candidates=evaluated,
        missed_gt_on_pilot=missed,
    )
    recommendation = classify_pilot(metrics)
    evidence = write_evidence(
        evidence_root=out_root / "evidence",
        candidates=evaluated,
        regions_by_id=regions_by_id,
    )

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    _dump(out_root / "pilot" / "fingerprints_after.json", after)
    _dump(out_root / "pilot" / "fingerprint_compare.json", {"unchanged": fp_cmp.get("unchanged"), "changed_keys": fp_cmp.get("changed_keys")})

    production = {
        "production_mutation_count": 0 if fp_cmp.get("unchanged") else len(fp_cmp.get("changed_keys") or []),
        "fingerprints_ok": fp_cmp.get("unchanged"),
        "changed_keys": fp_cmp.get("changed_keys") or [],
        "steel_unchanged": True,
        "bbs_unchanged": True,
        "excel_unchanged": True,
        "r13_unchanged": True,
        "si1_unchanged": True,
    }
    if not fp_cmp.get("unchanged"):
        production["steel_unchanged"] = "fifth_model_excel" not in (fp_cmp.get("changed_keys") or [])
        production["bbs_unchanged"] = "fifth_bbs_summary" not in (fp_cmp.get("changed_keys") or [])
        production["excel_unchanged"] = "fifth_model_excel" not in (fp_cmp.get("changed_keys") or [])
        production["r13_unchanged"] = "fifth_r13_models" not in (fp_cmp.get("changed_keys") or [])

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "pilot_set": PILOT_SET,
        "mode": mode,
        "production_write": PRODUCTION_WRITE,
        "engineering_changes": ENGINEERING_CHANGES,
        "pass_fail": "PASS" if unit.get("success") and fw.get("ok") and leak.get("ok") and fp_cmp.get("unchanged") else "FAIL",
        "output_root": str(out_root),
        "selection": sel_summary,
        "metrics": metrics,
        "recommendation": recommendation,
        "evidence": evidence,
        "unit_tests": unit,
        "firewall": fw,
        "leakage": leak,
        "production": production,
        "gt_evaluation": {
            "estimator_path": universe.get("estimator_path"),
            "model_path": universe.get("model_path"),
            "gt_used_at_runtime": False,
            "gt_used_for_selection": False,
        },
        "decision": recommendation.get("decision"),
        "strength": recommendation.get("strength"),
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    _dump(out_root / "pilot" / "result.json", result)
    _log(f"  TRUE_RECOVERIES={metrics.get('true_recoveries')} precision={metrics.get('VISION_CANDIDATE_PRECISION')}")
    _log(f"  decision={recommendation.get('decision')} strength={recommendation.get('strength')}")
    return result


__all__ = ["run_phase_p26"]
