"""
workbook_adapter.py — Load estimator / model Excel into OfficialWorkbookModel.

Reuses Phase R.1.4 OfficialModelBuilder without modifying it.
MODEL_VERSION: 8.9.0
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional

MODEL_VERSION = "8.9.0"

_R14_DIR = (
    Path(__file__).resolve().parents[1]
    / "PhaseR1_4_production_accuracy_benchmark"
)
_LOADED = False


def _ensure_r14() -> None:
    """Bootstrap Phase R.1.4 modules onto sys.path (flat package layout)."""
    global _LOADED
    if _LOADED:
        return
    src = str(_R14_DIR)
    if src not in sys.path:
        sys.path.insert(0, src)
    _LOADED = True


def load_workbook_model(workbook_path: Path) -> Any:
    """
    Parse an Excel workbook into OfficialWorkbookModel via R.1.4 builder.
    Works for both Estimator Output and Model Estimation_Output.xlsx.
    """
    _ensure_r14()
    from official_model_builder import OfficialModelBuilder  # type: ignore

    return OfficialModelBuilder().build(Path(workbook_path))


def model_summary(wb_model: Any) -> Dict[str, Any]:
    """Lightweight summary dict for logging / JSON."""
    if wb_model is None:
        return {"beam_count": 0, "row_count": 0, "total_kg": 0.0}
    steel = wb_model.steel_summary
    return {
        "beam_count": len(wb_model.beams),
        "row_count": len(wb_model.reinforcement_rows),
        "total_kg": float(getattr(steel, "total_kg", 0.0) or 0.0),
        "total_mt": float(getattr(steel, "total_mt", 0.0) or 0.0),
        "project_name": getattr(getattr(wb_model, "project", None), "project_name", "") or "",
        "sheet_names": list(getattr(getattr(wb_model, "project", None), "sheet_names", []) or []),
    }
