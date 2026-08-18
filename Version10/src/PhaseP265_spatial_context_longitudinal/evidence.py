"""Representative overlays for P2.6.5 shadow context classes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP264_selective_role_gap_gate.evidence import write_evidence as p264_write_evidence

from .config import STATUS_CALL, STATUS_INSUFFICIENT, STATUS_SKIP


def write_evidence(
    *,
    evidence_root: Path,
    decisions: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    index = p264_write_evidence(
        evidence_root=evidence_root,
        decisions=decisions,
        gated_candidates=gated_candidates,
        baseline_candidates=baseline_candidates,
        false_skips=false_skips,
        false_calls=false_calls or [],
    )
    from PhaseP263_longitudinal_aware_gate.evidence import _overlay

    wanted = [
        ("CONTEXT_SUPPORTS_CALL", lambda d: d.get("context_status") == STATUS_CALL),
        ("CONTEXT_SUPPORTS_SKIP", lambda d: d.get("context_status") == STATUS_SKIP),
        ("CONTEXT_INSUFFICIENT", lambda d: d.get("context_status") == STATUS_INSUFFICIENT),
    ]
    for label, pred in wanted:
        item = next((d for d in decisions if pred(d)), None)
        if item is None:
            continue
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
                    f"p264 {item.get('observed_decision')}",
                    f"ctx {item.get('context_status')}",
                    f"codes {item.get('context_evidence_codes')}",
                ],
            )
        sidecar = {
            "example_class": label,
            "beam_id": item.get("beam_id"),
            "set_key": item.get("set_key"),
            "observed_decision": item.get("observed_decision"),
            "context_status": item.get("context_status"),
            "context_evidence_codes": item.get("context_evidence_codes"),
            "overlay_path": str(overlay_path) if overlay_path.exists() else None,
        }
        (dest_dir / "provenance.json").write_text(json.dumps(sidecar, indent=2, default=str), encoding="utf-8")
        index.setdefault("examples", []).append(sidecar)
    index["count"] = len(index.get("examples") or [])
    (Path(evidence_root) / "index.json").write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")
    return index


__all__ = ["write_evidence"]
