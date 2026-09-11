"""Load production R1.3 models from a web run tree. Read-only."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .config import R13_REL, STEEL_SUMMARY_REL


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_r13_catalog(staging: Path) -> Dict[str, Any]:
    path = Path(staging) / R13_REL
    data = _load_json(path)
    models = data.get("models") if isinstance(data, dict) else data
    by_id: Dict[str, Dict[str, Any]] = {}
    if isinstance(models, dict):
        for key, value in models.items():
            if isinstance(value, dict):
                by_id[str(key)] = value
                bid = value.get("beam_id")
                if bid:
                    by_id[str(bid)] = value
    elif isinstance(models, list):
        for value in models:
            if isinstance(value, dict) and value.get("beam_id"):
                by_id[str(value.get("beam_id"))] = value
    unique = sorted(
        {
            str(value.get("beam_id") or key)
            for key, value in by_id.items()
            if isinstance(value, dict) and str(value.get("beam_id") or key)
        }
    )
    return {
        "ok": bool(unique),
        "reason": None if unique else ("R13_MISSING" if data is None else "R13_MODELS_EMPTY"),
        "by_id": by_id,
        "beam_ids": unique,
        "path": str(path),
        "exists": path.is_file(),
    }


def load_steel_fingerprint(staging: Path) -> Dict[str, Any]:
    path = Path(staging) / STEEL_SUMMARY_REL
    data = _load_json(path)
    if not isinstance(data, dict):
        return {"present": False}
    return {
        "present": True,
        "total_beams": data.get("total_beams"),
        "total_bars": data.get("total_bars"),
        "total_weight_kg": data.get("total_weight_kg"),
        "calculation_method": data.get("calculation_method"),
    }
