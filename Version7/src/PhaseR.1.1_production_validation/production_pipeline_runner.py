"""
production_pipeline_runner.py — Execute the complete V.B.1 production pipeline
using the Phase R.1 adapted reinforcement models.

No engineering logic is modified.  The runner calls V.B.1's existing modules
directly, passing the adapted models path instead of the L.2 path.

Pipeline:
  SteelWeightCompletion(adapted_path)  → ProjectSteelSummary
  BBSCompletionEngine(models)           → bbs_rows
  EstimatorExcelGenerator               → production_workbook.xlsx
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys
import time
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

_VB1_SRC = pathlib.Path(__file__).parents[2] / "src" / "PhaseVB.1_production_output_completion"


def _add_vb1_to_path() -> None:
    p = str(_VB1_SRC)
    if p not in sys.path:
        sys.path.insert(0, p)


class ProductionPipelineRunner:
    """
    Runs the V.B.1 production pipeline with Phase R.1 reinforcement models.
    Returns raw outputs for further comparison / reporting.
    """

    def __init__(
        self,
        adapted_models_path: pathlib.Path,
        output_dir:          pathlib.Path,
        beam_registry_path:  pathlib.Path,
    ):
        self._models_path   = adapted_models_path
        self._output_dir    = output_dir
        self._registry_path = beam_registry_path
        output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    def run(self) -> Dict[str, Any]:
        """Execute steel weight + BBS + Excel and return result dict."""
        _add_vb1_to_path()
        t0 = time.perf_counter()

        # ── Steel Weight ──────────────────────────────────────────────────────
        log.info("Running SteelWeightCompletion with R.1 models ...")
        from steel_weight_completion import SteelWeightCompletion  # type: ignore
        swc    = SteelWeightCompletion(self._models_path)
        summary = swc.compute()

        # Serialise to JSON
        sw_dict = self._summary_to_dict(summary)
        sw_path = self._output_dir / "steel_weight_summary_r1.json"
        sw_path.write_text(json.dumps(sw_dict, indent=2, default=str), encoding="utf-8")
        log.info("  Total steel weight: %.3f kg across %d beams", sw_dict["total_weight_kg"], sw_dict["total_beams"])

        # ── BBS ───────────────────────────────────────────────────────────────
        log.info("Running BBSCompletionEngine ...")
        bbs_rows: list = []
        bbs_path = None
        try:
            from bbs_completion_engine import BBSCompletionEngine  # type: ignore
            bbs_engine = BBSCompletionEngine(summary)
            bbs_rows   = bbs_engine.generate()
            bbs_path   = self._output_dir / "bbs_summary_r1.json"
            bbs_path.write_text(
                json.dumps({"total_bbs_rows": len(bbs_rows), "rows": bbs_rows}, indent=2, default=str),
                encoding="utf-8",
            )
            log.info("  BBS rows: %d", len(bbs_rows))
        except Exception as exc:
            log.warning("BBS engine error (non-fatal): %s", exc)

        # ── Excel ─────────────────────────────────────────────────────────────
        log.info("Running EstimatorExcelGenerator ...")
        excel_path: Optional[pathlib.Path] = None
        try:
            from estimator_excel_generator import EstimatorExcelGenerator  # type: ignore
            gen        = EstimatorExcelGenerator(bbs_rows, summary, self._output_dir)
            paths      = gen.generate()
            excel_path = paths.get("production") if isinstance(paths, dict) else self._output_dir / "production_workbook_r1.xlsx"
            log.info("  Excel workbook written: %s", excel_path)
        except Exception as exc:
            log.warning("Excel generator error (non-fatal): %s", exc)

        elapsed = round(time.perf_counter() - t0, 2)
        log.info("ProductionPipelineRunner complete in %.2fs", elapsed)

        return {
            "steel_weight":     sw_dict,
            "bbs_rows":         bbs_rows,
            "steel_weight_path": str(sw_path),
            "bbs_path":         str(bbs_path) if bbs_path else None,
            "excel_path":       str(excel_path) if excel_path else None,
            "elapsed_s":        elapsed,
        }

    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _summary_to_dict(summary) -> dict:
        """Convert ProjectSteelSummary dataclass to plain dict."""
        try:
            import dataclasses
            d = dataclasses.asdict(summary)
            return d
        except Exception:
            pass
        # Fallback: manual conversion
        result = {
            "total_weight_kg":  getattr(summary, "total_weight_kg", 0),
            "total_beams":      getattr(summary, "total_beams", 0),
            "total_bars":       getattr(summary, "total_bars", 0),
            "formula":          "W = (pi*d^2/4) * L * rho / 1e9 (IS 456)",
            "calculation_method": "Phase R.1.1 — R.1 reinforcement source",
            "density_kg_m3":    7850,
            "diameter_summary": [],
            "beam_weights":     [],
        }
        # Diameter summary
        for ds in getattr(summary, "diameter_summary", []):
            result["diameter_summary"].append({
                "diameter_mm":    getattr(ds, "diameter_mm", 0),
                "total_bars":     getattr(ds, "total_bars", 0),
                "total_length_mm": getattr(ds, "total_length_mm", 0),
                "total_weight_kg": getattr(ds, "total_weight_kg", 0),
                "weight_fraction_pct": round(getattr(ds, "weight_fraction", 0) * 100, 2),
            })
        # Beam weights
        for bw in getattr(summary, "beam_weights", []):
            wbd = {}
            for d_key, w in getattr(bw, "weight_by_diameter", {}).items():
                wbd[f"Y{d_key}"] = round(w, 3)
            result["beam_weights"].append({
                "beam_id":         getattr(bw, "beam_id", ""),
                "total_weight_kg": round(getattr(bw, "total_weight_kg", 0), 3),
                "weight_by_diameter": wbd,
            })
        return result
