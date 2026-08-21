"""Collect competing evidence. Do not invent missing sources. No beam-ID outcome logic."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    AVAIL_AVAILABLE,
    AVAIL_MISSING,
    P2610C1C2_OUTPUT_DIRNAME,
    P269_OUTPUT_DIRNAME,
    SOURCE_DET,
    SOURCE_MANUAL,
    SOURCE_P269,
    SOURCE_RENDER,
    SOURCE_SKETCH,
    SOURCE_VISION,
)
from .discovery import load_json
from .normalize import keys_of, physical_identity


def default_manual_path(package_dir: Path) -> Path:
    return Path(package_dir) / "fixtures" / "manual_verification.json"


def load_manual_verifications(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if path is None or not Path(path).exists():
        return {}
    payload = load_json(Path(path)) or {}
    out: Dict[str, Dict[str, Any]] = {}
    for row in payload.get("verifications") or []:
        bid = row.get("beam_id")
        if bid:
            out[str(bid)] = row
    return out


def _item(
    *,
    evidence_id: str,
    beam_id: str,
    source_type: str,
    source_path: Optional[str],
    source_phase: str,
    evidence_scope: str,
    availability: str,
    layer: str = "",
    role: str = "",
    specification: str = "",
    support_scope: str = "",
    confidence: Any = None,
    evidence_text: str = "",
    provenance: str = "",
    verification_status: str = "UNRESOLVED",
) -> Dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "beam_id": beam_id,
        "source_type": source_type,
        "source_path": source_path,
        "source_phase": source_phase,
        "evidence_scope": evidence_scope,
        "layer": layer,
        "role": role,
        "specification": specification,
        "support_scope": support_scope,
        "confidence": confidence,
        "evidence_text": evidence_text,
        "provenance": provenance,
        "availability": availability,
        "verification_status": verification_status,
    }


def vision_groups_from_parsed(parsed: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed = parsed or {}
    groups: List[Dict[str, Any]] = []
    for g in parsed.get("reinforcement_groups") or []:
        groups.append(
            {
                "layer": g.get("layer"),
                "role": g.get("role"),
                "specification": g.get("spec") or g.get("specification"),
                "support_scope": g.get("support_scope"),
                "confidence": g.get("confidence"),
            }
        )
    for s in parsed.get("stirrups") or []:
        groups.append(
            {
                "layer": "STIRRUP",
                "role": "STIRRUP",
                "specification": s.get("spec") or s.get("specification"),
                "support_scope": s.get("support_scope") or "",
                "confidence": s.get("confidence"),
            }
        )
    return groups


def catalog_groups(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for g in groups or []:
        layer, role, spec = physical_identity(g)
        out.append(
            {
                "layer": layer,
                "role": role,
                "specification": spec,
                "raw_specification": g.get("specification") or g.get("spec"),
                "support_scope": g.get("support_scope") or g.get("zone") or "",
                "family": g.get("family"),
                "confidence": g.get("confidence"),
            }
        )
    return out


def manual_groups(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups = list(row.get("verified_groups") or [])
    for s in row.get("verified_stirrups") or []:
        groups.append(
            {
                "layer": s.get("layer") or "STIRRUP",
                "role": s.get("role") or "STIRRUP",
                "specification": s.get("specification") or s.get("spec"),
                "support_scope": s.get("support_scope") or "",
            }
        )
    return groups


def overlay_groups(v10: Path, set_key: str, beam_id: str) -> List[Dict[str, Any]]:
    path = (
        Path(v10)
        / "src"
        / "PhaseP269_reinforcement_group_interpretation"
        / "fixtures"
        / "benchmark_reference.json"
    )
    data = load_json(path)
    if not data:
        return []
    for row in data.get("beams") or []:
        if row.get("set_key") == set_key and row.get("beam_id") == beam_id:
            return list(row.get("overlay_groups") or [])
    return []


def selection_row(v10: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = Path(v10) / "data" / "output" / P2610C1C2_OUTPUT_DIRNAME / "selection_manifest.json"
    payload = load_json(path)
    rows = payload if isinstance(payload, list) else (payload or {}).get("_list") or (payload or {}).get("rows")
    if not isinstance(rows, list):
        # manifest is a list at top level
        try:
            raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        except Exception:
            raw = None
        rows = raw if isinstance(raw, list) else []
    for row in rows:
        if row.get("beam_id") == beam_id:
            return row
    return None


def collect_beam_evidence(
    *,
    beam_id: str,
    set_key: str,
    c3_row: Dict[str, Any],
    c3_path: str,
    manual_row: Optional[Dict[str, Any]],
    v10: Path,
) -> Dict[str, Any]:
    parsed = ((c3_row.get("claude") or {}).get("parsed")) or {}
    comparison = c3_row.get("comparison") or {}
    vision = vision_groups_from_parsed(parsed)
    p269 = list(comparison.get("p269_expected") or [])
    det = list(comparison.get("deterministic") or [])
    sketch = overlay_groups(v10, set_key, beam_id)
    sel = selection_row(v10, beam_id)
    ctx = (sel or {}).get("context") or {}
    det_sel = (sel or {}).get("detail") or {}
    ctx_path = ctx.get("selected_path")
    det_path = det_sel.get("selected_path")
    ctx_exists = bool(ctx_path and Path(ctx_path).exists())
    det_exists = bool(det_path and Path(det_path).exists())

    inventory: List[Dict[str, Any]] = []
    n = 0

    def add(**kwargs: Any) -> None:
        nonlocal n
        n += 1
        inventory.append(_item(evidence_id=f"{beam_id}-E{n:02d}", beam_id=beam_id, **kwargs))

    if vision:
        for g in catalog_groups(vision):
            add(
                source_type=SOURCE_VISION,
                source_path=c3_path,
                source_phase="P2.6.10-C.3",
                evidence_scope="GROUP",
                availability=AVAIL_AVAILABLE,
                layer=g["layer"],
                role=g["role"],
                specification=g["specification"],
                support_scope=g.get("support_scope") or "",
                confidence=g.get("confidence"),
                evidence_text="Existing C.3 Claude parsed group",
                provenance="PhaseP2610C3_visual_completeness_claude_shadow",
                verification_status="RECORDED",
            )
    else:
        add(
            source_type=SOURCE_VISION,
            source_path=c3_path,
            source_phase="P2.6.10-C.3",
            evidence_scope="BEAM",
            availability=AVAIL_MISSING if not parsed else AVAIL_AVAILABLE,
            evidence_text="No parsed Vision groups",
            provenance="PhaseP2610C3_visual_completeness_claude_shadow",
            verification_status="MISSING_EVIDENCE" if not parsed else "RECORDED",
        )

    if det:
        for g in catalog_groups(det):
            add(
                source_type=SOURCE_DET,
                source_path=str(
                    Path(v10) / "data" / "output" / P269_OUTPUT_DIRNAME / "inventories" / f"{set_key}_{beam_id}.json"
                ),
                source_phase="P2.6.9 / R.1",
                evidence_scope="GROUP",
                availability=AVAIL_AVAILABLE,
                layer=g["layer"],
                role=g["role"],
                specification=g["specification"],
                support_scope=g.get("support_scope") or "",
                confidence=g.get("confidence"),
                evidence_text="Deterministic / R.1 detected group",
                provenance="P269 inventory detected_groups",
                verification_status="RECORDED",
            )
    else:
        add(
            source_type=SOURCE_DET,
            source_path=None,
            source_phase="P2.6.9 / R.1",
            evidence_scope="BEAM",
            availability=AVAIL_MISSING,
            evidence_text="MISSING_EVIDENCE",
            provenance="P269 inventory",
            verification_status="MISSING_EVIDENCE",
        )

    if p269:
        for g in catalog_groups(p269):
            add(
                source_type=SOURCE_P269,
                source_path=str(
                    Path(v10) / "data" / "output" / P269_OUTPUT_DIRNAME / "inventories" / f"{set_key}_{beam_id}.json"
                ),
                source_phase="P2.6.9",
                evidence_scope="GROUP",
                availability=AVAIL_AVAILABLE,
                layer=g["layer"],
                role=g["role"],
                specification=g["specification"],
                support_scope=g.get("support_scope") or "",
                evidence_text="P2.6.9 expected group",
                provenance="P269 inventory expected_groups",
                verification_status="RECORDED",
            )
    else:
        add(
            source_type=SOURCE_P269,
            source_path=None,
            source_phase="P2.6.9",
            evidence_scope="BEAM",
            availability=AVAIL_MISSING,
            evidence_text="MISSING_EVIDENCE",
            provenance="P269 inventory",
            verification_status="MISSING_EVIDENCE",
        )

    if sketch:
        for g in catalog_groups(sketch):
            add(
                source_type=SOURCE_SKETCH,
                source_path=str(
                    Path(v10)
                    / "src"
                    / "PhaseP269_reinforcement_group_interpretation"
                    / "fixtures"
                    / "benchmark_reference.json"
                ),
                source_phase="P2.6.9 overlay",
                evidence_scope="GROUP",
                availability=AVAIL_AVAILABLE,
                layer=g["layer"],
                role=g["role"],
                specification=g["specification"],
                evidence_text="Structured overlay group only; not automatic truth",
                provenance="benchmark_reference overlay_groups",
                verification_status="RECORDED",
            )
    else:
        add(
            source_type=SOURCE_SKETCH,
            source_path=str(
                Path(v10)
                / "src"
                / "PhaseP269_reinforcement_group_interpretation"
                / "fixtures"
                / "benchmark_reference.json"
            ),
            source_phase="P2.6.9 notes",
            evidence_scope="BEAM",
            availability=AVAIL_AVAILABLE if comparison.get("manual_notes") else AVAIL_MISSING,
            evidence_text="Free-text discrepancy notes are not parsed as groups",
            provenance="benchmark_reference discrepancy_notes",
            verification_status="UNRESOLVED",
        )

    for crop_type, path_s, exists in (
        ("context", ctx_path, ctx_exists),
        ("detail", det_path, det_exists),
    ):
        add(
            source_type=SOURCE_RENDER,
            source_path=path_s,
            source_phase=str((ctx if crop_type == "context" else det_sel).get("source_phase") or ""),
            evidence_scope=crop_type.upper(),
            availability=AVAIL_AVAILABLE if exists else AVAIL_MISSING,
            evidence_text="Selected PNG referenced only; pixels are not interpreted as groups",
            provenance="C.1+C.2 selection_manifest.json",
            verification_status="UNRESOLVED" if exists else "MISSING_EVIDENCE",
        )

    independent: List[Dict[str, Any]] = []
    if manual_row and str(manual_row.get("verification_status") or "").upper() == "VERIFIED":
        independent = manual_groups(manual_row)
        for g in catalog_groups(independent):
            add(
                source_type=SOURCE_MANUAL,
                source_path=str(default_manual_path(Path(__file__).resolve().parent)),
                source_phase="P2.6.10-C.4 fixture",
                evidence_scope="GROUP",
                availability=AVAIL_AVAILABLE,
                layer=g["layer"],
                role=g["role"],
                specification=g["specification"],
                support_scope=g.get("support_scope") or "",
                evidence_text=str(manual_row.get("notes") or ""),
                provenance=str(manual_row.get("verification_basis") or SOURCE_MANUAL),
                verification_status="VERIFIED",
            )

    return {
        "beam_id": beam_id,
        "set_key": set_key,
        "inventory": inventory,
        "vision_groups": catalog_groups(vision),
        "deterministic_groups": catalog_groups(det),
        "p269_groups": catalog_groups(p269),
        "phase_sketch_groups": catalog_groups(sketch),
        "independent_groups": catalog_groups(independent),
        "independent_basis": (manual_row or {}).get("verification_basis") if independent else None,
        "context_provenance": {
            "path": ctx_path,
            "source_phase": ctx.get("source_phase") or c3_row.get("context_source"),
            "sha256": ctx.get("selected_sha256"),
            "exists": ctx_exists,
        },
        "detail_provenance": {
            "path": det_path,
            "source_phase": det_sel.get("source_phase") or c3_row.get("detail_source"),
            "sha256": det_sel.get("selected_sha256"),
            "exists": det_exists,
        },
        "claude_called": bool((c3_row.get("claude") or {}).get("called")),
        "c3_taxonomy": comparison.get("taxonomy"),
        "notes": comparison.get("manual_notes") or [],
        "vision_keys": [list(k) for k in keys_of(catalog_groups(vision))],
        "deterministic_keys": [list(k) for k in keys_of(catalog_groups(det))],
    }


__all__ = [
    "catalog_groups",
    "collect_beam_evidence",
    "default_manual_path",
    "load_manual_verifications",
    "manual_groups",
    "vision_groups_from_parsed",
]
