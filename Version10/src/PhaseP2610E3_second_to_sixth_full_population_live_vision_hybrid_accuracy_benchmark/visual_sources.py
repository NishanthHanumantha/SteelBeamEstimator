"""Per-set visual source discovery. Other-set crops are never reused."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP261_stratified_vision_candidate_recovery.set_artefacts import crop_path as qa30_crop_path

from .config import QA30_DIRNAME
from .sets import competing_tokens, name_matches_set, tokens_for


def _sha(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_belongs_to_set(path: Path, set_key: str) -> bool:
    text = str(path).replace("\\", "/").lower()
    own = tokens_for(set_key)
    if any(tok in text for tok in own):
        other_folder = False
        for tok in competing_tokens(set_key):
            if f"/{tok}_set_" in text or f"/{tok} set" in text or f"qa2_{tok}" in text:
                other_folder = True
                break
        if other_folder and not any(f"/{t}_set_" in text or f"qa2_{t}" in text for t in own):
            return False
        return True
    return False


def t183_crop(run_root: Optional[str], beam_id: str) -> Optional[Path]:
    if not run_root:
        return None
    return (
        Path(run_root)
        / "data"
        / "output"
        / "PhaseT183_shared_engineering_ownership"
        / "RenderedBeams"
        / f"{beam_id}_render.png"
    )


def resolve_crop(*, v10: Path, set_key: str, beam_id: str, run_root: Optional[str]) -> Dict[str, Any]:
    qa = qa30_crop_path(v10, set_key, beam_id)
    if qa.exists() and qa.is_file() and qa.stat().st_size > 0:
        if path_belongs_to_set(qa, set_key):
            return {
                "available": True,
                "reason": None,
                "path": str(qa),
                "sha256": _sha(qa),
                "bytes": qa.stat().st_size,
                "source": f"QA30_{set_key.upper()}_SHARED_RENDER",
                "set_folder": QA30_DIRNAME,
            }
        return {
            "available": False,
            "reason": "OTHER_SET_PATH_REJECTED",
            "path": str(qa),
            "sha256": None,
        }
    t183 = t183_crop(run_root, beam_id)
    if t183 is not None and t183.exists() and t183.is_file() and t183.stat().st_size > 0:
        if run_root and name_matches_set(Path(run_root).name, set_key):
            return {
                "available": True,
                "reason": None,
                "path": str(t183),
                "sha256": _sha(t183),
                "bytes": t183.stat().st_size,
                "source": f"T183_{set_key.upper()}_RENDER",
                "set_folder": Path(run_root).name,
            }
        return {
            "available": False,
            "reason": "OTHER_SET_PATH_REJECTED",
            "path": str(t183),
            "sha256": None,
        }
    return {
        "available": False,
        "reason": "RENDER_MISSING",
        "path": str(qa),
        "sha256": None,
    }


def discover_visual_sources(
    v10: Path, *, set_key: str, beam_ids: List[str], run_root: Optional[str]
) -> Dict[str, Any]:
    by_id: Dict[str, Dict[str, Any]] = {}
    skipped_other_set = 0
    missing = 0
    available = 0
    for bid in beam_ids:
        row = resolve_crop(v10=v10, set_key=set_key, beam_id=str(bid), run_root=run_root)
        row["beam_id"] = str(bid)
        row["set_key"] = set_key
        if row.get("reason") == "OTHER_SET_PATH_REJECTED":
            skipped_other_set += 1
        elif not row.get("available"):
            missing += 1
        else:
            available += 1
        by_id[str(bid)] = row
    return {
        "ok": True,
        "set_key": set_key,
        "available_count": available,
        "missing_count": missing,
        "skipped_other_set": skipped_other_set,
        "by_id": by_id,
        "discovery_method": "QA30_THEN_T183_SET_TOKEN",
        "note": "Other-set crops are never used as Vision evidence for this set.",
    }


__all__ = ["discover_visual_sources", "path_belongs_to_set", "resolve_crop"]
