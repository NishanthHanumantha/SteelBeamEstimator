"""Generic checkpoint / resume. No beam-ID exception tables."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def checkpoint_path(out_root: Path) -> Path:
    return Path(out_root) / "run_checkpoint.json"


def load_checkpoint(out_root: Path) -> Dict[str, Any]:
    path = checkpoint_path(out_root)
    if not path.exists():
        return {"complete": False, "completed_ids": [], "pending_ids": [], "status": "ABSENT"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"complete": False, "completed_ids": [], "pending_ids": [], "status": "CORRUPT"}
    if not isinstance(data, dict):
        return {"complete": False, "completed_ids": [], "pending_ids": [], "status": "CORRUPT"}
    return data


def write_checkpoint(out_root: Path, *, beam_ids: List[str], completed_ids: List[str], status: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    done = sorted({str(x) for x in completed_ids if x})
    pending = [b for b in beam_ids if str(b) not in set(done)]
    payload = {
        "status": status,
        "complete": status == "COMPLETE" and not pending,
        "completed_ids": done,
        "pending_ids": pending,
        "discovered_count": len(beam_ids),
        "completed_count": len(done),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    dest = checkpoint_path(out_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return payload


__all__ = ["checkpoint_path", "load_checkpoint", "write_checkpoint"]
