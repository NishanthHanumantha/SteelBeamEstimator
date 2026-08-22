"""Discover reusable Fifth Set Vision artefacts. Replay only. Do not call Claude."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.discovery import is_live_vision_observation
from PhaseP2610D1_vision_semantic_contract_hybrid_foundation.vision_normalizer import extract_vision_payload


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_fifth_token(text: str) -> bool:
    t = str(text or "").lower()
    return "fifth" in t or "5th" in t


def discover_vision_artefacts(v10: Path) -> Dict[str, Any]:
    root = Path(v10) / "data" / "output"
    by_id: Dict[str, Dict[str, Any]] = {}
    scanned = 0
    unusable = 0
    api_failed = 0
    skipped_other_set = 0

    p267 = root / "PhaseP267_live_semantic_arbitration" / "raw_responses"
    if p267.exists():
        for path in sorted(p267.glob("*.json")):
            scanned += 1
            if not _is_fifth_token(path.name):
                skipped_other_set += 1
                continue
            payload = _load(path)
            if not isinstance(payload, dict):
                continue
            if not _is_fifth_token(str(payload.get("set_key") or path.name)):
                skipped_other_set += 1
                continue
            bid = str(payload.get("beam_id") or "")
            parsed = payload.get("payload") or payload.get("parsed") or payload.get("raw_response")
            if payload.get("ok") in (False, "False") or payload.get("error_class"):
                api_failed += 1
                if bid:
                    by_id.setdefault(bid, {
                        "beam_id": bid,
                        "usable": False,
                        "unusable_reason": str(payload.get("error_class") or "API_FAILURE"),
                        "source": "P267",
                        "path": str(path),
                        "parsed": None,
                    })
                continue
            if not isinstance(parsed, dict):
                unusable += 1
                continue
            extracted = extract_vision_payload(parsed)
            if not extracted.get("usable"):
                unusable += 1
            if bid:
                by_id[bid] = {
                    "beam_id": bid,
                    "usable": bool(extracted.get("usable")),
                    "unusable_reason": extracted.get("unusable_reason"),
                    "source": "P267",
                    "path": str(path),
                    "parsed": parsed,
                    "extracted": extracted,
                }

    c5 = root / "PhaseP2610C5_stratified_vision_semantic_benchmark" / "review"
    if c5.exists():
        for child in sorted(c5.iterdir()):
            vis_path = child / "vision_result.json"
            if not vis_path.exists():
                continue
            scanned += 1
            vis = _load(vis_path) or {}
            set_key = str(vis.get("set_key") or "")
            if set_key and not _is_fifth_token(set_key):
                skipped_other_set += 1
                continue
            if not set_key:
                skipped_other_set += 1
                continue
            parsed = vis.get("parsed") or {}
            if not is_live_vision_observation(vis, parsed if isinstance(parsed, dict) else {}):
                unusable += 1
                continue
            bid = str(vis.get("beam_id") or child.name)
            extracted = extract_vision_payload(parsed if isinstance(parsed, dict) else {})
            if extracted.get("usable"):
                by_id[bid] = {
                    "beam_id": bid,
                    "usable": True,
                    "source": "C5",
                    "path": str(vis_path),
                    "parsed": parsed,
                    "extracted": extracted,
                }

    usable_ids = sorted(k for k, v in by_id.items() if v.get("usable"))
    return {
        "mode": "OFFLINE_REPLAY",
        "scanned": scanned,
        "api_failed": api_failed,
        "unusable": unusable,
        "skipped_other_set": skipped_other_set,
        "usable_beam_count": len(usable_ids),
        "usable_beam_ids": usable_ids,
        "by_id": by_id,
        "note": "Only Fifth Set tagged artefacts are eligible. Other-set Vision is not reused.",
    }


__all__ = ["discover_vision_artefacts"]
