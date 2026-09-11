"""Discover Fifth Set visual sources. Never reuse other-set PNGs as Fifth evidence."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP261_stratified_vision_candidate_recovery.set_artefacts import crop_path as qa30_crop_path

from .config import OTHER_SET_TOKENS, QA30_DIRNAME, SET_FOLDER_TOKENS


def _is_fifth_path(path: Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    if any(tok in text for tok in OTHER_SET_TOKENS):
        if not any(tok in text for tok in SET_FOLDER_TOKENS):
            return False
        # mixed path: require a Fifth token and reject if a competing set folder wins
        fifth_hit = any(tok in text for tok in SET_FOLDER_TOKENS)
        other_folder = any(f"/{tok}_set_" in text or f"/{tok} set" in text for tok in ("fourth", "sixth", "second", "third"))
        return fifth_hit and not other_folder
    return any(tok in text for tok in SET_FOLDER_TOKENS)


def _sha(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_visual_sources(v10: Path, *, beam_ids: List[str]) -> Dict[str, Any]:
    by_id: Dict[str, Dict[str, Any]] = {}
    skipped_other_set = 0
    missing = 0
    available = 0
    for bid in beam_ids:
        path = qa30_crop_path(v10, "Fifth", bid)
        if not _is_fifth_path(path):
            skipped_other_set += 1
            by_id[str(bid)] = {
                "beam_id": str(bid),
                "available": False,
                "reason": "OTHER_SET_PATH_REJECTED",
                "path": str(path),
                "sha256": None,
            }
            continue
        exists = path.exists() and path.is_file() and path.stat().st_size > 0
        if not exists:
            missing += 1
            by_id[str(bid)] = {
                "beam_id": str(bid),
                "available": False,
                "reason": "RENDER_MISSING",
                "path": str(path),
                "sha256": None,
            }
            continue
        available += 1
        by_id[str(bid)] = {
            "beam_id": str(bid),
            "available": True,
            "reason": None,
            "path": str(path),
            "sha256": _sha(path),
            "bytes": path.stat().st_size,
            "source": "QA30_FIFTH_SHARED_RENDER",
            "set_folder": QA30_DIRNAME,
        }
    return {
        "ok": True,
        "available_count": available,
        "missing_count": missing,
        "skipped_other_set": skipped_other_set,
        "by_id": by_id,
        "discovery_method": "QA30_SET_FOLDER_TOKEN",
        "note": "Other-set crops are never used as Fifth Vision evidence.",
    }


__all__ = ["discover_visual_sources", "_is_fifth_path"]
