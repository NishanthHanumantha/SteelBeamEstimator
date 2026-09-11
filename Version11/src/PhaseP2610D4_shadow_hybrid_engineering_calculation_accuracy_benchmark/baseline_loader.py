"""Load frozen deterministic baseline steel weights. Do not recompute production."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _y_map(raw: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        try:
            out[str(k).upper()] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def load_deterministic_baseline(*, run_root: Optional[str], beam_ids: list) -> Dict[str, Any]:
    if not run_root:
        return {"ok": False, "reason": "RUN_ROOT_UNAVAILABLE", "by_id": {}, "path": None}
    path = Path(run_root) / "data" / "output" / "Production_Output" / "steel_weight_summary.json"
    payload = _load(path)
    if not isinstance(payload, dict):
        return {"ok": False, "reason": "BASELINE_UNAVAILABLE", "by_id": {}, "path": str(path)}
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in payload.get("beam_weights") or []:
        if not isinstance(row, dict) or not row.get("beam_id"):
            continue
        bid = str(row.get("beam_id"))
        by_id[bid] = {
            "beam_id": bid,
            "total_weight_kg": float(row.get("total_weight_kg") or 0.0),
            "weight_by_diameter": _y_map(row.get("weight_by_diameter")),
            "source": "FROZEN_STEEL_WEIGHT_SUMMARY",
            "path": str(path),
        }
    missing = [b for b in beam_ids if b not in by_id]
    return {
        "ok": True,
        "reason": None,
        "path": str(path),
        "formula": payload.get("formula"),
        "by_id": by_id,
        "missing_beam_ids_count": len(missing),
        "note": "Frozen deterministic baseline. Not recalculated by D.4.",
    }


__all__ = ["load_deterministic_baseline"]
