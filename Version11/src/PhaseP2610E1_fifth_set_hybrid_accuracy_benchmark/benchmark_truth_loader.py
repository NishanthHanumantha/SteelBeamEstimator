"""Load Fifth Set estimator truth via QA.2A workbook normalizer. Do not invent values."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .config import TRUTH_ESTIMATOR, TRUTH_NONE


def _qa2a_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "PhaseQA.2A_ground_truth_benchmark"


def _ensure_qa2a() -> None:
    p = str(_qa2a_dir())
    if p not in sys.path:
        sys.path.insert(0, p)


def load_estimator_workbook(path: Optional[Path]):
    _ensure_qa2a()
    from workbook_normalizer import WorkbookNormalizer  # type: ignore

    if path is None or not Path(path).exists():
        return None
    return WorkbookNormalizer().normalize(Path(path), "ESTIMATOR")


def load_benchmark_truth(*, estimator_path: Optional[str]) -> Dict[str, Any]:
    wb = load_estimator_workbook(Path(estimator_path) if estimator_path else None)
    if wb is None:
        return {
            "ok": False,
            "source": TRUTH_NONE,
            "path": estimator_path,
            "beam_count": 0,
            "bar_count": 0,
            "total_weight_kg": None,
            "workbook": None,
        }
    return {
        "ok": True,
        "source": TRUTH_ESTIMATOR,
        "path": str(estimator_path),
        "beam_count": len(wb.beams),
        "bar_count": sum(len(b.bars) for b in wb.beams),
        "total_weight_kg": round(float(wb.total_steel_kg or 0.0), 4),
        "workbook": wb,
    }


__all__ = ["load_benchmark_truth", "load_estimator_workbook"]
