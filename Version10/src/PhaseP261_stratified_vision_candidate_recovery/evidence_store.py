"""Visual evidence provenance for representative P2.6.1 candidates. No production write."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import GT_AMBIGUOUS, GT_DUPLICATE, GT_TRUE_RECOVERY, GT_UNSUPPORTED


def _overlay(src: Path, dest: Path, lines: List[str]) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        shutil.copy2(src, dest)
        return False
    im = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    y = 8
    draw.rectangle((4, 4, im.width - 4, 18 + 16 * len(lines)), fill=(0, 0, 0))
    for line in lines:
        draw.text((10, y), line[:90], fill=(255, 255, 0), font=font)
        y += 16
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    return True


def _pick(candidates: List[Dict[str, Any]], pred) -> Optional[Dict[str, Any]]:
    for cand in candidates:
        if pred(cand):
            return cand
    return None


def write_evidence(
    *,
    evidence_root: Path,
    candidates: List[Dict[str, Any]],
    regions_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    evidence_root = Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    wanted: Dict[str, Optional[Dict[str, Any]]] = {
        "TRUE_RECOVERY_STIRRUP": _pick(
            candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY
            and str(c.get("candidate_type") or "").upper() == "STIRRUP",
        ),
        "TRUE_RECOVERY_LONGITUDINAL": _pick(
            candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY
            and "LONGITUDINAL" in str(c.get("candidate_type") or "").upper(),
        ),
        "DUPLICATE": _pick(candidates, lambda c: c.get("gt_match_status") == GT_DUPLICATE),
        "UNSUPPORTED": _pick(candidates, lambda c: c.get("gt_match_status") == GT_UNSUPPORTED),
        "AMBIGUOUS": _pick(candidates, lambda c: c.get("gt_match_status") == GT_AMBIGUOUS),
        "EASY_CONTROL": _pick(candidates, lambda c: c.get("stratum") == "EASY"),
        "NORMAL_CASE": _pick(candidates, lambda c: c.get("stratum") == "NORMAL"),
    }

    written: List[Dict[str, Any]] = []
    missing = [k for k, v in wanted.items() if v is None]
    for label, cand in wanted.items():
        if cand is None:
            continue
        region = regions_by_id.get(cand.get("region_id") or "") or {}
        crop = Path(region.get("crop_path") or "")
        dest_dir = evidence_root / str(cand.get("candidate_id", "unknown")).replace("::", "__")
        dest_dir.mkdir(parents=True, exist_ok=True)
        overlay_path = dest_dir / "region_overlay.png"
        if crop.exists():
            _overlay(
                crop,
                overlay_path,
                [
                    f"ID {cand.get('candidate_id')}",
                    f"beam {cand.get('beam_id')}  type {cand.get('candidate_type')}",
                    f"set {cand.get('source_set')}  stratum {cand.get('stratum')}",
                    f"text {cand.get('annotation_text')}",
                    f"det {cand.get('deterministic_match_status')}  gt {cand.get('gt_match_status')}",
                    f"assoc {cand.get('beam_association')}  example {label}",
                ],
            )
        sidecar = {
            "example_class": label,
            "candidate_id": cand.get("candidate_id"),
            "beam_id": cand.get("beam_id"),
            "source_set": cand.get("source_set"),
            "stratum": cand.get("stratum"),
            "annotation_text": cand.get("annotation_text"),
            "candidate_type": cand.get("candidate_type"),
            "role": cand.get("role"),
            "diameter_mm": cand.get("diameter_mm"),
            "quantity": cand.get("quantity"),
            "deterministic_match_status": cand.get("deterministic_match_status"),
            "gt_match_status": cand.get("gt_match_status"),
            "beam_association": cand.get("beam_association"),
            "region_id": cand.get("region_id"),
            "crop_path": str(crop) if crop.exists() else None,
            "overlay_path": str(overlay_path) if overlay_path.exists() else None,
            "decision": cand.get("decision"),
            "evidence_type": cand.get("evidence_type"),
            "raw_vision_response_reference": cand.get("raw_vision_response_reference"),
        }
        (dest_dir / "provenance.json").write_text(
            json.dumps(sidecar, indent=2, default=str), encoding="utf-8"
        )
        written.append(sidecar)

    index = {"examples": written, "count": len(written), "missing_classes": missing}
    (evidence_root / "index.json").write_text(
        json.dumps(index, indent=2, default=str), encoding="utf-8"
    )
    return index


__all__ = ["write_evidence"]
