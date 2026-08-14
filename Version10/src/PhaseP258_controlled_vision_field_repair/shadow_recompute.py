"""Isolated shadow VB.1 recomputation. Never overwrites production artefacts."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP231_controlled_engineering_recompute.sandbox import prepare_sandbox
from PhaseP231_controlled_engineering_recompute.vb1_runner import run_vb1_excel

from .config import MODEL_VERSION, PHASE_ID, PRODUCTION_WRITE


def write_patched_r13(sandbox_root: Path, patched_doc: Dict[str, Any]) -> Path:
    dest = (
        Path(sandbox_root)
        / "data"
        / "output"
        / "PhaseR1.3_pipeline_integration"
        / "beam_reinforcement_models_production.json"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(patched_doc, indent=2, default=str), encoding="utf-8")
    return dest


def run_shadow_recompute(
    *,
    engine_root: Path,
    source_run_root: Path,
    ownership: Dict[str, Any],
    patched_r13: Dict[str, Any],
    sandbox_root: Path,
    scoped: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Copy Fifth Set R1.3/context into an isolated sandbox, overlay patched models,
    then run the existing VB.1 Excel generator.
    """
    prep = prepare_sandbox(
        sandbox_root=sandbox_root,
        source_run_root=source_run_root,
        ownership=ownership,
        scoped=scoped,
        label="P258_VISION_ASSISTED",
    )
    r13_path = write_patched_r13(sandbox_root, patched_r13)
    marker = Path(sandbox_root) / "P258_SANDBOX.json"
    marker.write_text(
        json.dumps(
            {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "production_write": PRODUCTION_WRITE,
                "source_run_root": str(source_run_root),
                "patched_r13": str(r13_path),
                "historical_production_mutated": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    vb1 = run_vb1_excel(engine_root=engine_root, sandbox_run_root=sandbox_root)
    return {
        "sandbox": prep,
        "vb1": vb1,
        "patched_r13": str(r13_path),
        "production_write": False,
        "success": bool(vb1.get("success")),
    }


def copy_isolated(src: Path, dest: Path) -> Optional[str]:
    src = Path(src)
    dest = Path(dest)
    if not src.exists():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return str(dest)


__all__ = ["copy_isolated", "run_shadow_recompute", "write_patched_r13"]
