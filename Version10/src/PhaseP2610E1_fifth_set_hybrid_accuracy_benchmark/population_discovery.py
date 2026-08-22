"""Discover the Fifth Set population from set metadata / web-run names. No beam-ID tables."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseQA2B0_pipeline_integration.pipeline_paths import resolve_latest_web_run


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _repo_root(v10: Path) -> Path:
    return Path(v10).resolve().parent


def discover_fifth_web_run(v10: Path) -> Dict[str, Any]:
    web = Path(v10) / "data" / "web_runs"
    if not web.exists():
        return {"ok": False, "reason": "WEB_RUNS_UNAVAILABLE", "run_root": None, "set_key": None}
    tokens = ("fifth", "5th")
    named = [
        p
        for p in web.iterdir()
        if p.is_dir() and p.name.lower().startswith("qa2_") and any(t in p.name.lower() for t in tokens)
    ]
    if named:
        run = sorted(named, key=lambda p: p.name)[-1]
        m = re.search(r"qa2_([A-Za-z]+)", run.name, re.I)
        set_key = m.group(1) if m else None
        return {
            "ok": True,
            "reason": None,
            "run_root": str(run),
            "set_key": set_key,
            "discovery": "WEB_RUN_NAME_TOKEN",
            "folder_name": run.name,
        }
    for key in ("Fifth", "5th"):
        run = resolve_latest_web_run(web, key)
        if run is not None:
            return {
                "ok": True,
                "reason": None,
                "run_root": str(run),
                "set_key": key,
                "discovery": "RESOLVE_LATEST_WEB_RUN",
                "folder_name": Path(run).name,
            }
    return {"ok": False, "reason": "FIFTH_WEB_RUN_UNAVAILABLE", "run_root": None, "set_key": None}


def discover_estimator_workbook(v10: Path) -> Optional[Path]:
    test_input = _repo_root(v10) / "Test_Input"
    if not test_input.exists():
        return None
    tokens = ("5th", "fifth")
    folders: List[Path] = []
    for child in sorted(test_input.iterdir()):
        if not child.is_dir():
            continue
        name = child.name.lower()
        if any(t in name for t in tokens):
            folders.append(child)
            for nested in child.rglob("*"):
                if nested.is_dir() and "estimator" in nested.name.lower():
                    folders.append(nested)
    candidates: List[Path] = []
    seen = set()
    for folder in folders:
        for path in folder.glob("*.xlsx"):
            if path.name.startswith("~$"):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def load_r13_catalog(run_root: Optional[str]) -> Dict[str, Any]:
    if not run_root:
        return {"ok": False, "reason": "RUN_ROOT_UNAVAILABLE", "by_id": {}, "path": None}
    path = Path(run_root) / "data" / "output" / "PhaseR1.3_pipeline_integration" / "beam_reinforcement_models_production.json"
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
    unique = sorted({str(v.get("beam_id") or k) for k, v in by_id.items() if isinstance(v, dict)})
    unique = [b for b in unique if b]
    unique = sorted(set(unique))
    return {
        "ok": bool(unique),
        "reason": None if unique else "R13_MODELS_EMPTY",
        "by_id": by_id,
        "beam_ids": unique,
        "path": str(path),
        "run_root": run_root,
    }


def discover_population(v10: Path) -> Dict[str, Any]:
    run = discover_fifth_web_run(v10)
    catalog = load_r13_catalog(run.get("run_root"))
    est = discover_estimator_workbook(v10)
    return {
        "ok": bool(run.get("ok")) and bool(catalog.get("ok")) and est is not None,
        "drawing_set": "Fifth Set Drawings",
        "set_key": run.get("set_key"),
        "population_source": run.get("discovery"),
        "run_root": run.get("run_root"),
        "run_folder": run.get("folder_name"),
        "r13_path": catalog.get("path"),
        "model_beam_ids": catalog.get("beam_ids") or [],
        "model_beam_count": len(catalog.get("beam_ids") or []),
        "estimator_path": str(est) if est else None,
        "catalog": catalog,
        "reason": None if (run.get("ok") and catalog.get("ok") and est) else (run.get("reason") or catalog.get("reason") or "ESTIMATOR_UNAVAILABLE"),
    }


__all__ = [
    "discover_estimator_workbook",
    "discover_fifth_web_run",
    "discover_population",
    "load_r13_catalog",
]
