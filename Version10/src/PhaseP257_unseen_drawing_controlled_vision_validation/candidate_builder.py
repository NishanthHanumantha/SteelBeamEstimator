"""Build Fifth Set candidates using the real P2.5.1 QuantityIntent path."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PhaseP251_quantity_intent_schema.intent_builder import build_intent_for_annotation
from PhaseP255_controlled_shadow_integration.deterministic_snapshot import intent_to_snapshot

from .selective_gate import should_invoke_claude, trigger_reasons


def _ownership_path(version10_root: Path) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / "Fifth_Set_Drawings"
        / "EngineeringSummaries"
        / "BeamOwnership.json"
    )


def _crop_path(version10_root: Path, beam_id: str) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / "PhaseQA30_unseen_benchmark"
        / "Fifth_Set_Drawings"
        / "RenderedCrops"
        / "shared_renders"
        / f"{beam_id}_render.png"
    )


def _beam_evidence(beam_id: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    anns = []
    for a in rec.get("accepted_annotations") or []:
        aid = a.get("id") or a.get("annotation_id")
        anns.append(
            {
                "annotation_id": aid,
                "raw_text": a.get("text") or "",
                "normalized_text": a.get("text") or "",
            }
        )
    env = (rec.get("envelope") or {})
    return {
        "beam_id": beam_id,
        "phase_id": "P2.5.7_FIFTH_SET_EVIDENCE",
        "annotations": anns,
        "leader_chains": {"accepted": list(rec.get("accepted_chains") or [])},
        "beam_depth_mm": env.get("depth_mm"),
        "beam_orientation": "HORIZONTAL",
    }


def build_candidates(version10_root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (all_rows, eligible_for_claude). Each row has candidate + deterministic snapshot."""
    data = json.loads(_ownership_path(version10_root).read_text(encoding="utf-8"))
    all_rows: List[Dict[str, Any]] = []
    eligible: List[Dict[str, Any]] = []
    for beam_id, rec in sorted((data.get("by_beam") or {}).items()):
        evidence = _beam_evidence(beam_id, rec)
        siblings = [a.get("raw_text") for a in evidence["annotations"]]
        crop = _crop_path(version10_root, beam_id)
        for ann in evidence["annotations"]:
            intent = build_intent_for_annotation(
                beam_id=beam_id, annotation=ann, evidence=evidence
            )
            if intent is None:
                continue
            det = intent_to_snapshot(intent)
            cid = f"VC::{beam_id}::{ann['annotation_id']}"
            candidate = {
                "candidate_id": cid,
                "beam_id": beam_id,
                "annotation_id": ann["annotation_id"],
                "raw_text": ann["raw_text"],
                "normalized_text": intent.normalized_text,
                "quantity_status": intent.quantity_status,
                "baseline_semantic_type": intent.semantic_type,
                "baseline_role": intent.reinforcement_role,
                "beam_depth_mm": evidence.get("beam_depth_mm"),
                "beam_orientation": evidence.get("beam_orientation"),
                "sibling_annotation_count": len(siblings),
                "sibling_annotation_texts": [t for t in siblings if t != ann["raw_text"]],
                "evidence_source": "FIFTH_SET_T18_OWNERSHIP",
                "crop_path": str(crop) if crop.exists() else None,
                "has_crop": crop.exists(),
                "provenance_ids": {"intent_id": intent.intent_id},
            }
            reasons = trigger_reasons(candidate=candidate, deterministic=det)
            invoke, skip_or_force = should_invoke_claude(reasons)
            candidate["candidate_reason_codes"] = reasons
            candidate["shadow_trigger_reason"] = reasons
            row = {
                "candidate": candidate,
                "deterministic": det,
                "invoke_claude": invoke and crop.exists(),
                "skip_reason": None if (invoke and crop.exists()) else (
                    "MISSING_CROP" if invoke and not crop.exists() else skip_or_force
                ),
            }
            all_rows.append(row)
            if row["invoke_claude"]:
                eligible.append(row)
    return all_rows, eligible


__all__ = ["build_candidates"]
