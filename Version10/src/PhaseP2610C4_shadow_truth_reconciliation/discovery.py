"""Discover C.3 six-beam control population from predecessor artefacts. No beam-ID tables."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import C3_SIX_BEAM_NAME, P2610C3_OUTPUT_DIRNAME


def c3_output_root(v10: Path) -> Path:
    return Path(v10) / "data" / "output" / P2610C3_OUTPUT_DIRNAME


def load_six_beam_control(v10: Path) -> Dict[str, Any]:
    path = c3_output_root(v10) / C3_SIX_BEAM_NAME
    if not path.exists():
        return {"ok": False, "path": str(path), "rows": [], "availability": "MISSING"}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = list(payload.get("rows") or [])
    return {
        "ok": True,
        "path": str(path),
        "rows": rows,
        "technically_valid": payload.get("technically_valid"),
        "availability": "AVAILABLE",
    }


def control_beam_ids(control: Dict[str, Any]) -> List[str]:
    ids = []
    for row in control.get("rows") or []:
        bid = row.get("beam_id")
        if bid and bid not in ids:
            ids.append(str(bid))
    return ids


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else {"_list": data}


__all__ = ["c3_output_root", "control_beam_ids", "load_json", "load_six_beam_control"]
