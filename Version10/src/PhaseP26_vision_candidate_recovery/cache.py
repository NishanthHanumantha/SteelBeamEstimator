"""File cache for P2.6 Vision calls. Key = drawing + region + prompt + model + schema."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import CLAUDE_MODEL, SCHEMA_VERSION


def cache_key(
    *,
    drawing_hash: str,
    region_hash: str,
    prompt_hash: str,
    vision_model: str = CLAUDE_MODEL,
    schema_version: str = SCHEMA_VERSION,
) -> str:
    raw = json.dumps(
        {
            "drawing_hash": drawing_hash,
            "region_hash": region_hash,
            "prompt_hash": prompt_hash,
            "vision_model": vision_model,
            "schema_version": schema_version,
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_path(cache_root: Path, key: str) -> Path:
    return Path(cache_root) / f"{key}.json"


def load_cache(cache_root: Path, key: str) -> Optional[Dict[str, Any]]:
    path = cache_path(cache_root, key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_cache(cache_root: Path, key: str, payload: Dict[str, Any]) -> Path:
    path = cache_path(cache_root, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "cache_key": key,
        "cached_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_metadata": payload.get("request_metadata") or {},
        "raw_response": payload.get("raw_response"),
        "normalized_response": payload.get("normalized_response"),
        "usage": payload.get("usage") or {},
        "error": payload.get("error"),
    }
    path.write_text(json.dumps(doc, indent=2, default=str), encoding="utf-8")
    return path


__all__ = ["cache_key", "cache_path", "load_cache", "save_cache"]
