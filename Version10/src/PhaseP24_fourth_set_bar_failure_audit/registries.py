"""
Build GT and model bar registries + Excel-level matching.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .qa2a_bootstrap import load_matchers


def build_registries_and_matches(
    engine_root: Path,
    estimator_excel: Path,
    model_excel: Path,
    drawing_set: str,
) -> Dict[str, Any]:
    WorkbookNormalizer, BeamMatcher, BarMatcher = load_matchers(engine_root)
    normalizer = WorkbookNormalizer()
    estimator = normalizer.normalize(Path(estimator_excel), "ESTIMATOR")
    model = normalizer.normalize(Path(model_excel), "MODEL")

    beam_matcher = BeamMatcher()
    bar_matcher = BarMatcher()
    beam_matching = beam_matcher.match(estimator, model)
    pairs = beam_matcher.matched_beam_pairs(estimator, model, beam_matching)
    unmatched_est = [
        b
        for b in estimator.beams
        if b.beam_id in (beam_matching.get("missing_ids") or [])
    ]
    bar_matching = bar_matcher.match_all(drawing_set, pairs, unmatched_est)

    gt_registry: List[Dict[str, Any]] = []
    for beam in sorted(estimator.beams, key=lambda b: b.beam_id):
        for i, bar in enumerate(beam.bars):
            gt_id = f"GT::{beam.beam_id}::{i:04d}::{bar.bar_role}"
            gt_registry.append(
                {
                    "gt_bar_id": gt_id,
                    "drawing_set": drawing_set,
                    "beam_id": beam.beam_id,
                    "bar_index": i,
                    "bar_role": bar.bar_role,
                    "diameter": bar.diameter,
                    "quantity": bar.quantity,
                    "cut_length": bar.cut_length,
                    "steel_weight": bar.steel_weight,
                    "shape": bar.shape,
                    "remarks": bar.remarks,
                    "source_description": bar.source_description,
                    "source_row": bar.source_row,
                    "source_sheet": beam.source_sheet,
                    "original_wording": bar.source_description or bar.remarks or "",
                    "stage0": "GT_CONFIRMED",
                }
            )

    model_registry: List[Dict[str, Any]] = []
    for beam in sorted(model.beams, key=lambda b: b.beam_id):
        for i, bar in enumerate(beam.bars):
            mid = f"MOD::{beam.beam_id}::{i:04d}::{bar.bar_role}"
            model_registry.append(
                {
                    "model_bar_id": mid,
                    "beam_id": beam.beam_id,
                    "bar_index": i,
                    "bar_role": bar.bar_role,
                    "diameter": bar.diameter,
                    "quantity": bar.quantity,
                    "cut_length": bar.cut_length,
                    "steel_weight": bar.steel_weight,
                    "source_description": bar.source_description,
                    "engineering_object_id": "UNKNOWN",
                    "vb1_object_id": mid,
                    "ownership_state": "UNKNOWN",
                    "annotation_id": "UNKNOWN",
                    "leader_id": "UNKNOWN",
                    "physical_bar_id": "UNKNOWN",
                    "entity_handle": "UNKNOWN",
                }
            )

    # BarMatcher walks estimator bars in beam list order; pair 1:1 with GT registry.
    gt_by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for g in gt_registry:
        gt_by_beam.setdefault(g["beam_id"], []).append(g)

    match_rows_gt: List[Dict[str, Any]] = []
    extras: List[Dict[str, Any]] = []
    cursor: Dict[str, int] = {bid: 0 for bid in gt_by_beam}
    for row in bar_matching.get("rows") or []:
        status = row.get("status")
        if status in ("EXTRA", "ACCEPTABLE_EXTRA"):
            extras.append(row)
            continue
        bid = row.get("beam_id")
        cands = gt_by_beam.get(bid) or []
        idx = cursor.get(bid, 0)
        if idx < len(cands):
            chosen = cands[idx]
            cursor[bid] = idx + 1
            match_rows_gt.append({**row, "gt_bar_id": chosen["gt_bar_id"]})
        else:
            match_rows_gt.append({**row, "gt_bar_id": "UNKNOWN"})

    return {
        "estimator": estimator,
        "model": model,
        "beam_matching": beam_matching,
        "bar_matching": bar_matching,
        "gt_registry": gt_registry,
        "model_registry": model_registry,
        "match_rows": match_rows_gt,
        "extra_rows": extras,
        "pairs": [(a.beam_id, b.beam_id) for a, b in pairs],
        "unmatched_est_beam_ids": [b.beam_id for b in unmatched_est],
    }
