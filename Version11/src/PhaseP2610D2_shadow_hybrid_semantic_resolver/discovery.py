"""Load the D.1 benchmark population from artefacts. No beam-ID tables."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    D1_CONTRACT_NAME,
    D1_POPULATION_NAME,
    EXPECTED_POPULATION_SIZE,
    P2610D1_OUTPUT_DIRNAME,
)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def d1_output_root(v10: Path) -> Path:
    return Path(v10) / "data" / "output" / P2610D1_OUTPUT_DIRNAME


def load_authority_contract(v10: Path) -> Dict[str, Any]:
    payload = _load(d1_output_root(v10) / D1_CONTRACT_NAME)
    if not isinstance(payload, dict) or not payload.get("fields"):
        return {"ok": False, "reason": "D1_CONTRACT_UNAVAILABLE", "contract": None}
    return {"ok": True, "reason": None, "contract": payload}


def load_d1_population(v10: Path) -> Dict[str, Any]:
    root = d1_output_root(v10)
    payload = _load(root / D1_POPULATION_NAME)
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "reason": "D1_POPULATION_UNAVAILABLE",
            "expected": EXPECTED_POPULATION_SIZE,
            "records": [],
            "beam_ids": [],
        }
    records = list(payload.get("records") or [])
    ids: List[str] = []
    for rec in records:
        bid = str(rec.get("beam_id") or "")
        if bid and bid not in ids:
            ids.append(bid)
    unique = len(ids)
    ok = unique == EXPECTED_POPULATION_SIZE
    reason = None
    if not records:
        reason = "D1_POPULATION_EMPTY"
        ok = False
    elif unique != EXPECTED_POPULATION_SIZE:
        reason = "D1_POPULATION_SIZE_MISMATCH"
        ok = False
    elif unique != len(records):
        reason = "D1_POPULATION_DUPLICATE_IDS"
        ok = False
    return {
        "ok": ok,
        "reason": reason,
        "expected": EXPECTED_POPULATION_SIZE,
        "discovered_count": unique,
        "record_count": len(records),
        "records": records,
        "beam_ids": ids,
        "source_path": str(root / D1_POPULATION_NAME),
        "c3_count": payload.get("c3_count"),
        "c5_count": payload.get("c5_count"),
    }


__all__ = ["d1_output_root", "load_authority_contract", "load_d1_population"]
