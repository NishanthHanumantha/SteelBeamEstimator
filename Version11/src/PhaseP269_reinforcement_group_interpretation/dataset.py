"""Load the six-beam benchmark artefacts. Read-only. No resampling."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseQA2B0_pipeline_integration.pipeline_paths import resolve_latest_web_run

from .config import BENCHMARK_BEAMS, TARGET_BEAMS

_V10 = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_set_run(version10_root: Path, set_key: str) -> Path:
    web = Path(version10_root) / "data" / "web_runs"
    run = resolve_latest_web_run(web, set_key)
    if run is None:
        raise FileNotFoundError(f"no web_run for set_key={set_key!r} under {web}")
    return run


def load_r13_model(run_root: Path, beam_id: str) -> Dict[str, Any]:
    path = Path(run_root) / "data" / "output" / "PhaseR1.3_pipeline_integration" / "beam_reinforcement_models_production.json"
    data = _load_json(path)
    models = data.get("models") if isinstance(data, dict) else data
    if isinstance(models, dict):
        hit = models.get(beam_id)
        if isinstance(hit, dict):
            return hit
        models = list(models.values())
    for model in models or []:
        if isinstance(model, dict) and str(model.get("beam_id")) == beam_id:
            return model
    return {}


def load_r1_annotations(run_root: Path, beam_id: str) -> List[Dict[str, Any]]:
    path = Path(run_root) / "data" / "output" / "PhaseR.1_generalized_reinforcement_discovery" / "reinforcement_annotations.json"
    data = _load_json(path)
    by_beam = (data.get("by_beam") or {}) if isinstance(data, dict) else {}
    rows = by_beam.get(beam_id) or []
    return [r for r in rows if isinstance(r, dict)]


def load_benchmark_targets(version10_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    v10 = Path(version10_root or _V10).resolve()
    out: List[Dict[str, Any]] = []
    for set_key, beam_id in BENCHMARK_BEAMS:
        run = resolve_set_run(v10, set_key)
        model = load_r13_model(run, beam_id)
        anns = load_r1_annotations(run, beam_id)
        out.append(
            {
                "set_key": set_key,
                "beam_id": beam_id,
                "run_root": str(run),
                "r13_model": model,
                "r1_annotations": anns,
                "model_found": bool(model),
                "annotation_count": len(anns),
            }
        )
    if len(out) != TARGET_BEAMS:
        raise RuntimeError(f"expected {TARGET_BEAMS} benchmark beams, loaded {len(out)}")
    return out


def load_control_overlay(package_dir: Optional[Path] = None) -> Dict[Tuple[str, str], Dict[str, Any]]:
    path = Path(package_dir or Path(__file__).resolve().parent) / "fixtures" / "benchmark_reference.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in data.get("beams") or []:
        if not isinstance(row, dict):
            continue
        out[(str(row.get("set_key")), str(row.get("beam_id")))] = row
    return out


__all__ = [
    "load_benchmark_targets",
    "load_control_overlay",
    "load_r13_model",
    "load_r1_annotations",
    "resolve_set_run",
]
