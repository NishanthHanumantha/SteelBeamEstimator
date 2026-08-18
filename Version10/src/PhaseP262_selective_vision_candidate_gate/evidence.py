"""Representative overlays for P2.6.2 gate decisions. No production write."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import DECISION_CALL, DECISION_SKIP

GT_DUPLICATE = "DUPLICATE"
GT_TRUE_RECOVERY = "TRUE_RECOVERY"
GT_UNSUPPORTED = "UNSUPPORTED"


def _overlay(src: Path, dest: Path, lines: List[str]) -> bool:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        if src.exists():
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


def _pick(items: List[Dict[str, Any]], pred) -> Optional[Dict[str, Any]]:
    for it in items:
        if pred(it):
            return it
    return None


def write_evidence(
    *,
    evidence_root: Path,
    decisions: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
) -> Dict[str, Any]:
    evidence_root = Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    by_id = {d.get("region_id"): d for d in decisions}

    wanted = {
        "CALL_TRUE_RECOVERY": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY and c.get("gate_decision") == DECISION_CALL,
        ),
        "CALL_DUPLICATE": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_DUPLICATE
            or c.get("deterministic_match_status") == "ALREADY_DETECTED",
        ),
        "CALL_UNSUPPORTED": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_UNSUPPORTED,
        ),
        "SKIP_CORRECT": _pick(
            decisions,
            lambda d: d.get("decision") == DECISION_SKIP
            and not any(
                f.get("beam_id") == d.get("beam_id") and f.get("set_key") == d.get("set_key")
                for f in false_skips
            ),
        ),
        "SKIP_FALSE_SKIP": false_skips[0] if false_skips else None,
        "STIRRUP_GAP": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY
            and str(c.get("candidate_type") or "").upper() == "STIRRUP",
        ),
        "LONGITUDINAL_GAP": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY
            and "LONGITUDINAL" in str(c.get("candidate_type") or "").upper(),
        ),
        "NORMAL_OR_EASY_RECOVERY": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY
            and c.get("stratum") in ("NORMAL", "EASY"),
        )
        or _pick(false_skips, lambda c: c.get("stratum") == "EASY")
        or _pick(false_skips, lambda c: c.get("stratum") == "NORMAL"),
    }

    written: List[Dict[str, Any]] = []
    missing = [k for k, v in wanted.items() if v is None]
    for label, item in wanted.items():
        if item is None:
            continue
        region_id = item.get("region_id")
        decision = by_id.get(region_id) or {}
        crop = Path(decision.get("crop_path") or "")
        dest_dir = evidence_root / label.lower()
        dest_dir.mkdir(parents=True, exist_ok=True)
        overlay_path = dest_dir / "region_overlay.png"
        if crop.exists():
            _overlay(
                crop,
                overlay_path,
                [
                    f"{label}",
                    f"beam {item.get('beam_id')} set {item.get('set_key') or decision.get('set_key')}",
                    f"gate {item.get('gate_decision') or decision.get('decision')}",
                    f"text {item.get('annotation') or item.get('annotation_text')}",
                    f"gt {item.get('gt_match_status') or item.get('gt_recovery')}",
                    f"reasons {decision.get('reason_codes')}",
                ],
            )
        sidecar = {
            "example_class": label,
            "beam_id": item.get("beam_id"),
            "set_key": item.get("set_key") or decision.get("set_key"),
            "stratum": item.get("stratum") or item.get("eval_stratum") or decision.get("eval_stratum"),
            "gate_decision": item.get("gate_decision") or decision.get("decision"),
            "reason_codes": item.get("why_gate_skipped") or item.get("reason_codes") or decision.get("reason_codes"),
            "annotation_text": item.get("annotation") or item.get("annotation_text"),
            "candidate_type": item.get("candidate_class") or item.get("candidate_type"),
            "gt_match_status": item.get("gt_match_status") or item.get("gt_recovery"),
            "overlay_path": str(overlay_path) if overlay_path.exists() else None,
        }
        (dest_dir / "provenance.json").write_text(
            json.dumps(sidecar, indent=2, default=str), encoding="utf-8"
        )
        written.append(sidecar)

    index = {"examples": written, "count": len(written), "missing_classes": missing}
    (evidence_root / "index.json").write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")
    return index


__all__ = ["write_evidence"]
