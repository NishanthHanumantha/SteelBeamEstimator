"""Deterministic stratified sampling. Fixed seed. No GT / estimator access."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .config import PER_STRATUM, SAMPLE_SEED, SET_KEYS, STRATA, TARGET_BEAMS
from .features import feature_row
from .set_artefacts import crop_path, load_ownership, load_r13_index
from .stratifier import attach_strata


def score_universe(*, version10_root: Path) -> List[Dict[str, Any]]:
    v10 = Path(version10_root)
    rows: List[Dict[str, Any]] = []
    for set_key in SET_KEYS:
        own = load_ownership(v10, set_key)
        r13 = load_r13_index(v10, set_key)
        for beam_id, rec in sorted((own.get("by_beam") or {}).items()):
            crop = crop_path(v10, set_key, beam_id)
            rows.append(
                feature_row(
                    set_key=set_key,
                    beam_id=beam_id,
                    rec=rec,
                    model=r13.get(beam_id),
                    crop_exists=crop.exists(),
                    crop_path=str(crop) if crop.exists() else None,
                )
            )
    return attach_strata(rows)


def _pick_stratum(
    pool: List[Dict[str, Any]],
    *,
    n: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    by_set: Dict[str, List[Dict[str, Any]]] = {k: [] for k in SET_KEYS}
    for row in pool:
        by_set.setdefault(row["set_key"], []).append(row)
    for key in SET_KEYS:
        by_set[key].sort(key=lambda r: r["beam_id"])
        rng.shuffle(by_set[key])
    quota = n // len(SET_KEYS)
    remainder = n - quota * len(SET_KEYS)
    picked: List[Dict[str, Any]] = []
    leftover: List[Dict[str, Any]] = []
    for i, key in enumerate(SET_KEYS):
        take_n = quota + (1 if i < remainder else 0)
        chunk = by_set[key]
        picked.extend(chunk[:take_n])
        leftover.extend(chunk[take_n:])
    leftover.sort(key=lambda r: (r["set_key"], r["beam_id"]))
    rng.shuffle(leftover)
    while len(picked) < n and leftover:
        picked.append(leftover.pop(0))
    return picked[:n]


def sample_stratified(
    universe: List[Dict[str, Any]],
    *,
    seed: int = SAMPLE_SEED,
    per_stratum: int = PER_STRATUM,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    rng = random.Random(int(seed))
    eligible = [r for r in universe if r.get("has_crop")]
    selected: List[Dict[str, Any]] = []
    allocation: Dict[str, int] = {}
    available: Dict[str, int] = {}
    for stratum in STRATA:
        pool = [r for r in eligible if r.get("stratum") == stratum]
        available[stratum] = len(pool)
        picked = _pick_stratum(pool, n=per_stratum, rng=rng)
        allocation[stratum] = len(picked)
        for row in picked:
            rec = dict(row)
            rec["selection_reason"] = f"STRATIFIED_{stratum}_SEED_{seed}"
            rec["random_seed"] = seed
            selected.append(rec)
    selected.sort(key=lambda r: (STRATA.index(r["stratum"]), r["set_key"], r["beam_id"]))
    by_set: Dict[str, int] = {}
    for row in selected:
        by_set[row["set_key"]] = by_set.get(row["set_key"], 0) + 1
    summary = {
        "seed": seed,
        "target_beams": TARGET_BEAMS,
        "per_stratum_target": per_stratum,
        "selected": len(selected),
        "universe_scored": len(universe),
        "eligible_with_crop": len(eligible),
        "available_by_stratum": available,
        "selected_by_stratum": allocation,
        "selected_by_set": by_set,
        "gt_used_for_selection": False,
        "estimator_used_for_selection": False,
        "drawing_sets": list(SET_KEYS),
        "drawing_visibility": "UNSEEN",
        "note": "Fourth/Fifth/Sixth are QA.3.0 unseen sets. First Set (known) was not sampled.",
    }
    return selected, summary


def build_sample(*, version10_root: Path, seed: int = SAMPLE_SEED) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    universe = score_universe(version10_root=version10_root)
    selected, summary = sample_stratified(universe, seed=seed)
    summary["p26_overlap_in_sample"] = sum(1 for r in selected if r.get("p26_pilot_overlap"))
    return selected, summary


__all__ = ["build_sample", "sample_stratified", "score_universe"]
