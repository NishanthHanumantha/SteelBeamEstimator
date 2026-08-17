"""
P2.6.1 orchestrator — Stratified Vision Candidate Recovery Benchmark.

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

from .config import (  # noqa: E402
    CLAUDE_MODEL,
    ENGINEERING_CHANGES,
    MAX_LIVE_CALLS,
    MODE,
    MODE_CACHE_ONLY,
    MODE_LIVE_API,
    MODEL_VERSION,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
    SAMPLE_SEED,
    SCOPE,
    SET_KEYS,
    TEMPERATURE,
)
from .evidence_store import write_evidence  # noqa: E402
from .ground_truth_matcher import (  # noqa: E402
    apply_comparison,
    evaluate_candidates,
    load_gt_universe,
    missed_count_for_keys,
    universe_key,
)
from .metrics import classify_benchmark, compute_metrics  # noqa: E402
from .region_builder import build_region_package  # noqa: E402
from .regression import (  # noqa: E402
    capture_fingerprints,
    compare_fingerprints,
    fingerprint_paths,
    firewall_check,
    runtime_leakage_scan,
)
from .report_builder import write_reports  # noqa: E402
from .sampler import build_sample  # noqa: E402
from .set_artefacts import load_ownership, load_r13_index  # noqa: E402
from .unit_tests import run_unit_tests  # noqa: E402
from .vision_observer import observe_region  # noqa: E402


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


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


def run_phase_p261(
    *,
    version10_root: Optional[Path] = None,
    output_root: Optional[Path] = None,
    run_tests: bool = True,
    mode: str = MODE_LIVE_API,
    max_live_calls: int = MAX_LIVE_CALLS,
    seed: int = SAMPLE_SEED,
) -> Dict[str, Any]:
    v10 = Path(version10_root or _V10).resolve()
    out_root = Path(output_root or (v10 / "data" / "output" / OUTPUT_DIRNAME)).resolve()
    for d in (
        out_root,
        out_root / "benchmark",
        out_root / "candidates",
        out_root / "evidence",
        out_root / "cache",
        out_root / "reports",
        out_root / "config",
        out_root / "sampling",
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
    _log(f"  max_live_calls={max_live_calls} seed={seed}")
    _log(f"  output={out_root}")

    unit = {"success": True, "passed": 0, "total": 0}
    if run_tests:
        unit = run_unit_tests()
        _dump(out_root / "benchmark" / "unit_tests.json", unit)
        if not unit.get("success"):
            failed = [r for r in unit.get("results") or [] if not r.get("pass")]
            raise RuntimeError(f"P2.6.1 unit tests failed: {failed}")

    fw = firewall_check(v10)
    leak = runtime_leakage_scan(Path(__file__).resolve().parent)
    _dump(out_root / "benchmark" / "firewall.json", {"firewall": fw, "leakage": leak})
    if not fw.get("ok"):
        raise RuntimeError(f"P2.6.1 firewall offenders: {fw.get('offenders')}")
    if not leak.get("ok"):
        raise RuntimeError(f"P2.6.1 runtime leakage: {leak.get('hits')}")

    fp_paths = fingerprint_paths(v10, {})
    before = capture_fingerprints(fp_paths)
    _dump(out_root / "benchmark" / "fingerprints_before.json", before)

    selected, sel_summary = build_sample(version10_root=v10, seed=seed)
    _dump(
        out_root / "sampling" / "manifest.json",
        {
            "summary": sel_summary,
            "regions": [
                {
                    "beam_id": r["beam_id"],
                    "source_set": r["source_set"],
                    "source_drawing": r["source_drawing"],
                    "stratum": r["stratum"],
                    "selection_features": r.get("features"),
                    "selection_reason": r.get("selection_reason"),
                    "random_seed": r.get("random_seed"),
                    "set_key": r["set_key"],
                    "region_id": r["region_id"],
                    "crop_path": r.get("crop_path"),
                    "drawing_visibility": r.get("drawing_visibility"),
                    "p26_pilot_overlap": r.get("p26_pilot_overlap"),
                    "score": r.get("score"),
                }
                for r in selected
            ],
        },
    )
    _log(
        f"  selected {len(selected)} beams "
        f"strata={sel_summary.get('selected_by_stratum')} "
        f"sets={sel_summary.get('selected_by_set')}"
    )

    own_by_set = {k: load_ownership(v10, k) for k in SET_KEYS}
    r13_by_set = {k: load_r13_index(v10, k) for k in SET_KEYS}

    observations: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []
    regions_by_id: Dict[str, Dict[str, Any]] = {}
    cache_root = out_root / "cache"
    live_used = 0
    partial = False

    for row in selected:
        beam_id = row["beam_id"]
        region_id = row["region_id"]
        set_key = row["set_key"]
        own = (own_by_set.get(set_key) or {}).get("by_beam") or {}
        r13_index = r13_by_set.get(set_key) or {}
        pkg = build_region_package(
            beam_id=beam_id,
            region_id=region_id,
            source_set=row["source_set"],
            ownership_rec=own.get(beam_id) or {},
            crop_path=Path(row["crop_path"] or ""),
        )
        regions_by_id[region_id] = pkg
        _dump(
            out_root / "benchmark" / "regions" / f"{set_key}_{beam_id}.json",
            _strip_images(pkg),
        )
        obs = observe_region(
            version10_root=v10,
            region=pkg,
            cache_root=cache_root,
            mode=mode,
            live_calls_used=live_used,
            max_live_calls=max_live_calls,
        )
        if obs.get("live_call"):
            live_used += 1
        if obs.get("budget_stop"):
            partial = True
        compared = apply_comparison(obs.get("candidates") or [], r13_model=r13_index.get(beam_id))
        obs["candidates"] = compared
        obs["stratum"] = row["stratum"]
        obs["set_key"] = set_key
        slim = dict(obs)
        slim.pop("raw_response", None)
        observations.append(slim)
        _dump(out_root / "benchmark" / "observations" / f"{set_key}_{beam_id}.json", slim)
        for cand in compared:
            cand["stratum"] = row["stratum"]
            cand["set_key"] = set_key
            cand["drawing_visibility"] = row.get("drawing_visibility") or "UNSEEN"
            cand["p26_pilot_overlap"] = bool(row.get("p26_pilot_overlap"))
            cand["region_bbox"] = pkg.get("region_bbox")
            cand["crop_hash"] = pkg.get("crop_hash")
            cand["crop_width"] = pkg.get("crop_width")
            cand["crop_height"] = pkg.get("crop_height")
            cand["crop_source"] = pkg.get("crop_source")
            candidates.append(cand)
            _dump(
                out_root / "candidates" / f"{str(cand['candidate_id']).replace('::', '__')}.json",
                cand,
            )
        _log(
            f"  {set_key}/{beam_id} [{row['stratum']}]: "
            f"cache_hit={obs.get('cache_hit')} live={obs.get('live_call')} "
            f"cands={len(compared)} error={obs.get('error')}"
        )
        if obs.get("budget_stop"):
            _log("  LIVE_CALL_BUDGET_REACHED — remaining regions cache-only / skipped")

    _dump(out_root / "benchmark" / "observations.json", observations)

    # GT evaluation ONLY after Vision candidate generation.
    universe = load_gt_universe(v10)
    sampled_keys = [universe_key(r["set_key"], r["beam_id"]) for r in selected]
    missed_overall = missed_count_for_keys(universe, sampled_keys)
    missed_by_stratum: Dict[str, int] = {}
    missed_by_set: Dict[str, int] = {}
    for row in selected:
        uk = universe_key(row["set_key"], row["beam_id"])
        n = missed_count_for_keys(universe, [uk])
        missed_by_stratum[row["stratum"]] = missed_by_stratum.get(row["stratum"], 0) + n
        missed_by_set[row["source_set"]] = missed_by_set.get(row["source_set"], 0) + n

    evaluated = evaluate_candidates(candidates, universe=universe)
    _dump(out_root / "candidates" / "all_candidates.json", evaluated)
    metrics = compute_metrics(
        observations=observations,
        candidates=evaluated,
        missed_gt_overall=missed_overall,
        missed_by_stratum=missed_by_stratum,
        missed_by_set=missed_by_set,
    )
    evidence = write_evidence(
        evidence_root=out_root / "evidence",
        candidates=evaluated,
        regions_by_id=regions_by_id,
    )

    after = capture_fingerprints(fp_paths)
    fp_cmp = compare_fingerprints(before, after)
    _dump(out_root / "benchmark" / "fingerprints_after.json", after)
    _dump(
        out_root / "benchmark" / "fingerprint_compare.json",
        {"unchanged": fp_cmp.get("unchanged"), "changed_keys": fp_cmp.get("changed_keys")},
    )

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
    changed = set(fp_cmp.get("changed_keys") or [])
    if changed:
        production["steel_unchanged"] = not any("model_excel" in k for k in changed)
        production["bbs_unchanged"] = not any("bbs_summary" in k for k in changed)
        production["excel_unchanged"] = not any("model_excel" in k for k in changed)
        production["r13_unchanged"] = not any("r13_models" in k for k in changed)

    recommendation = classify_benchmark(
        metrics,
        firewall_ok=bool(fw.get("ok")) and bool(fp_cmp.get("unchanged")),
        review_blocker_or_high=False,
    )

    review_path = out_root / "benchmark" / "independent_review.json"
    independent_review = {
        "status": "PENDING",
        "blocker": None,
        "high": None,
        "medium": None,
        "low": None,
    }
    if review_path.exists():
        try:
            independent_review = json.loads(review_path.read_text(encoding="utf-8"))
        except Exception:
            independent_review = independent_review

    result = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "scope": SCOPE,
        "mode": mode,
        "production_write": PRODUCTION_WRITE,
        "engineering_changes": ENGINEERING_CHANGES,
        "partial_execution": partial,
        "pass_fail": (
            "PASS"
            if unit.get("success") and fw.get("ok") and leak.get("ok") and fp_cmp.get("unchanged")
            else "FAIL"
        ),
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
            "paths": universe.get("paths"),
            "gt_used_at_runtime": False,
            "gt_used_for_selection": False,
        },
        "independent_review": independent_review,
        "decision": recommendation.get("decision"),
        "strength": recommendation.get("strength"),
    }
    paths = write_reports(out_root=out_root, result=result)
    result["report_paths"] = paths
    _dump(out_root / "benchmark" / "result.json", result)
    _log(
        f"  TRUE_RECOVERIES={metrics.get('TRUE_RECOVERIES')} "
        f"precision={metrics.get('VISION_CANDIDATE_PRECISION')} "
        f"partial={partial}"
    )
    _log(f"  decision={recommendation.get('decision')} strength={recommendation.get('strength')}")
    return result


__all__ = ["run_phase_p261"]
