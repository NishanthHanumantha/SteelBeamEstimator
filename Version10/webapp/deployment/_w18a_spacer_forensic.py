"""W.18A read-only spacer forensic dump and M.2 replay.

Does not mutate production data or calculation modules.
Writes JSON next to this file when run as __main__.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ENGINE = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version10\src")
L2_PATH = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w16_gn\galera_l2.json")
OUT_JSON = Path(
    r"C:\Users\nishanth.h\SteelBeamEstimator\Version10\webapp\deployment"
    r"\W18A_SPACER_FORENSIC_TRACE.json"
)
FOCUS = ("B1", "B10", "B23")
SPACER_SPACING_MM = 1000.0
PRIMARY_BEAMS = FOCUS

sys.path.insert(0, str(ENGINE))
from PhaseV9_spacer_rule.spacer_engine import (  # noqa: E402
    compute_spacers_for_beam,
    spacer_quantity,
    cut_length_mm as engine_cut_length_mm,
)
from PhaseV9_spacer_rule.spacer_models import (  # noqa: E402
    BeamSpacerInput,
    LongitudinalGroup,
)
from PhaseV9_spacer_rule.r13_injector import _bar_to_group  # noqa: E402


LONG_KEYS = (
    "top_main_bars",
    "top_extra_bars",
    "bottom_main_bars",
    "bottom_extra_bars",
)
BUCKET_ROLE = {
    "top_main_bars": "TOP_MAIN",
    "top_extra_bars": "TOP_EXTRA",
    "bottom_main_bars": "BOTTOM_MAIN",
    "bottom_extra_bars": "BOTTOM_EXTRA",
    "spacer_bars": "SPACER_BAR",
    "stirrups": "STIRRUP",
    "side_face_reinforcement": "SIDE_FACE_REINFORCEMENT",
}


def _role_from_bar_id(bar_id: str) -> Optional[str]:
    # R13-{beam}-{ROLE}-{hash}
    parts = str(bar_id or "").split("-")
    if len(parts) >= 4 and parts[0] == "R13":
        # beam ids can contain no extra dashes (B1, B10, B23)
        return parts[2] if len(parts) == 4 else "-".join(parts[2:-1])
    return None


class _BarProxy:
    """Minimal object so r13_injector._bar_to_group can be reused read-only."""

    def __init__(self, role: str, bar: Dict[str, Any], meta: Dict[str, Any]):
        self.bar_role = role
        self.engineering_metadata = meta
        self.diameter_mm = bar.get("diameter_mm")
        self.quantity = bar.get("quantity") or 1


def _l2_meta(bar: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild injector metadata from L.2 export fields (many M.2 keys are dropped)."""
    meta = dict(bar.get("engineering_metadata") or {})
    if not meta:
        meta = {}
    if bar.get("cut_length_mm") is not None:
        meta.setdefault("cut_length_mm", bar.get("cut_length_mm"))
    if bar.get("piece_type"):
        meta.setdefault("piece_type", bar.get("piece_type"))
    if bar.get("extent"):
        meta.setdefault("extent", bar.get("extent"))
    if bar.get("piece_start_mm") is not None:
        meta.setdefault("piece_start_mm", bar.get("piece_start_mm"))
    if bar.get("piece_end_mm") is not None:
        meta.setdefault("piece_end_mm", bar.get("piece_end_mm"))
    return meta


def _infer_extent_from_piece_type(
    piece_type: Optional[str], span_mm: Optional[float]
) -> Tuple[Optional[float], Optional[float], str]:
    pt = str(piece_type or "").upper()
    if not span_mm or span_mm <= 0:
        return None, None, "NOT_AVAILABLE_NO_SPAN"
    if pt in ("TOP_MAIN", "BOTTOM_MAIN", "CONTINUOUS_BAR"):
        return 0.0, float(span_mm), "inferred_from_piece_type_full_span"
    if pt.endswith("_LEFT") or pt in ("TOP_EXTRA_LEFT", "BOTTOM_EXTRA_LEFT"):
        return 0.0, float(span_mm) * 0.25, "inferred_from_piece_type_left_0.25L"
    if pt.endswith("_RIGHT") or pt in ("TOP_EXTRA_RIGHT", "BOTTOM_EXTRA_RIGHT"):
        return float(span_mm) * 0.75, float(span_mm), "inferred_from_piece_type_right_0.75L"
    return None, None, "NOT_AVAILABLE"


def _bar_fields(bar: Dict[str, Any], l2_key: str) -> Dict[str, Any]:
    keys_present = sorted(bar.keys())
    return {
        "l2_key": l2_key,
        "bar_id": bar.get("bar_id"),
        "bar_label": bar.get("bar_label"),
        "semantic_role": bar.get("semantic_role"),
        "bar_id_role_token": _role_from_bar_id(str(bar.get("bar_id") or "")),
        "bucket_role": BUCKET_ROLE.get(l2_key),
        "diameter_mm": bar.get("diameter_mm"),
        "quantity": bar.get("quantity"),
        "spacing_mm": bar.get("spacing_mm"),
        "cut_length_mm": bar.get("cut_length_mm"),
        "piece_type": bar.get("piece_type"),
        "shape_code": bar.get("shape_code"),
        "extent": bar.get("extent"),
        "continuity": bar.get("continuity"),
        "position_zone": bar.get("position_zone"),
        "support_zone": bar.get("support_zone"),
        "source_bar_id": bar.get("source_bar_id"),
        "source_pipeline_role": bar.get("source_pipeline_role"),
        "classification_evidence": bar.get("classification_evidence"),
        "classification_confidence": bar.get("classification_confidence"),
        "steel_grade": bar.get("steel_grade"),
        "engineering_metadata": bar.get("engineering_metadata") or {},
        "piece_start_mm": bar.get("piece_start_mm"),
        "piece_end_mm": bar.get("piece_end_mm"),
        "zone": bar.get("zone"),
        "source_phase": bar.get("source_phase"),
        "l2_keys_present": keys_present,
        "role_bucket_match": (
            _role_from_bar_id(str(bar.get("bar_id") or "")) == BUCKET_ROLE.get(l2_key)
            or str(bar.get("semantic_role") or "") == BUCKET_ROLE.get(l2_key)
        ),
    }


def _groups_from_l2(
    model: Dict[str, Any],
    role_source: str,
    infer_piece_extents: bool,
) -> Tuple[List[LongitudinalGroup], List[Dict[str, Any]]]:
    geom = model.get("geometry") or {}
    span = geom.get("clear_span_mm")
    try:
        span_f = float(span) if span is not None else None
    except (TypeError, ValueError):
        span_f = None
    groups: List[LongitudinalGroup] = []
    lineage: List[Dict[str, Any]] = []
    for key in LONG_KEYS:
        for bar in model.get(key) or []:
            if not isinstance(bar, dict):
                continue
            bid_role = _role_from_bar_id(str(bar.get("bar_id") or ""))
            sem = str(bar.get("semantic_role") or "").upper() or None
            bucket = BUCKET_ROLE.get(key)
            if role_source == "bar_id":
                role = bid_role or sem or bucket
            elif role_source == "semantic_role":
                role = sem or bid_role or bucket
            else:
                role = bucket
            meta = _l2_meta(bar)
            inferred_note = "NOT_AVAILABLE"
            if infer_piece_extents and meta.get("piece_start_mm") is None:
                s, e, inferred_note = _infer_extent_from_piece_type(
                    bar.get("piece_type"), span_f
                )
                if s is not None:
                    meta["piece_start_mm"] = s
                    meta["piece_end_mm"] = e
            proxy = _BarProxy(str(role), bar, meta)
            g = _bar_to_group(proxy, span_mm=span_f)
            rec = {
                "bar_id": bar.get("bar_id"),
                "bar_label": bar.get("bar_label"),
                "l2_key": key,
                "role_used": role,
                "role_source": role_source,
                "group": None if g is None else {
                    "role": g.role,
                    "face": g.face,
                    "start_mm": g.start_mm,
                    "end_mm": g.end_mm,
                    "clear_length_mm": g.clear_length_mm,
                    "extent_confidence": g.extent_confidence,
                    "has_extent": g.has_extent(),
                    "quantity": g.quantity,
                    "diameter_mm": g.diameter_mm,
                },
                "extent_inference": inferred_note if infer_piece_extents else "not_applied",
            }
            lineage.append(rec)
            if g is not None:
                groups.append(g)
    return groups, lineage


def _result_to_dict(res) -> Dict[str, Any]:
    return {
        "skipped": res.skipped,
        "skip_reason": res.skip_reason,
        "warnings": list(res.warnings),
        "n_rows": len(res.rows),
        "rows": [
            {
                "face": r.face,
                "quantity": r.quantity,
                "diameter_mm": r.diameter_mm,
                "spacing_mm": r.spacing_mm,
                "cut_length_mm": r.cut_length_mm,
                "zone_start_mm": r.zone_start_mm,
                "zone_end_mm": r.zone_end_mm,
                "zone_length_mm": r.zone_length_mm,
                "extent_fallback": r.extent_fallback,
                "cover_mm": r.cover_mm,
                "qty_from_ceil_formula": spacer_quantity(r.zone_length_mm),
            }
            for r in res.rows
        ],
        "quantities": [r.quantity for r in res.rows],
    }


def _spec_qty(overlap_mm: Optional[float]) -> Optional[float]:
    if overlap_mm is None or overlap_mm <= 0:
        return None
    # Authoritative text: (length / 1000) + 1  — no rounding stated
    return (float(overlap_mm) / SPACER_SPACING_MM) + 1.0


def _reverse_cut_base(cut_mm: Optional[float], dia: Optional[float], span: Optional[float]) -> Dict[str, Any]:
    if cut_mm is None or dia is None:
        return {"base_mm": None, "note": "NOT_AVAILABLE"}
    # Galera Fe550/M30 TABLE 1: Ld = 50d; GN hook 5d; piece cut = base + 2Ld + 2*hook*d
    ld = 50.0 * float(dia)
    hook_add = 2.0 * 5.0 * float(dia)
    base = float(cut_mm) - 2.0 * ld - hook_add
    note = "cut - 2*50d - 2*5d"
    kind = "UNCLASSIFIED"
    if span and abs(base - float(span)) <= 2.0:
        kind = "FULL_SPAN_PLUS_2LD_AND_HOOKS"
    elif span and abs(base - 0.25 * float(span)) <= 2.0:
        kind = "LEFT_OR_QUARTER_SPAN_PLUS_2LD_AND_HOOKS"
    elif span and abs(base - 0.75 * float(span)) <= 2.0:
        kind = "THREE_QUARTER_LENGTH_PLUS_2LD_AND_HOOKS"
    return {
        "cut_length_mm": cut_mm,
        "assumed_ld_mm": ld,
        "assumed_hook_add_mm": hook_add,
        "implied_base_mm": round(base, 3),
        "implied_base_kind": kind,
        "note": note,
        "WARNING": "Ld/hook assumptions are Galera TABLE 1 Fe550 + GN 5d; not stored on the L.2 spacer row",
    }


def analyze_beam(model: Dict[str, Any]) -> Dict[str, Any]:
    bid = model.get("beam_id")
    geom = model.get("geometry") or {}
    span = geom.get("clear_span_mm")
    width = geom.get("width_mm")
    depth = geom.get("depth_mm")
    cover = geom.get("top_cover_mm") or geom.get("bottom_cover_mm")
    try:
        span_f = float(span) if span is not None else None
        width_f = float(width) if width is not None else None
        cover_f = float(cover) if cover is not None else 30.0
    except (TypeError, ValueError):
        span_f = None
        width_f = None
        cover_f = 30.0

    longitudinal = []
    for key in LONG_KEYS:
        for bar in model.get(key) or []:
            if isinstance(bar, dict):
                rec = _bar_fields(bar, key)
                rec["cut_reverse"] = _reverse_cut_base(
                    bar.get("cut_length_mm"), bar.get("diameter_mm"), span_f
                )
                longitudinal.append(rec)

    spacers = []
    for bar in model.get("spacer_bars") or []:
        if isinstance(bar, dict):
            rec = _bar_fields(bar, "spacer_bars")
            rec["qty_matches_ceil_of_which_long_cut"] = []
            q = bar.get("quantity")
            for lg in longitudinal:
                cl = lg.get("cut_length_mm")
                if cl is None:
                    continue
                if spacer_quantity(float(cl)) == q:
                    rec["qty_matches_ceil_of_which_long_cut"].append(
                        {
                            "bar_id": lg.get("bar_id"),
                            "bar_label": lg.get("bar_label"),
                            "cut_length_mm": cl,
                            "formula": "ceil(cut_length_mm/1000)+1",
                        }
                    )
            if span_f:
                rec["qty_matches_ceil_of_span"] = spacer_quantity(span_f) == q
            spacers.append(rec)

    replays = {}
    for role_source in ("bar_id", "semantic_role", "bucket"):
        for infer in (False, True):
            tag = f"{role_source}_inferExtents={infer}"
            groups, lineage = _groups_from_l2(model, role_source, infer)
            inp = BeamSpacerInput(
                beam_id=str(bid),
                beam_width_mm=width_f,
                cover_mm=cover_f,
                groups=groups,
                already_has_spacer=False,
            )
            res = compute_spacers_for_beam(inp)
            replays[tag] = {
                "n_groups": len(groups),
                "lineage": lineage,
                "engine": _result_to_dict(res),
                "matches_l2_quantities": sorted(res.rows and [r.quantity for r in res.rows] or [])
                == sorted([s.get("quantity") for s in spacers]),
            }

    # Authoritative expected: one zone per physically distinct MAIN+EXTRA overlap.
    # Without true positions this is a bounded estimate, not a drawing proof.
    extras = [r for r in longitudinal if (r.get("bar_id_role_token") or r.get("semantic_role") or "").find("EXTRA") >= 0]
    mains = [r for r in longitudinal if (r.get("bar_id_role_token") or "").find("MAIN") >= 0]
    expected_notes = []
    if not extras and not any("EXTRA" in str(r.get("bucket_role")) for r in longitudinal):
        expected_notes.append("If only one face layer exists, authoritative rule says NO spacer")
    current_qty_sum = sum(int(s.get("quantity") or 0) for s in spacers)

    return {
        "beam_id": bid,
        "geometry": {
            "width_mm": width,
            "depth_mm": depth,
            "clear_span_mm": span,
            "cover_mm_l2": cover,
            "geometry_source": geom.get("geometry_source") or geom.get("source"),
            "confidence": geom.get("confidence"),
            "l2_geometry_keys": sorted(geom.keys()),
        },
        "cut_from_width_cover": engine_cut_length_mm(width_f or 0.0, cover_f) if width_f else None,
        "longitudinal_reinforcement_records": longitudinal,
        "spacer_records": spacers,
        "n_longitudinal": len(longitudinal),
        "n_spacer_l2_rows": len(spacers),
        "current_quantity_sum": current_qty_sum,
        "role_bucket_mismatches": [
            {
                "bar_id": r.get("bar_id"),
                "bar_label": r.get("bar_label"),
                "bar_id_role_token": r.get("bar_id_role_token"),
                "l2_key": r.get("l2_key"),
                "semantic_role": r.get("semantic_role"),
            }
            for r in longitudinal
            if r.get("bar_id_role_token") and r.get("bucket_role")
            and r.get("bar_id_role_token") != r.get("bucket_role")
        ],
        "m2_replays": replays,
        "authoritative_rule": {
            "diameter_mm": 25,
            "spacing_mm": 1000,
            "qty_formula_text": "(overlapping_bar_length / 1000) + 1",
            "implementation_qty_formula": "ceil(zone_length_mm / 1000) + 1",
            "cut_formula": "beam_width_mm - 2 * cover_mm",
            "expected_qty_if_full_span_overlap": _spec_qty(span_f),
            "implementation_qty_if_full_span_overlap": spacer_quantity(span_f) if span_f else None,
            "notes": expected_notes,
        },
        "missing_information": {
            "piece_start_mm": "NOT_AVAILABLE_IN_L2_EXPORT"
            if all(r.get("piece_start_mm") is None for r in longitudinal)
            else "present_on_some_records",
            "piece_end_mm": "NOT_AVAILABLE_IN_L2_EXPORT"
            if all(r.get("piece_end_mm") is None for r in longitudinal)
            else "present_on_some_records",
            "overlap_start_end": "NOT_AVAILABLE",
            "spacer_engineering_metadata": (
                "EMPTY_OR_MISSING"
                if all(not (s.get("engineering_metadata")) for s in spacers)
                else "present"
            ),
            "parent_trigger_bars": "NOT_AVAILABLE",
        },
    }


def extra_galera_cases(models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for m in models:
        bid = m.get("beam_id")
        n_sp = len(m.get("spacer_bars") or [])
        longs = []
        for k in LONG_KEYS:
            for b in m.get(k) or []:
                if isinstance(b, dict):
                    longs.append(
                        {
                            "l2_key": k,
                            "label": b.get("bar_label"),
                            "qty": b.get("quantity"),
                            "dia": b.get("diameter_mm"),
                            "cut": b.get("cut_length_mm"),
                            "bar_id": b.get("bar_id"),
                            "semantic_role": b.get("semantic_role"),
                        }
                    )
        n_top_m = len(m.get("top_main_bars") or [])
        n_top_e = len(m.get("top_extra_bars") or [])
        n_bot_m = len(m.get("bottom_main_bars") or [])
        n_bot_e = len(m.get("bottom_extra_bars") or [])
        interesting = (
            n_sp >= 2
            or (n_top_e >= 1 and n_top_m >= 1)
            or (n_bot_e >= 1 and n_bot_m >= 1)
            or (n_top_m >= 2)
            or (n_bot_m >= 2)
            or ("#L" in json.dumps(longs) and "#R" in json.dumps(longs))
            or (n_sp == 0 and (n_top_e + n_bot_e) > 0)
            or (n_sp == 0 and n_top_m + n_bot_m + n_top_e + n_bot_e == 1)
        )
        if not interesting and bid not in PRIMARY_BEAMS:
            continue
        tags = []
        if n_sp >= 2:
            tags.append("multiple_spacer_rows")
        if n_top_m >= 1 and n_top_e >= 1:
            tags.append("top_main_plus_top_extra")
        if n_bot_m >= 1 and n_bot_e >= 1:
            tags.append("bottom_main_plus_bottom_extra")
        if n_top_m >= 2:
            tags.append("multiple_top_main_records")
        if n_bot_m >= 2:
            tags.append("multiple_bottom_main_records")
        labels = " ".join(str(x.get("label") or "") for x in longs)
        if "#L" in labels and "#R" in labels:
            tags.append("left_right_extras")
        if n_sp == 0 and (n_top_e + n_bot_e) == 0 and (n_top_m + n_bot_m) <= 1:
            tags.append("no_spacer_expected_single_layer")
        if n_sp == 0 and (n_top_e + n_bot_e) > 0:
            tags.append("extra_present_but_zero_spacers")
        out.append(
            {
                "beam_id": bid,
                "n_spacer_rows": n_sp,
                "spacer_quantities": [b.get("quantity") for b in (m.get("spacer_bars") or []) if isinstance(b, dict)],
                "n_top_main": n_top_m,
                "n_top_extra": n_top_e,
                "n_bottom_main": n_bot_m,
                "n_bottom_extra": n_bot_e,
                "clear_span_mm": (m.get("geometry") or {}).get("clear_span_mm"),
                "width_mm": (m.get("geometry") or {}).get("width_mm"),
                "tags": tags,
                "longitudinal": longs,
            }
        )
    return out


def main() -> int:
    l2 = json.loads(L2_PATH.read_text(encoding="utf-8"))
    models = l2.get("models") or []
    by_id = {m.get("beam_id"): m for m in models if isinstance(m, dict)}

    focused = []
    for bid in FOCUS:
        if bid not in by_id:
            focused.append({"beam_id": bid, "error": "BEAM_NOT_IN_L2"})
            continue
        focused.append(analyze_beam(by_id[bid]))

    extras = extra_galera_cases(models)
    payload = {
        "phase": "W.18A",
        "mode": "READ_ONLY_FORENSIC",
        "l2_path": str(L2_PATH),
        "l2_source": l2.get("source"),
        "l2_model_version": l2.get("model_version"),
        "l2_model_count": l2.get("model_count") or len(models),
        "engine_qty_formula": "ceil(zone_length_mm / 1000) + 1",
        "engine_cut_formula": "beam_width_mm - 2 * cover_mm",
        "authoritative_qty_formula": "(overlapping_bar_length / spacing) + 1",
        "focused_beams": focused,
        "additional_galera_diagnostic_beams": extras,
        "galera_spacer_row_histogram": {},
        "notes": [
            "L.2 export (to_l2_compatible) drops engineering_metadata, piece_start_mm, piece_end_mm, and M.2 zone fields.",
            "M.2 replay here reconstructs injector groups from remaining L.2 fields; bar_id role token is the pre-hybrid EngineeringBarModel.bar_role.",
        ],
    }
    hist: Dict[str, int] = {}
    for m in models:
        n = len(m.get("spacer_bars") or [])
        hist[str(n)] = hist.get(str(n), 0) + 1
    payload["galera_spacer_row_histogram"] = hist

    OUT_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"model_count={payload['l2_model_count']} histogram={hist}")
    for b in focused:
        print(
            b.get("beam_id"),
            "spacers",
            b.get("n_spacer_l2_rows"),
            "qtys",
            [s.get("quantity") for s in b.get("spacer_records") or []],
            "mismatches",
            len(b.get("role_bucket_mismatches") or []),
        )
        replays = b.get("m2_replays") or {}
        for tag, rr in replays.items():
            print(" ", tag, "engine_qtys", rr.get("engine", {}).get("quantities"), "match", rr.get("matches_l2_quantities"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
