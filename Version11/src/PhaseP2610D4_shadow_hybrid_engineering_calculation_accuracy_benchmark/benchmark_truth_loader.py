"""Load estimator/benchmark truth with explicit provenance. Do not invent truth."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import TRUTH_ESTIMATOR, TRUTH_NONE


def _repo_root(v10: Path) -> Path:
    return Path(v10).resolve().parent


def discover_estimator_workbook(v10: Path) -> Optional[Path]:
    test_input = _repo_root(v10) / "Test_Input"
    if not test_input.exists():
        return None
    hints = ("4th", "fourth")
    folders: List[Path] = []
    for child in sorted(test_input.iterdir()):
        if not child.is_dir():
            continue
        name = child.name.lower()
        if any(h in name for h in hints):
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
            if path.resolve() in seen:
                continue
            seen.add(path.resolve())
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def _parse_estimator(path: Path) -> Dict[str, Dict[str, Any]]:
    folder = Path(__file__).resolve().parents[1] / "PhaseVTEST3_2_estimator_comparison_engine"
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    from estimator_workbook_parser import EstimatorWorkbookParser  # type: ignore

    parser = EstimatorWorkbookParser(path)
    blocks = parser.parse_beam_blocks()
    by_id: Dict[str, Dict[str, Any]] = {}
    for block in blocks:
        bid = str(getattr(block, "beam_id", "") or "").upper()
        if not bid:
            continue
        dia = {}
        raw = getattr(block, "diameter_kg", None) or {}
        for k, v in raw.items():
            try:
                dia[f"Y{int(k)}"] = float(v)
            except (TypeError, ValueError):
                continue
        steel = getattr(block, "total_steel_kg", None)
        if steel is None:
            steel = getattr(block, "steel_kg", None)
        if steel is None:
            steel = sum(dia.values())
        by_id[bid] = {
            "beam_id": bid,
            "total_weight_kg": float(steel or 0.0),
            "weight_by_diameter": dia,
            "source": TRUTH_ESTIMATOR,
            "path": str(path),
            "lines": [
                {
                    "role": getattr(ln, "role", None),
                    "description": getattr(ln, "description", None),
                    "diameter_mm": getattr(ln, "diameter_mm", None),
                    "bar_count": getattr(ln, "bar_count", None),
                    "weight_kg": getattr(ln, "steel_kg", None),
                }
                for ln in (getattr(block, "lines", None) or [])
            ],
        }
    return by_id


def load_benchmark_truth(*, v10: Path, beam_ids: List[str]) -> Dict[str, Any]:
    path = discover_estimator_workbook(v10)
    if path is None:
        return {
            "ok": False,
            "reason": "ESTIMATOR_WORKBOOK_UNAVAILABLE",
            "source": TRUTH_NONE,
            "by_id": {},
            "path": None,
            "coverage": {bid: {"source": TRUTH_NONE, "available": False} for bid in beam_ids},
        }
    try:
        parsed = _parse_estimator(path)
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"ESTIMATOR_PARSE_FAILED:{exc}",
            "source": TRUTH_NONE,
            "by_id": {},
            "path": str(path),
            "coverage": {bid: {"source": TRUTH_NONE, "available": False} for bid in beam_ids},
        }
    coverage = {}
    by_id = {}
    for bid in beam_ids:
        hit = parsed.get(str(bid).upper())
        if hit and float(hit.get("total_weight_kg") or 0) > 0:
            by_id[bid] = hit
            coverage[bid] = {"source": TRUTH_ESTIMATOR, "available": True, "total_weight_kg": hit.get("total_weight_kg")}
        else:
            coverage[bid] = {"source": TRUTH_NONE, "available": False}
    return {
        "ok": True,
        "reason": None,
        "source": TRUTH_ESTIMATOR,
        "path": str(path),
        "by_id": by_id,
        "coverage": coverage,
        "parsed_beam_count": len(parsed),
        "matched_population_count": len(by_id),
    }


__all__ = ["discover_estimator_workbook", "load_benchmark_truth"]
