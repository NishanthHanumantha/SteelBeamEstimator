"""Build per-beam benchmark evidence records from existing artefacts. No reselection."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP2610C3_visual_completeness_claude_shadow.manifest_loader import sha256_file

from .config import STATUS_NOT_READY
from .discovery import load_p269_inventory
from .normalize import map_layer, normalize_spec


def _side_integrity(side: Dict[str, Any]) -> Dict[str, Any]:
    path_s = side.get("selected_path")
    expected = side.get("selected_sha256")
    p = Path(path_s) if path_s else None
    exists = bool(p and p.exists() and p.is_file() and p.stat().st_size > 200)
    actual = sha256_file(p) if exists else None
    mismatch = bool(exists and expected and actual and actual.lower() != str(expected).lower())
    return {
        "path": str(p) if p else None,
        "exists": exists,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "sha_mismatch": mismatch,
        "integrity_ok": exists and not mismatch,
        "source_phase": side.get("selected_source_phase") or side.get("source_phase"),
        "primary_status": side.get("selected_primary_status"),
        "critical_failure": side.get("selected_critical_failure"),
        "reason_codes": list(side.get("selection_reason_codes") or []),
    }


def _group_stats(groups: List[Dict[str, Any]]) -> Dict[str, Any]:
    long_g = []
    stirrups = []
    layers = []
    roles = []
    specs = []
    for g in groups or []:
        layer = map_layer(g.get("physical_layer") or g.get("layer"))
        role = str(g.get("reinforcement_role") or g.get("role") or "").upper()
        fam = str(g.get("family") or "").upper()
        spec = normalize_spec(g.get("specification") or g.get("spec"))
        if fam == "STIRRUP" or layer == "STIRRUP":
            stirrups.append(g)
            continue
        long_g.append(g)
        layers.append(layer)
        roles.append(role)
        specs.append(spec)
    top_n = sum(1 for x in layers if x == "TOP")
    bot_n = sum(1 for x in layers if x == "BOTTOM")
    spec_counts: Dict[str, int] = {}
    for s in specs:
        if s:
            spec_counts[s] = spec_counts.get(s, 0) + 1
    same_spec_distinct = any(n > 1 for n in spec_counts.values())
    # same spec on different layer/role
    keys = [(map_layer(g.get("physical_layer") or g.get("layer")), str(g.get("reinforcement_role") or g.get("role") or "").upper(), normalize_spec(g.get("specification") or g.get("spec"))) for g in long_g]
    spec_to_keys: Dict[str, set] = {}
    for layer, role, spec in keys:
        if not spec:
            continue
        spec_to_keys.setdefault(spec, set()).add((layer, role))
    same_spec_distinct = any(len(v) > 1 for v in spec_to_keys.values())
    stirrup_complex = any("@" in str(g.get("specification") or g.get("spec") or "") for g in stirrups)
    return {
        "longitudinal_count": len(long_g),
        "stirrup_count": len(stirrups),
        "top_count": top_n,
        "bottom_count": bot_n,
        "has_main": "MAIN" in roles,
        "has_extra": "EXTRA" in roles,
        "same_spec_distinct": same_spec_distinct,
        "stirrup_present": len(stirrups) > 0,
        "stirrup_complex": stirrup_complex,
        "layers": sorted(set(layers)),
        "roles": sorted(set(roles)),
    }


def build_candidate(
    *,
    v10: Path,
    set_key: str,
    sel_row: Dict[str, Any],
    gate_row: Optional[Dict[str, Any]],
    r13_groups: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    beam_id = str(sel_row.get("beam_id"))
    ctx = _side_integrity(sel_row.get("context") or {})
    det = _side_integrity(sel_row.get("detail") or {})
    inv = load_p269_inventory(v10, set_key, beam_id)
    expected = list((inv or {}).get("expected_groups") or [])
    detected = list((inv or {}).get("detected_groups") or [])
    if not detected and r13_groups:
        detected = list(r13_groups)
    stats = _group_stats(expected or detected)
    gate = gate_row or {}
    status = str(gate.get("status") or "")
    nested = gate.get("gate") or {}
    anchor = nested.get("anchor") or {}
    assoc = bool(anchor.get("association_ambiguous"))
    reasons = list(gate.get("reason_codes") or nested.get("reason_codes") or [])
    valid = bool(ctx.get("integrity_ok") and det.get("integrity_ok"))
    excluded_reason = None
    if not ctx.get("exists") or not det.get("exists"):
        excluded_reason = "MISSING_SELECTED_PNG"
        valid = False
    elif ctx.get("sha_mismatch") or det.get("sha_mismatch"):
        excluded_reason = "SHA256_MISMATCH"
        valid = False
    elif status == STATUS_NOT_READY:
        excluded_reason = "VISION_NOT_READY"
    return {
        "beam_id": beam_id,
        "set_key": set_key,
        "drawing_set_provenance": set_key,
        "context_selected_source": ctx.get("source_phase"),
        "detail_selected_source": det.get("source_phase"),
        "context_selected_path": ctx.get("path"),
        "detail_selected_path": det.get("path"),
        "context_selected_sha256": ctx.get("expected_sha256"),
        "detail_selected_sha256": det.get("expected_sha256"),
        "mixed_source": ctx.get("source_phase") != det.get("source_phase"),
        "c3_visual_gate_status": status or None,
        "c3_gate_reasons": reasons,
        "association_ambiguous": assoc,
        "neighbour_association_risk": assoc,
        "deterministic_group_count": stats["longitudinal_count"] + stats["stirrup_count"],
        "deterministic_layers": stats["layers"],
        "stirrup_interpretation_present": stats["stirrup_present"],
        "multiple_longitudinal_groups": stats["longitudinal_count"] > 2 or stats["top_count"] > 1 or stats["bottom_count"] > 1,
        "group_stats": stats,
        "p269_available": inv is not None,
        "expected_groups": expected,
        "detected_groups": detected,
        "context_integrity": ctx,
        "detail_integrity": det,
        "evidence_valid": valid,
        "excluded_reason": excluded_reason,
        "known_render_limitations": reasons,
    }


def sha256_hex(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["build_candidate", "sha256_hex"]
