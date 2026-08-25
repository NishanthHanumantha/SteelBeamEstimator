"""Canonical Hybrid → R13 semantic handoff.

Patches Vision-preferred fields on the production R1.3 model. Never writes
cut length, spacing engineering, geometry, stirrup quantity, or Excel.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseW5_production_hybrid_shadow.paths import ensure_src_on_path

from .config import (
    ALL_BAR_BUCKETS,
    LONGITUDINAL_BUCKETS,
    PRE_HYBRID_FILENAME,
    PROTECTED_BAR_KEYS,
    R13_DIR_REL,
    R13_REL,
    SPACER_BUCKET,
    STIRRUP_BUCKET,
)

SRC_VISION = "VISION"

_LAYER_ROLE_BUCKET = {
    ("TOP", "MAIN"): ("top_main_bars", "TOP_MAIN"),
    ("TOP", "EXTRA"): ("top_extra_bars", "TOP_EXTRA"),
    ("BOTTOM", "MAIN"): ("bottom_main_bars", "BOTTOM_MAIN"),
    ("BOTTOM", "EXTRA"): ("bottom_extra_bars", "BOTTOM_EXTRA"),
    ("SIDE", "MAIN"): ("side_face_reinforcement", "SIDE_FACE_REINFORCEMENT"),
    ("SIDE", "EXTRA"): ("side_face_reinforcement", "SIDE_FACE_REINFORCEMENT"),
    ("SIDE_FACE", "MAIN"): ("side_face_reinforcement", "SIDE_FACE_REINFORCEMENT"),
    ("SIDE_FACE", "EXTRA"): ("side_face_reinforcement", "SIDE_FACE_REINFORCEMENT"),
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def r13_path(staging: Path) -> Path:
    return Path(staging) / R13_REL


def pre_hybrid_path(staging: Path) -> Path:
    return Path(staging) / R13_DIR_REL / PRE_HYBRID_FILENAME


def _models_list(data: Any) -> Tuple[Any, List[Dict[str, Any]]]:
    if isinstance(data, list):
        return data, [m for m in data if isinstance(m, dict)]
    if not isinstance(data, dict):
        return data, []
    models = data.get("models")
    if isinstance(models, list):
        return data, [m for m in models if isinstance(m, dict)]
    if isinstance(models, dict):
        return data, [v for v in models.values() if isinstance(v, dict)]
    if data.get("beam_id"):
        return data, [data]
    return data, []


def _field(rec: Any) -> Dict[str, Any]:
    return rec if isinstance(rec, dict) else {}


def _vision_value(rec: Any) -> Any:
    field = _field(rec)
    if field.get("source") != SRC_VISION:
        return None
    value = field.get("value")
    if value in (None, "", "UNKNOWN"):
        return None
    return value


def _parse_int(value: Any) -> Optional[int]:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _parse_diameter(spec: Any, explicit: Any = None) -> Optional[int]:
    ensure_src_on_path()
    from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.normalize import (  # noqa: WPS433
        parse_diameter,
    )

    return parse_diameter(spec, explicit)


def _detected_by_id(model: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    ensure_src_on_path()
    from PhaseP269_reinforcement_group_interpretation.extractor import (  # noqa: WPS433
        extract_detected_groups,
    )

    out: Dict[str, Dict[str, Any]] = {}
    for group in extract_detected_groups(model):
        if isinstance(group, dict) and group.get("group_id"):
            out[str(group.get("group_id"))] = group
    return out


def _source_bar_ids(group: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    raw = group.get("source_bar_ids")
    if isinstance(raw, list):
        ids.extend(str(x) for x in raw if x and str(x) not in ("UNKNOWN", ""))
    for key in ("source_bar_id", "deterministic_identity"):
        val = group.get(key)
        if val and str(val) not in ("UNKNOWN", ""):
            ids.append(str(val))
    extra = group.get("extra") if isinstance(group.get("extra"), dict) else {}
    if extra.get("source_bar_id"):
        ids.append(str(extra.get("source_bar_id")))
    seen = set()
    unique = []
    for item in ids:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _find_bar(
    model: Dict[str, Any], bar_id: str
) -> Optional[Tuple[str, int, Dict[str, Any]]]:
    for bucket in ALL_BAR_BUCKETS:
        bars = model.get(bucket)
        if not isinstance(bars, list):
            continue
        for idx, bar in enumerate(bars):
            if isinstance(bar, dict) and str(bar.get("bar_id") or "") == str(bar_id):
                return bucket, idx, bar
    return None


def _bucket_for(layer: Any, role: Any) -> Optional[Tuple[str, str]]:
    layer_u = str(layer or "").upper()
    role_u = str(role or "").upper()
    if layer_u in ("STIRRUP",) or role_u in ("STIRRUP",):
        return STIRRUP_BUCKET, "STIRRUP"
    if layer_u in ("SPACER",) or role_u in ("SPACER", "SPACER_BAR"):
        return SPACER_BUCKET, "SPACER_BAR"
    return _LAYER_ROLE_BUCKET.get((layer_u, role_u))


def _set_semantic(bar: Dict[str, Any], key: str, value: Any, applied: List[str]) -> None:
    if key in PROTECTED_BAR_KEYS:
        return
    if value is None:
        return
    if bar.get(key) == value:
        applied.append(key)
        return
    bar[key] = value
    applied.append(key)


def _apply_longitudinal_group(
    *,
    model: Dict[str, Any],
    group: Dict[str, Any],
    detected: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    ledger: List[Dict[str, Any]] = []
    origin = str(group.get("origin") or "")
    if origin == "VISION_ONLY_GROUP":
        return [
            {
                "beam_id": model.get("beam_id"),
                "origin": origin,
                "action": "UNRESOLVED_VISION_ONLY",
                "reason": "VISION_ONLY_GROUP_NOT_MATERIALIZED",
                "group_id": group.get("group_id"),
            }
        ]
    if origin not in ("MATCHED",):
        return []

    det_id = str(((group.get("provenance") or {}).get("deterministic_id") or group.get("group_id") or ""))
    detected_group = detected.get(det_id) or {}
    bar_ids = _source_bar_ids(detected_group)
    if not bar_ids:
        return [
            {
                "beam_id": model.get("beam_id"),
                "origin": origin,
                "action": "UNMATCHED_DETERMINISTIC_IDENTITY",
                "group_id": group.get("group_id"),
                "deterministic_id": det_id,
            }
        ]

    vis_count = _parse_int(_vision_value(group.get("bar_count")))
    vis_dia = _parse_int(_vision_value(group.get("diameter")))
    vis_spec = _vision_value(group.get("specification"))
    vis_role = _vision_value(group.get("role"))
    vis_layer = _vision_value(group.get("layer"))
    vis_scope = _vision_value(group.get("support_scope"))
    if vis_dia is None and vis_spec:
        vis_dia = _parse_diameter(vis_spec)

    target_bucket_role = None
    if vis_layer or vis_role:
        # Combine Vision-preferred layer/role with remaining deterministic values.
        sample = _find_bar(model, bar_ids[0])
        current_role = (sample[2].get("semantic_role") if sample else "") or ""
        layer_guess = vis_layer
        role_guess = vis_role
        if layer_guess is None:
            if "TOP" in str(current_role).upper():
                layer_guess = "TOP"
            elif "BOTTOM" in str(current_role).upper():
                layer_guess = "BOTTOM"
            elif "SIDE" in str(current_role).upper():
                layer_guess = "SIDE_FACE"
        if role_guess is None:
            if "EXTRA" in str(current_role).upper():
                role_guess = "EXTRA"
            elif "MAIN" in str(current_role).upper():
                role_guess = "MAIN"
        target_bucket_role = _bucket_for(layer_guess, role_guess)

    for bar_id in bar_ids:
        located = _find_bar(model, bar_id)
        if located is None:
            ledger.append(
                {
                    "beam_id": model.get("beam_id"),
                    "bar_id": bar_id,
                    "action": "BAR_NOT_FOUND",
                    "group_id": group.get("group_id"),
                }
            )
            continue
        bucket, idx, bar = located
        if bucket == STIRRUP_BUCKET or bucket == SPACER_BUCKET:
            continue
        applied: List[str] = []
        before = {
            "quantity": bar.get("quantity"),
            "diameter_mm": bar.get("diameter_mm"),
            "bar_label": bar.get("bar_label"),
            "semantic_role": bar.get("semantic_role"),
            "bucket": bucket,
            "cut_length_mm": bar.get("cut_length_mm"),
            "spacing_mm": bar.get("spacing_mm"),
        }
        if vis_count is not None:
            _set_semantic(bar, "quantity", vis_count, applied)
        if vis_dia is not None:
            _set_semantic(bar, "diameter_mm", vis_dia, applied)
        if vis_spec is not None:
            _set_semantic(bar, "bar_label", str(vis_spec), applied)
        if vis_scope is not None:
            _set_semantic(bar, "support_zone", str(vis_scope), applied)
            _set_semantic(bar, "extent", str(vis_scope), applied)
        moved_to = bucket
        if target_bucket_role is not None:
            dest_bucket, dest_role = target_bucket_role
            if dest_bucket in LONGITUDINAL_BUCKETS:
                _set_semantic(bar, "semantic_role", dest_role, applied)
                if dest_bucket != bucket:
                    model.setdefault(dest_bucket, [])
                    if not isinstance(model[dest_bucket], list):
                        model[dest_bucket] = []
                    model[bucket].pop(idx)
                    model[dest_bucket].append(bar)
                    moved_to = dest_bucket
                    applied.append("bucket")
        if applied:
            bar["hybrid_semantic_handoff"] = {
                "applied": True,
                "phase": "W.6",
                "source": SRC_VISION,
                "fields": sorted(set(applied)),
                "group_id": group.get("group_id"),
            }
        ledger.append(
            {
                "beam_id": model.get("beam_id"),
                "bar_id": bar_id,
                "group_id": group.get("group_id"),
                "origin": origin,
                "action": "PATCHED" if applied else "NO_VISION_FIELDS",
                "fields": sorted(set(applied)),
                "before": before,
                "after": {
                    "quantity": bar.get("quantity"),
                    "diameter_mm": bar.get("diameter_mm"),
                    "bar_label": bar.get("bar_label"),
                    "semantic_role": bar.get("semantic_role"),
                    "bucket": moved_to,
                    "cut_length_mm": bar.get("cut_length_mm"),
                    "spacing_mm": bar.get("spacing_mm"),
                },
                "engineering_untouched": {
                    "cut_length_mm": before.get("cut_length_mm") == bar.get("cut_length_mm"),
                    "spacing_mm": before.get("spacing_mm") == bar.get("spacing_mm"),
                },
            }
        )
    return ledger


def _apply_stirrup_item(
    *,
    model: Dict[str, Any],
    item: Dict[str, Any],
) -> List[Dict[str, Any]]:
    origin = str(item.get("origin") or "")
    if origin == "VISION_ONLY_GROUP":
        return [
            {
                "beam_id": model.get("beam_id"),
                "origin": origin,
                "action": "UNRESOLVED_VISION_ONLY_STIRRUP",
                "reason": "VISION_ONLY_STIRRUP_NOT_MATERIALIZED",
            }
        ]
    if origin != "MATCHED":
        return []
    ident = _field(item.get("semantic_identification"))
    if ident.get("source") != SRC_VISION:
        return []
    spec = ident.get("value")
    if spec in (None, "", "UNKNOWN"):
        return []
    det_spec = ((_field(item.get("engineering_calculation_reference"))).get("specification"))
    if not det_spec:
        return [
            {
                "beam_id": model.get("beam_id"),
                "origin": origin,
                "action": "STIRRUP_IDENTITY_UNMATCHED",
                "reason": "MISSING_DETERMINISTIC_SPEC",
            }
        ]
    dia = _parse_diameter(spec)
    ledger: List[Dict[str, Any]] = []
    stirrups = model.get(STIRRUP_BUCKET) if isinstance(model.get(STIRRUP_BUCKET), list) else []
    for bar in stirrups:
        if not isinstance(bar, dict):
            continue
        label = str(bar.get("bar_label") or "")
        if det_spec:
            if label != str(det_spec):
                continue
        applied: List[str] = []
        before_qty = bar.get("quantity")
        before_cut = bar.get("cut_length_mm")
        before_spacing = bar.get("spacing_mm")
        _set_semantic(bar, "bar_label", str(spec), applied)
        if dia is not None:
            _set_semantic(bar, "diameter_mm", dia, applied)
        if applied:
            bar["hybrid_semantic_handoff"] = {
                "applied": True,
                "phase": "W.6",
                "source": SRC_VISION,
                "fields": sorted(set(applied)),
                "kind": "STIRRUP_IDENTIFICATION",
            }
        ledger.append(
            {
                "beam_id": model.get("beam_id"),
                "bar_id": bar.get("bar_id"),
                "origin": origin,
                "action": "PATCHED_STIRRUP_IDENTIFICATION" if applied else "NO_VISION_FIELDS",
                "fields": sorted(set(applied)),
                "quantity_unchanged": before_qty == bar.get("quantity"),
                "cut_length_unchanged": before_cut == bar.get("cut_length_mm"),
                "spacing_unchanged": before_spacing == bar.get("spacing_mm"),
            }
        )
        if det_spec:
            break
    return ledger


def apply_beam_handoff(
    *,
    model: Dict[str, Any],
    hybrid_semantic: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(model, dict) or not isinstance(hybrid_semantic, dict):
        return []
    detected = _detected_by_id(model)
    ledger: List[Dict[str, Any]] = []
    for group in hybrid_semantic.get("reinforcement_groups") or []:
        if isinstance(group, dict):
            ledger.extend(
                _apply_longitudinal_group(model=model, group=group, detected=detected)
            )
    stirrups = hybrid_semantic.get("stirrups") or {}
    items = stirrups.get("items") if isinstance(stirrups, dict) else []
    for item in items or []:
        if isinstance(item, dict):
            ledger.extend(_apply_stirrup_item(model=model, item=item))
    return ledger


def apply_production_handoff(
    *,
    staging: Path,
    shadow_result: Dict[str, Any],
    apply: bool,
) -> Dict[str, Any]:
    """
    If apply is True and Vision resolved MATCHED groups, patch R13 in place
    after saving a pre-hybrid snapshot. Never fabricates bars.
    """
    path = r13_path(staging)
    payload = {
        "applied": False,
        "reason": "NOT_APPLIED",
        "r13_path": str(path),
        "pre_hybrid_path": None,
        "beams_patched": 0,
        "fields_patched": 0,
        "unresolved_vision_only": 0,
        "ledger": [],
        "engineering_protected_keys": list(PROTECTED_BAR_KEYS),
    }
    if not path.is_file():
        payload["reason"] = "R13_MISSING"
        return payload
    original = _load_json(path)
    if not apply:
        payload["reason"] = "HANDOFF_NOT_AUTHORITATIVE"
        return payload

    wrapper, models = _models_list(copy.deepcopy(original))
    by_id = {str(m.get("beam_id")): m for m in models if m.get("beam_id")}
    ledger: List[Dict[str, Any]] = []
    patched_beams = 0
    for row in shadow_result.get("beams") or []:
        if not isinstance(row, dict):
            continue
        beam_id = str(row.get("beam_id") or "")
        model = by_id.get(beam_id)
        hybrid = row.get("hybrid_semantic")
        if model is None or not isinstance(hybrid, dict):
            continue
        if row.get("hybrid_status") not in ("OBSERVED",):
            continue
        beam_ledger = apply_beam_handoff(model=model, hybrid_semantic=hybrid)
        ledger.extend(beam_ledger)
        if any(item.get("action", "").startswith("PATCHED") for item in beam_ledger):
            patched_beams += 1

    payload["ledger"] = ledger
    payload["beams_patched"] = patched_beams
    payload["fields_patched"] = sum(len(item.get("fields") or []) for item in ledger)
    payload["unresolved_vision_only"] = sum(
        1 for item in ledger if "VISION_ONLY" in str(item.get("action") or "")
    )
    if patched_beams == 0 and not ledger:
        payload["reason"] = "NO_VISION_MATCHED_FIELDS"
        return payload

    pre = pre_hybrid_path(staging)
    if not pre.exists():
        _dump_json(pre, original)
    payload["pre_hybrid_path"] = str(pre)
    _dump_json(path, wrapper)
    payload["applied"] = True
    payload["reason"] = "HYBRID_SEMANTIC_HANDOFF_APPLIED"
    return payload
