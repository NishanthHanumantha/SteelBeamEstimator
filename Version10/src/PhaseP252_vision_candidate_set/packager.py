"""Package verified P2.5.0 visual evidence for Vision candidates."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from .config import VISION_STATUS_PENDING
from .crop_qa import evaluate_candidate_crop_qa
from .selector import mark_insufficient_visual


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def load_evidence(p250_beams_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = p250_beams_root / beam_id / "evidence.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def package_candidate(
    *,
    selection: Dict[str, Any],
    p250_beams_root: Path,
    candidates_root: Path,
) -> Dict[str, Any]:
    """
    Build one candidate visual evidence package.
    Uses verified P2.5.0 engineering_crop as both local and beam-context visuals
    (evidence window already encodes accepted-evidence crop).
    """
    beam_id = selection["beam_id"]
    cid = selection["candidate_id"]
    out_dir = candidates_root / cid.replace("::", "__")
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence = load_evidence(p250_beams_root, beam_id)
    src_eng = p250_beams_root / beam_id / "engineering_crop.png"
    src_ovl = p250_beams_root / beam_id / "evidence_overlay.png"

    local_path = out_dir / "local_crop.png"
    beam_ctx_path = out_dir / "beam_context_crop.png"
    has_visual = False
    if src_eng.exists():
        shutil.copy2(src_eng, local_path)
        shutil.copy2(src_eng, beam_ctx_path)
        has_visual = True
    # optional overlay for human review (not sent as primary Vision crop)
    if src_ovl.exists():
        shutil.copy2(src_ovl, out_dir / "evidence_overlay.png")

    outcome = selection.get("outcome")
    # Only package Vision candidates / deferred with attempted visuals
    if outcome == "VISION_CANDIDATE" and not has_visual:
        selection = mark_insufficient_visual(selection)
        outcome = selection["outcome"]

    qa = evaluate_candidate_crop_qa(
        selection=selection,
        evidence=evidence,
        local_crop_path=local_path if has_visual else None,
        beam_context_path=beam_ctx_path if has_visual else None,
    )

    # Extreme / unreadable verified crop → defer rather than send bad evidence to Vision
    if qa.get("overall") == "FAIL" and (
        "NO_EXTREME_EXPANSION" in (qa.get("hard_fails") or [])
        or "VALID_IMAGE" in (qa.get("hard_fails") or [])
        or "TARGET_BEAM_PRESENT" in (qa.get("hard_fails") or [])
    ):
        if selection.get("outcome") == "VISION_CANDIDATE":
            selection = mark_insufficient_visual(selection)
            selection["candidate_reason_text"] = (
                (selection.get("candidate_reason_text") or "")
                + " | deferred: crop QA hard-fail (extreme/missing/invalid visual)"
            ).strip(" |")
            # Re-evaluate QA metadata against deferred outcome (still record FAIL gates)
            qa["deferred_due_to_crop_qa"] = True

    links = (selection.get("deterministic_intent") or {}).get("evidence_links") or {}
    win = ((evidence or {}).get("evidence_window") or {}).get("bbox")
    excluded = ((evidence or {}).get("excluded_rejected_evidence") or {})

    manifest = {
        "candidate_id": selection["candidate_id"],
        "beam_id": beam_id,
        "annotation_id": selection.get("annotation_id"),
        "raw_text": selection.get("raw_text"),
        "normalized_text": (selection.get("deterministic_intent") or {}).get(
            "normalized_text"
        ),
        "quantity_status": (selection.get("deterministic_intent") or {}).get(
            "quantity_status"
        ),
        "quantity_value": (selection.get("deterministic_intent") or {}).get(
            "quantity_value"
        ),
        "diameter_value_mm": (selection.get("deterministic_intent") or {}).get(
            "diameter_value_mm"
        ),
        "semantic_type": (selection.get("deterministic_intent") or {}).get(
            "semantic_type"
        ),
        "reinforcement_role": (selection.get("deterministic_intent") or {}).get(
            "reinforcement_role"
        ),
        "outcome": selection.get("outcome"),
        "candidate_priority": selection.get("candidate_priority"),
        "candidate_reason_codes": selection.get("candidate_reason_codes"),
        "candidate_reason_text": selection.get("candidate_reason_text"),
        "candidate_normalization_hint": selection.get("candidate_normalization_hint"),
        "leader_id": links.get("leader_id"),
        "ownership_id": links.get("ownership_id"),
        "source_handle": links.get("source_handle"),
        "evidence_id": links.get("evidence_id"),
        "crop_local_path": str(local_path) if has_visual else None,
        "crop_beam_context_path": str(beam_ctx_path) if has_visual else None,
        "crop_bounds": win,
        "crop_dimensions_mm": {
            "w_mm": qa.get("crop_width_mm"),
            "h_mm": qa.get("crop_height_mm"),
        },
        "image_dimensions_px": {
            "w": qa.get("image_width_px"),
            "h": qa.get("image_height_px"),
        },
        "crop_qa_status": qa.get("overall"),
        "crop_qa": qa,
        "excluded_evidence_summary": {
            "rejected_bars": excluded.get("bars") or [],
            "rejected_leaders": excluded.get("leaders") or [],
            "basis": excluded.get("basis"),
        },
        "deterministic_intent": selection.get("deterministic_intent"),
        "vision_candidate_context": {
            "local_crop": "P2.5.0 engineering_crop (accepted-evidence window)",
            "beam_context_crop": "Same verified evidence window (LEVEL B == LEVEL A source)",
            "note": "No new coordinate system; rejected PhysicalBars excluded upstream",
        },
        "provenance": {
            "phase": "P2.5.2",
            "source_quantity_intent": (selection.get("deterministic_intent") or {}).get(
                "intent_id"
            ),
            "source_evidence_beam": beam_id,
            "p250_evidence_path": str(p250_beams_root / beam_id / "evidence.json"),
        },
        "future_vision_status": VISION_STATUS_PENDING,
    }

    _dump(out_dir / "manifest.json", manifest)
    _dump(
        out_dir / "metadata.json",
        {
            "selection": {
                k: selection[k]
                for k in selection
                if k != "deterministic_intent"
            },
            "crop_qa": qa,
            "has_visual": has_visual,
        },
    )
    return manifest
