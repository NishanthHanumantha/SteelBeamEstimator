"""Representative overlays for P2.6.4. Reuses P2.6.3 evidence plus role-gap classes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP263_longitudinal_aware_gate.evidence import _overlay
from PhaseP263_longitudinal_aware_gate.evidence import write_evidence as p263_write_evidence

from .config import COVER_LAYER, DECISION_SKIP, ROLE_GAP_EXPLAINED, ROLE_GAP_REQUIRED


def write_evidence(
    *,
    evidence_root: Path,
    decisions: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    index = p263_write_evidence(
        evidence_root=evidence_root,
        decisions=decisions,
        gated_candidates=gated_candidates,
        baseline_candidates=baseline_candidates,
        false_skips=false_skips,
        false_calls=false_calls or [],
    )
    extra = []
    explained_skip = next(
        (
            d
            for d in decisions
            if d.get("role_gap_status") == ROLE_GAP_EXPLAINED
            and d.get("decision") == DECISION_SKIP
        ),
        None,
    )
    explained_any = next(
        (d for d in decisions if d.get("role_gap_status") == ROLE_GAP_EXPLAINED),
        None,
    )
    required_call = next(
        (
            d
            for d in decisions
            if d.get("role_gap_status") == ROLE_GAP_REQUIRED
            and d.get("longitudinal_coverage") == COVER_LAYER
        ),
        None,
    )
    if explained_skip or explained_any:
        extra.append(("ROLE_GAP_EXPLAINED", explained_skip or explained_any))
    if required_call:
        extra.append(("ROLE_GAP_REQUIRED", required_call))

    for label, item in extra:
        dest_dir = Path(evidence_root) / label.lower()
        dest_dir.mkdir(parents=True, exist_ok=True)
        crop = Path(item.get("crop_path") or "")
        overlay_path = dest_dir / "region_overlay.png"
        if crop.exists():
            _overlay(
                crop,
                overlay_path,
                [
                    label,
                    f"beam {item.get('beam_id')} set {item.get('set_key')}",
                    f"gate {item.get('decision')}",
                    f"reason {item.get('role_gap_reason')}",
                    f"status {item.get('role_gap_status')}",
                ],
            )
        sidecar = {
            "example_class": label,
            "beam_id": item.get("beam_id"),
            "set_key": item.get("set_key"),
            "gate_decision": item.get("decision"),
            "role_gap_status": item.get("role_gap_status"),
            "role_gap_reason": item.get("role_gap_reason"),
            "reason_codes": item.get("reason_codes"),
            "overlay_path": str(overlay_path) if overlay_path.exists() else None,
        }
        (dest_dir / "provenance.json").write_text(
            json.dumps(sidecar, indent=2, default=str), encoding="utf-8"
        )
        index.setdefault("examples", []).append(sidecar)
    index["count"] = len(index.get("examples") or [])
    (Path(evidence_root) / "index.json").write_text(
        json.dumps(index, indent=2, default=str), encoding="utf-8"
    )
    return index


__all__ = ["write_evidence"]
