"""Discover Fourth Set population from existing artefacts. No DXF. No beam-ID tables."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    C3_GATE_MANIFEST_NAME,
    C3_SIX_BEAM_NAME,
    P2610B1_OUTPUT_DIRNAME,
    P2610C1C2_OUTPUT_DIRNAME,
    P2610C3_OUTPUT_DIRNAME,
    P269_OUTPUT_DIRNAME,
    POPULATION_MANIFEST_NAME,
    SELECTION_MANIFEST_NAME,
)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def discover_fourth_set(v10: Path) -> Dict[str, Any]:
    pop_path = Path(v10) / "data" / "output" / P2610B1_OUTPUT_DIRNAME / POPULATION_MANIFEST_NAME
    payload = _load(pop_path)
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "reason": "FOURTH_SET_PROVENANCE_UNAVAILABLE",
            "path": str(pop_path),
            "beam_ids": [],
            "set_key": None,
        }
    set_key = str(payload.get("set_key") or "")
    if set_key != "Fourth":
        return {
            "ok": False,
            "reason": "FOURTH_SET_PROVENANCE_UNAVAILABLE",
            "path": str(pop_path),
            "beam_ids": [],
            "set_key": set_key or None,
            "note": "population_manifest.set_key is not Fourth",
        }
    ids: List[str] = []
    for row in payload.get("beams") or []:
        if str(row.get("set_key") or set_key) != "Fourth":
            continue
        bid = row.get("beam_id")
        if bid and str(bid) not in ids:
            ids.append(str(bid))
    if not ids:
        return {
            "ok": False,
            "reason": "FOURTH_SET_PROVENANCE_UNAVAILABLE",
            "path": str(pop_path),
            "beam_ids": [],
            "set_key": set_key,
        }
    return {
        "ok": True,
        "reason": None,
        "path": str(pop_path),
        "set_key": set_key,
        "beam_ids": ids,
        "source_dxf": payload.get("source_dxf"),
        "unique_beam_ids": payload.get("unique_beam_ids"),
        "discovery_method": "P2610B1_population_manifest.set_key",
    }


def load_selection_manifest(v10: Path) -> List[Dict[str, Any]]:
    path = Path(v10) / "data" / "output" / P2610C1C2_OUTPUT_DIRNAME / SELECTION_MANIFEST_NAME
    payload = _load(path)
    return payload if isinstance(payload, list) else []


def load_c3_gate_by_id(v10: Path) -> Dict[str, Dict[str, Any]]:
    path = Path(v10) / "data" / "output" / P2610C3_OUTPUT_DIRNAME / C3_GATE_MANIFEST_NAME
    payload = _load(path)
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(payload, list):
        for row in payload:
            bid = row.get("beam_id")
            if bid:
                out[str(bid)] = row
    return out


def load_prior_control_ids(v10: Path) -> List[str]:
    path = Path(v10) / "data" / "output" / P2610C3_OUTPUT_DIRNAME / C3_SIX_BEAM_NAME
    payload = _load(path)
    ids: List[str] = []
    for row in (payload or {}).get("rows") or []:
        bid = row.get("beam_id")
        if bid and str(bid) not in ids:
            ids.append(str(bid))
    return ids


def p269_inventory_path(v10: Path, set_key: str, beam_id: str) -> Path:
    return (
        Path(v10)
        / "data"
        / "output"
        / P269_OUTPUT_DIRNAME
        / "inventories"
        / f"{set_key}_{beam_id}.json"
    )


def load_p269_inventory(v10: Path, set_key: str, beam_id: str) -> Optional[Dict[str, Any]]:
    path = p269_inventory_path(v10, set_key, beam_id)
    payload = _load(path)
    return payload if isinstance(payload, dict) else None


def load_r13_detected_by_beam(v10: Path, set_key: str) -> Dict[str, Any]:
    """Read-only R1.3 production models for the discovered set. Does not mutate production."""
    from PhaseP269_reinforcement_group_interpretation.dataset import resolve_set_run
    from PhaseP269_reinforcement_group_interpretation.extractor import extract_detected_groups

    try:
        run = resolve_set_run(v10, set_key)
    except Exception as exc:
        return {"ok": False, "reason": str(exc), "run_root": None, "by_beam": {}}
    path = Path(run) / "data" / "output" / "PhaseR1.3_pipeline_integration" / "beam_reinforcement_models_production.json"
    payload = _load(path)
    if not isinstance(payload, dict) and not isinstance(payload, list):
        return {"ok": False, "reason": "R13_MODEL_UNAVAILABLE", "run_root": str(run), "by_beam": {}}
    models = payload.get("models") if isinstance(payload, dict) else payload
    if isinstance(models, dict):
        model_list = list(models.values())
    else:
        model_list = list(models or [])
    by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for model in model_list:
        if not isinstance(model, dict):
            continue
        bid = str(model.get("beam_id") or "")
        if not bid:
            continue
        by_beam[bid] = extract_detected_groups(model)
    return {
        "ok": True,
        "reason": None,
        "run_root": str(run),
        "path": str(path),
        "by_beam": by_beam,
        "note": "Read-only R1.3 evidence. No production mutation.",
    }


__all__ = [
    "discover_fourth_set",
    "load_c3_gate_by_id",
    "load_p269_inventory",
    "load_prior_control_ids",
    "load_r13_detected_by_beam",
    "load_selection_manifest",
    "p269_inventory_path",
]
