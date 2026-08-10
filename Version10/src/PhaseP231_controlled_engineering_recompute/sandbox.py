"""
Sandbox preparation for baseline / controlled engineering recompute.
MODEL_VERSION: 10.5.6

Never mutates historical web_run T18 or Production_Output.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from .config import MODEL_VERSION, PHASE_ID


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def prepare_sandbox(
    *,
    sandbox_root: Path,
    source_run_root: Path,
    ownership: Dict[str, Any],
    scoped: Optional[Dict[str, Any]],
    label: str,
) -> Dict[str, Any]:
    """
    Build a minimal run_root containing R1.3 models + injected ownership +
    empty Production_Output for VB1.
    """
    sandbox_root = Path(sandbox_root)
    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)
    out = sandbox_root / "data" / "output"
    src_out = Path(source_run_root) / "data" / "output"

    r13_name = "PhaseR1.3_pipeline_integration"
    r13_file = "beam_reinforcement_models_production.json"
    src_r13 = src_out / r13_name / r13_file
    if not src_r13.exists():
        raise FileNotFoundError(f"Missing R1.3 models: {src_r13}")
    _copy_file(src_r13, out / r13_name / r13_file)

    # Optional R2A context if present (VB1 may use it)
    for rel in (
        "PhaseR.2A_engineering_context/EngineeringContext.json",
        "PhaseR2A_engineering_context/EngineeringContext.json",
    ):
        p = src_out / rel
        if p.exists():
            _copy_file(p, out / rel)
            break

    t18 = out / "PhaseT18_beam_ownership"
    t18.mkdir(parents=True, exist_ok=True)
    own_doc = dict(ownership)
    own_doc["p231_sandbox_label"] = label
    own_doc["p231_model_version"] = MODEL_VERSION
    (t18 / "BeamOwnership.json").write_text(
        json.dumps(own_doc, indent=2, default=str), encoding="utf-8"
    )
    if scoped is not None:
        (t18 / "BeamScopedAnnotations.json").write_text(
            json.dumps(scoped, indent=2, default=str), encoding="utf-8"
        )

    prod = out / "Production_Output"
    prod.mkdir(parents=True, exist_ok=True)

    # Marker so we never confuse with historical run
    (sandbox_root / "P231_SANDBOX.json").write_text(
        json.dumps(
            {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "label": label,
                "source_run_root": str(source_run_root),
                "historical_t18_mutated": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "sandbox_root": str(sandbox_root),
        "output_root": str(out),
        "r13_models": str(out / r13_name / r13_file),
        "ownership": str(t18 / "BeamOwnership.json"),
        "production_output": str(prod),
        "label": label,
    }
