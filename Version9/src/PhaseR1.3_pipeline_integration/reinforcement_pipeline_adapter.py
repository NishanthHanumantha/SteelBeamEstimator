"""Load R.1 reinforcement and convert to EngineeringBarModel."""
from __future__ import annotations
import json
import pathlib
from typing import Any, Dict, List, Tuple

from .engineering_bar_model import BeamEngineeringModel
from .engineering_bar_builder import EngineeringBarBuilder


class ReinforcementPipelineAdapter:
    """ONLY reinforcement provider — R.1 -> EngineeringBarModel."""

    def __init__(
        self,
        r1_models_path: pathlib.Path,
        beam_registry_path: pathlib.Path,
        engineering_context: Dict[str, Any] | None = None,
    ):
        self._r1_path = r1_models_path
        self._registry_path = beam_registry_path
        self._ctx = engineering_context or {}

    def load_and_convert(self) -> Tuple[List[BeamEngineeringModel], Dict[str, Any]]:
        if not self._r1_path.exists():
            raise FileNotFoundError(f"R.1 models not found: {self._r1_path}")
        if not self._registry_path.exists():
            raise FileNotFoundError(f"Beam registry not found: {self._registry_path}")

        builder = EngineeringBarBuilder(
            self._r1_path, self._registry_path, self._ctx
        )
        beam_models, build_stats = builder.build_all()
        validation = self._validate(beam_models, build_stats)
        return beam_models, {**build_stats, "validation": validation}

    def _validate(
        self, beam_models: List[BeamEngineeringModel], stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        r1_data = json.loads(self._r1_path.read_text(encoding="utf-8"))
        r1_beams = set(r1_data.get("models", {}).keys())
        converted = {bm.beam_id for bm in beam_models}
        missing = r1_beams - converted
        return {
            "r1_beam_count": len(r1_beams),
            "converted_beam_count": len(converted),
            "all_r1_beams_converted": len(missing) == 0,
            "missing_beam_ids": sorted(missing),
            "beams_with_bars": stats["beams_with_bars"],
            "beams_empty": stats["beams_empty"],
            "empty_beam_ids": stats["empty_beam_ids"],
            "total_bars": stats["total_bars"],
            "benchmark_filtering": False,
            "reference_classification_used": False,
        }
