"""Load D.2 hybrid artefacts and read-only deterministic engineering catalogs. No DXF. No writes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    D2_HYBRID_NAME,
    D2_POPULATION_NAME,
    EXPECTED_POPULATION_SIZE,
    P2610B1_OUTPUT_DIRNAME,
    P2610D2_OUTPUT_DIRNAME,
    POPULATION_MANIFEST_NAME,
)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def d2_output_root(v10: Path) -> Path:
    return Path(v10) / "data" / "output" / P2610D2_OUTPUT_DIRNAME


def load_d2_population(v10: Path) -> Dict[str, Any]:
    root = d2_output_root(v10)
    payload = _load(root / D2_POPULATION_NAME)
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "reason": "D2_POPULATION_UNAVAILABLE",
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
        reason = "D2_POPULATION_EMPTY"
        ok = False
    elif unique != EXPECTED_POPULATION_SIZE:
        reason = "D2_POPULATION_SIZE_MISMATCH"
        ok = False
    elif unique != len(records):
        reason = "D2_POPULATION_DUPLICATE_IDS"
        ok = False
    return {
        "ok": ok,
        "reason": reason,
        "expected": EXPECTED_POPULATION_SIZE,
        "discovered_count": unique,
        "record_count": len(records),
        "records": records,
        "beam_ids": ids,
        "source_path": str(root / D2_POPULATION_NAME),
    }


def load_d2_hybrids(v10: Path) -> Dict[str, Any]:
    root = d2_output_root(v10)
    payload = _load(root / D2_HYBRID_NAME)
    if not isinstance(payload, list) or not payload:
        review = root / "review"
        rows = []
        if review.exists():
            for child in sorted(review.iterdir()):
                hit = _load(child / "hybrid_result.json")
                if isinstance(hit, dict) and hit.get("beam_id"):
                    rows.append(hit)
        payload = rows
    if not isinstance(payload, list) or not payload:
        return {"ok": False, "reason": "D2_HYBRID_UNAVAILABLE", "by_id": {}, "rows": []}
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in payload:
        if isinstance(row, dict) and row.get("beam_id"):
            by_id[str(row.get("beam_id"))] = row
    if not by_id:
        return {"ok": False, "reason": "D2_HYBRID_UNAVAILABLE", "by_id": {}, "rows": []}
    return {"ok": True, "reason": None, "by_id": by_id, "rows": list(by_id.values())}


def discover_set_key(v10: Path) -> Optional[str]:
    path = Path(v10) / "data" / "output" / P2610B1_OUTPUT_DIRNAME / POPULATION_MANIFEST_NAME
    payload = _load(path)
    if isinstance(payload, dict) and payload.get("set_key"):
        return str(payload.get("set_key"))
    return None


def load_r13_catalog(v10: Path) -> Dict[str, Any]:
    """Read-only R1.3 models keyed by beam_id. Never writes."""
    set_key = discover_set_key(v10)
    if not set_key:
        return {"ok": False, "reason": "SET_KEY_UNAVAILABLE", "by_id": {}, "path": None}
    try:
        from PhaseP269_reinforcement_group_interpretation.dataset import resolve_set_run
    except Exception:
        return {"ok": False, "reason": "R13_RESOLVER_UNAVAILABLE", "by_id": {}, "path": None}
    try:
        run = resolve_set_run(Path(v10), set_key)
    except Exception:
        return {"ok": False, "reason": "R13_RUN_UNAVAILABLE", "by_id": {}, "path": None}
    path = Path(run) / "data" / "output" / "PhaseR1.3_pipeline_integration" / "beam_reinforcement_models_production.json"
    data = _load(path)
    models = data.get("models") if isinstance(data, dict) else data
    by_id: Dict[str, Dict[str, Any]] = {}
    if isinstance(models, dict):
        for k, v in models.items():
            if isinstance(v, dict):
                by_id[str(k)] = v
                bid = v.get("beam_id")
                if bid:
                    by_id[str(bid)] = v
    elif isinstance(models, list):
        for v in models:
            if isinstance(v, dict) and v.get("beam_id"):
                by_id[str(v.get("beam_id"))] = v
    return {
        "ok": bool(by_id),
        "reason": None if by_id else "R13_MODELS_EMPTY",
        "by_id": by_id,
        "path": str(path),
        "set_key": set_key,
    }


__all__ = [
    "d2_output_root",
    "discover_set_key",
    "load_d2_hybrids",
    "load_d2_population",
    "load_r13_catalog",
]
