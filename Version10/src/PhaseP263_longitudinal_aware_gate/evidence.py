"""Representative overlays for P2.6.3 longitudinal-aware gate decisions."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    COVER_LAYER,
    COVER_QTY,
    COVER_ROLE,
    DECISION_CALL,
    DECISION_SKIP,
)

GT_DUPLICATE = "DUPLICATE"
GT_TRUE_RECOVERY = "TRUE_RECOVERY"


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


def _is_long(item: Dict[str, Any]) -> bool:
    t = str(
        item.get("candidate_type")
        or item.get("candidate_class")
        or item.get("candidate_class_hint")
        or ""
    ).upper()
    return "LONGITUDINAL" in t


def write_evidence(
    *,
    evidence_root: Path,
    decisions: List[Dict[str, Any]],
    gated_candidates: List[Dict[str, Any]],
    baseline_candidates: List[Dict[str, Any]],
    false_skips: List[Dict[str, Any]],
    false_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    evidence_root = Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    by_id = {d.get("region_id"): d for d in decisions}
    by_beam = {(d.get("set_key"), d.get("beam_id")): d for d in decisions}

    long_fs = [f for f in false_skips if _is_long(f) or "LONGITUDINAL" in str(f.get("candidate_class") or "").upper()]
    long_fc = [f for f in false_calls if _is_long(f) or "LONGITUDINAL" in str(f.get("reason_codes") or "")]

    wanted = {
        "LONGITUDINAL_TRUE_RECOVERY": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY and _is_long(c),
        ),
        "LONGITUDINAL_FALSE_SKIP": long_fs[0] if long_fs else (false_skips[0] if false_skips else None),
        "LONGITUDINAL_FALSE_CALL": long_fc[0] if long_fc else (false_calls[0] if false_calls else None),
        "LONGITUDINAL_DUPLICATE": _pick(
            gated_candidates,
            lambda c: _is_long(c)
            and (
                c.get("gt_match_status") == GT_DUPLICATE
                or c.get("deterministic_match_status") == "ALREADY_DETECTED"
            ),
        ),
        "LONGITUDINAL_QUANTITY_SHORTFALL": _pick(
            decisions,
            lambda d: COVER_QTY in (d.get("coverage_conditions") or [])
            or d.get("longitudinal_coverage") == COVER_QTY,
        ),
        "LONGITUDINAL_ROLE_CONFLICT": _pick(
            decisions,
            lambda d: COVER_ROLE in (d.get("coverage_conditions") or [])
            or COVER_LAYER in (d.get("coverage_conditions") or [])
            or d.get("longitudinal_coverage") in (COVER_ROLE, COVER_LAYER),
        ),
        "STIRRUP_TRUE_RECOVERY": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY
            and str(c.get("candidate_type") or "").upper() == "STIRRUP",
        ),
        "NORMAL_OR_EASY_LONGITUDINAL_RECOVERY": _pick(
            gated_candidates,
            lambda c: c.get("gt_match_status") == GT_TRUE_RECOVERY
            and _is_long(c)
            and c.get("stratum") in ("NORMAL", "EASY"),
        )
        or _pick(
            false_skips,
            lambda c: _is_long(c) and c.get("stratum") in ("NORMAL", "EASY"),
        ),
    }

    written: List[Dict[str, Any]] = []
    missing = [k for k, v in wanted.items() if v is None]
    for label, item in wanted.items():
        if item is None:
            continue
        region_id = item.get("region_id")
        decision = by_id.get(region_id) or by_beam.get((item.get("set_key"), item.get("beam_id"))) or {}
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
                    f"cov {decision.get('longitudinal_coverage')}",
                    f"reasons {item.get('reason_codes') or decision.get('reason_codes')}",
                ],
            )
        sidecar = {
            "example_class": label,
            "beam_id": item.get("beam_id"),
            "set_key": item.get("set_key") or decision.get("set_key"),
            "stratum": item.get("stratum") or item.get("eval_stratum") or decision.get("eval_stratum"),
            "gate_decision": item.get("gate_decision") or decision.get("decision"),
            "reason_codes": item.get("why_gate_skipped")
            or item.get("reason_codes")
            or decision.get("reason_codes"),
            "annotation_text": item.get("annotation") or item.get("annotation_text"),
            "role": item.get("role"),
            "diameter": item.get("diameter"),
            "quantity": item.get("quantity"),
            "production_coverage": item.get("production_coverage") or decision.get("longitudinal_coverage"),
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
