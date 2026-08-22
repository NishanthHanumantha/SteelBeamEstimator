"""Discover D.3 population dynamically. No hardcoded beam IDs. No hardcoded size."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    BINDING_RESULTS_NAME,
    D3_RESULTS_NAME,
    P2610B1_OUTPUT_DIRNAME,
    P2610D2_OUTPUT_DIRNAME,
    P2610D3_OUTPUT_DIRNAME,
    POPULATION_MANIFEST_NAME,
)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def d3_output_root(v10: Path) -> Path:
    return Path(v10) / "data" / "output" / P2610D3_OUTPUT_DIRNAME


def load_d3_population(v10: Path) -> Dict[str, Any]:
    root = d3_output_root(v10)
    payload = _load(root / POPULATION_MANIFEST_NAME)
    if not isinstance(payload, dict):
        slim = _load(root / D3_RESULTS_NAME)
        payload = (slim or {}).get("population") if isinstance(slim, dict) else None
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "reason": "D3_POPULATION_UNAVAILABLE",
            "records": [],
            "beam_ids": [],
            "discovered_count": 0,
        }
    records = list(payload.get("records") or [])
    ids: List[str] = []
    if records:
        for rec in records:
            if not isinstance(rec, dict):
                continue
            bid = str(rec.get("beam_id") or "")
            if bid and bid not in ids:
                ids.append(bid)
    else:
        for bid in payload.get("beam_ids") or []:
            bid = str(bid)
            if bid and bid not in ids:
                ids.append(bid)
    unique = len(ids)
    artefact_count = payload.get("discovered_count")
    reason = None
    ok = True
    if unique == 0:
        reason = "D3_POPULATION_EMPTY"
        ok = False
    elif records and unique != len(records):
        reason = "D3_POPULATION_DUPLICATE_IDS"
        ok = False
    elif artefact_count is not None and int(artefact_count) != unique:
        reason = "D3_POPULATION_SIZE_MISMATCH"
        ok = False
    return {
        "ok": ok,
        "reason": reason,
        "artefact_discovered_count": artefact_count,
        "discovered_count": unique,
        "record_count": len(records) if records else unique,
        "records": records,
        "beam_ids": ids,
        "source_path": str(root / POPULATION_MANIFEST_NAME),
    }


def load_d3_bindings(v10: Path) -> Dict[str, Any]:
    root = d3_output_root(v10)
    payload = _load(root / BINDING_RESULTS_NAME)
    if not isinstance(payload, list) or not payload:
        review = root / "review"
        rows = []
        if review.exists():
            for child in sorted(review.iterdir()):
                hit = _load(child / "engineering_binding_result.json")
                if isinstance(hit, dict) and hit.get("beam_id"):
                    rows.append(hit)
        payload = rows
    if not isinstance(payload, list) or not payload:
        return {"ok": False, "reason": "D3_BINDINGS_UNAVAILABLE", "by_id": {}, "rows": []}
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in payload:
        if isinstance(row, dict) and row.get("beam_id"):
            by_id[str(row.get("beam_id"))] = row
    if not by_id:
        return {"ok": False, "reason": "D3_BINDINGS_UNAVAILABLE", "by_id": {}, "rows": []}
    return {"ok": True, "reason": None, "by_id": by_id, "rows": list(by_id.values())}


def load_d2_hybrids(v10: Path) -> Dict[str, Any]:
    root = Path(v10) / "data" / "output" / P2610D2_OUTPUT_DIRNAME
    payload = _load(root / "hybrid_beam_results.json")
    if not isinstance(payload, list):
        return {"ok": False, "reason": "D2_HYBRID_UNAVAILABLE", "by_id": {}}
    by_id = {str(r.get("beam_id")): r for r in payload if isinstance(r, dict) and r.get("beam_id")}
    return {"ok": bool(by_id), "by_id": by_id}


def discover_set_key(v10: Path) -> Optional[str]:
    path = Path(v10) / "data" / "output" / P2610B1_OUTPUT_DIRNAME / "population_manifest.json"
    payload = _load(path)
    if isinstance(payload, dict) and payload.get("set_key"):
        return str(payload.get("set_key"))
    return None


def load_r13_catalog(v10: Path) -> Dict[str, Any]:
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
        "run_root": str(run),
        "set_key": set_key,
    }


__all__ = [
    "d3_output_root",
    "discover_set_key",
    "load_d2_hybrids",
    "load_d3_bindings",
    "load_d3_population",
    "load_r13_catalog",
]
