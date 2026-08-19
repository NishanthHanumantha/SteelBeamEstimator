"""Compare expected vs detected group inventories. Evaluation-only matching."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import (
    ASSOC_AMBIGUOUS,
    ASSOC_CORRECT,
    ASSOC_INCORRECT,
    ASSOC_UNGROUPED,
    ERR_MERGED,
    ERR_MISSED,
    ERR_SPLIT,
    ERR_SPURIOUS,
    ERR_STIRRUP_MIX,
    ERR_WRONG_COUNT,
    ERR_WRONG_LAYER,
    ERR_WRONG_ROLE,
    ERR_WRONG_SPEC,
    ERR_WRONG_ZONE,
    FAMILY_LONGITUDINAL,
    FAMILY_STIRRUP,
    PRIMARY_FAMILIES,
    UNKNOWN,
    ZONE_UNKNOWN,
)
from .group_model import identity_key, spec_layer_key


def _primary(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [g for g in groups if str(g.get("family")) in PRIMARY_FAMILIES]


def _index(groups: List[Dict[str, Any]]) -> Dict[tuple, List[Dict[str, Any]]]:
    out: Dict[tuple, List[Dict[str, Any]]] = {}
    for g in groups:
        key = identity_key(g)
        out.setdefault(key, []).append(g)
    return out


def apply_overlay(expected: List[Dict[str, Any]], overlay: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not overlay:
        return list(expected)
    extra = list(overlay.get("overlay_groups") or [])
    if not extra:
        return list(expected)
    have = {identity_key(g) for g in expected}
    merged = list(expected)
    beam_id = str((expected[0].get("beam_id") if expected else overlay.get("beam_id")) or "")
    from .identity import assign_group_ids

    for row in extra:
        rec = dict(row)
        rec.setdefault("beam_id", beam_id)
        rec.setdefault("family", FAMILY_LONGITUDINAL)
        rec.setdefault("provenance", rec.get("provenance") or "CONTROL_OVERLAY")
        rec.setdefault("evidence_quality", "CONTROL")
        rec.setdefault("confidence", 0.6)
        rec.setdefault("annotation_ids", [])
        rec.setdefault("leader_ids", [])
        rec.setdefault("spacing", UNKNOWN)
        rec.setdefault("zone", rec.get("zone") or UNKNOWN)
        rec.setdefault("spatial_extent", rec.get("spatial_extent") or UNKNOWN)
        rec.setdefault("source_layer", UNKNOWN)
        rec.setdefault("deterministic_identity", "CONTROL_OVERLAY")
        rec.setdefault("start_position", UNKNOWN)
        rec.setdefault("end_position", UNKNOWN)
        rec.setdefault("phase", "P2.6.9")
        rec.setdefault("group_id", "")
        if identity_key(rec) not in have:
            merged.append(rec)
            have.add(identity_key(rec))
    return assign_group_ids(merged, beam_id=beam_id)


def compare_inventories(
    *,
    expected: List[Dict[str, Any]],
    detected: List[Dict[str, Any]],
) -> Dict[str, Any]:
    exp_p = _primary(expected)
    det_p = _primary(detected)
    exp_i = _index(exp_p)
    det_i = _index(det_p)
    matched: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []
    spurious: List[Dict[str, Any]] = []
    merged: List[Dict[str, Any]] = []
    split: List[Dict[str, Any]] = []
    errors: List[str] = []
    used_det: set = set()

    for key, exp_rows in exp_i.items():
        det_rows = det_i.get(key) or []
        if not det_rows:
            layer_hits = [
                d
                for d in det_p
                if spec_layer_key(d) == (key[0], key[1], key[3])
            ]
            spec_hits = [d for d in det_p if str(d.get("specification")) == key[3] and str(d.get("family")) == key[0]]
            if spec_hits and all(str(d.get("physical_layer")) != key[1] for d in spec_hits):
                errors.append(ERR_WRONG_LAYER)
            if layer_hits and all(str(d.get("reinforcement_role")) != key[2] for d in layer_hits):
                errors.append(ERR_WRONG_ROLE)
            if spec_hits and len(spec_hits) == 1 and len(exp_rows) >= 1:
                other_exp = [e for e in exp_p if str(e.get("specification")) == key[3] and identity_key(e) != key]
                if other_exp:
                    merged.append({"expected": [identity_key(e) for e in exp_rows + other_exp], "detected": [identity_key(spec_hits[0])]})
                    errors.append(ERR_MERGED)
            for row in exp_rows:
                missing.append(row)
                errors.append(ERR_MISSED)
            continue
        if len(det_rows) > len(exp_rows):
            split.append({"expected": [key], "detected_n": len(det_rows)})
            errors.append(ERR_SPLIT)
        pair_n = min(len(exp_rows), len(det_rows))
        for i in range(pair_n):
            e = exp_rows[i]
            d = det_rows[i]
            used_det.add(id(d))
            rec = {"expected": identity_key(e), "detected": identity_key(d), "status": "CORRECT_GROUP"}
            if str(e.get("physical_layer")) != str(d.get("physical_layer")):
                rec["status"] = ERR_WRONG_LAYER
                errors.append(ERR_WRONG_LAYER)
            if str(e.get("reinforcement_role")) not in (UNKNOWN, "") and str(d.get("reinforcement_role")) not in (UNKNOWN, ""):
                if str(e.get("reinforcement_role")) != str(d.get("reinforcement_role")):
                    rec["status"] = ERR_WRONG_ROLE
                    errors.append(ERR_WRONG_ROLE)
            if str(e.get("specification")) != str(d.get("specification")):
                rec["status"] = ERR_WRONG_SPEC
                errors.append(ERR_WRONG_SPEC)
            e_count, d_count = e.get("count"), d.get("count")
            if (
                str(e.get("family")) == FAMILY_LONGITUDINAL
                and isinstance(e_count, int)
                and isinstance(d_count, int)
                and e_count != d_count
            ):
                rec["count_error"] = True
                errors.append(ERR_WRONG_COUNT)
            e_zone, d_zone = str(e.get("zone") or ZONE_UNKNOWN), str(d.get("zone") or ZONE_UNKNOWN)
            if e_zone not in (UNKNOWN, ZONE_UNKNOWN) and d_zone not in (UNKNOWN, ZONE_UNKNOWN) and e_zone != d_zone:
                if not (e_zone in ("SUPPORT_ZONE", "BOTH_SUPPORTS") and d_zone in ("SUPPORT_ZONE", "BOTH_SUPPORTS", "LEFT_SUPPORT", "RIGHT_SUPPORT")):
                    errors.append(ERR_WRONG_ZONE)
            if str(e.get("family")) == FAMILY_STIRRUP and str(d.get("family")) == FAMILY_LONGITUDINAL:
                errors.append(ERR_STIRRUP_MIX)
                rec["status"] = ERR_STIRRUP_MIX
            if str(e.get("family")) == FAMILY_LONGITUDINAL and str(d.get("family")) == FAMILY_STIRRUP:
                errors.append(ERR_STIRRUP_MIX)
                rec["status"] = ERR_STIRRUP_MIX
            matched.append(rec)
        for i in range(pair_n, len(exp_rows)):
            missing.append(exp_rows[i])
            errors.append(ERR_MISSED)

    for d in det_p:
        if id(d) in used_det:
            continue
        key = identity_key(d)
        if key not in exp_i:
            spurious.append(d)
            errors.append(ERR_SPURIOUS)

    correct = sum(1 for m in matched if m.get("status") == "CORRECT_GROUP")
    return {
        "expected_group_count": len(exp_p),
        "detected_group_count": len(det_p),
        "correctly_interpreted_groups": correct,
        "missing_groups": [identity_key(g) for g in missing],
        "spurious_groups": [identity_key(g) for g in spurious],
        "merged_groups": merged,
        "split_groups": split,
        "matched": matched,
        "errors": list(dict.fromkeys(errors)),
        "error_counts": {code: errors.count(code) for code in dict.fromkeys(errors)},
        "expected": [identity_key(g) for g in exp_p],
        "detected": [identity_key(g) for g in det_p],
    }


def associate_annotations(
    *,
    annotations: List[Dict[str, Any]],
    detected: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    from .drawing_groups import annotation_to_piece

    out: List[Dict[str, Any]] = []
    for ann in annotations:
        beam_id = str(ann.get("beam_id") or (detected[0].get("beam_id") if detected else "") or "")
        piece = annotation_to_piece(ann, beam_id=beam_id)
        if piece is None:
            out.append(
                {
                    "annotation_id": ann.get("annotation_id"),
                    "parsed_specification": UNKNOWN,
                    "assigned_group_id": None,
                    "assigned_layer": UNKNOWN,
                    "assigned_role": UNKNOWN,
                    "association_status": ASSOC_UNGROUPED,
                    "association_confidence": 0.0,
                }
            )
            continue
        hits = [d for d in detected if identity_key(d) == identity_key(piece)]
        if not hits:
            hits = [d for d in detected if spec_layer_key(d) == spec_layer_key(piece)]
        status = ASSOC_UNGROUPED
        assigned = None
        if len(hits) == 1:
            assigned = hits[0]
            status = ASSOC_CORRECT if identity_key(hits[0]) == identity_key(piece) else ASSOC_INCORRECT
        elif len(hits) > 1:
            status = ASSOC_AMBIGUOUS
            assigned = hits[0]
        exp_hits = [e for e in expected if identity_key(e) == identity_key(piece)]
        if assigned is None and exp_hits:
            status = ASSOC_UNGROUPED
        out.append(
            {
                "annotation_id": ann.get("annotation_id"),
                "parsed_specification": piece.get("specification"),
                "assigned_group_id": None if assigned is None else assigned.get("group_id"),
                "assigned_layer": None if assigned is None else assigned.get("physical_layer"),
                "assigned_role": None if assigned is None else assigned.get("reinforcement_role"),
                "spatial_leader_evidence": {
                    "position_zone": ann.get("position_zone") or UNKNOWN,
                    "role": ann.get("role") or UNKNOWN,
                },
                "association_status": status,
                "association_confidence": 0.8 if status == ASSOC_CORRECT else (0.4 if assigned else 0.0),
            }
        )
    return out


__all__ = ["apply_overlay", "associate_annotations", "compare_inventories"]
