"""Pipeline integration manager — build and export engineering bar models."""
from __future__ import annotations
import json
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .engineering_bar_builder import EngineeringBarBuilder
from .l2_engineering_processor import L2EngineeringProcessor
from .reinforcement_pipeline_adapter import ReinforcementPipelineAdapter
from .reinforcement_source_selector import ReinforcementSourceSelector


class PipelineIntegrationManager:

    MODEL_VERSION = "7.7.0"

    def __init__(self, v7_root: pathlib.Path, output_dir: Optional[pathlib.Path] = None):
        self._v7 = v7_root
        self._selector = ReinforcementSourceSelector(v7_root)
        self._out = output_dir or (
            v7_root / "data/output/PhaseR1.3_pipeline_integration"
        )
        self._out.mkdir(parents=True, exist_ok=True)
        self._ctx: Dict[str, Any] = {}
        self._loader = None

    def _load_engineering_context(self) -> None:
        try:
            import sys
            import types
            import importlib.util as ilu

            r2a_dir = self._v7 / "src/PhaseR.2A_engineering_context"
            if "PhaseR2A.engineering_context_parser" not in sys.modules:
                pkg = types.ModuleType("PhaseR2A")
                pkg.__path__ = [str(r2a_dir)]
                sys.modules["PhaseR2A"] = pkg
                spec = ilu.spec_from_file_location(
                    "PhaseR2A.engineering_context_parser",
                    r2a_dir / "engineering_context_parser.py",
                )
                mod = ilu.module_from_spec(spec)
                mod.__package__ = "PhaseR2A"
                sys.modules["PhaseR2A.engineering_context_parser"] = mod
                spec.loader.exec_module(mod)
            parser = sys.modules["PhaseR2A.engineering_context_parser"]
            self._loader, _, _ = parser.parse_engineering_context(self._v7)
            if self._loader:
                self._ctx = self._loader.summary() or {}
        except Exception:
            self._ctx = {}

    def build_and_export(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        self._load_engineering_context()

        adapter = ReinforcementPipelineAdapter(
            self._selector.r1_models_path(),
            self._selector.beam_registry_path(),
            self._ctx,
        )
        beam_models, adapter_stats = adapter.load_and_convert()

        processor = L2EngineeringProcessor()
        processing_report = processor.process(beam_models)

        builder = EngineeringBarBuilder(
            self._selector.r1_models_path(),
            self._selector.beam_registry_path(),
            self._ctx,
        )
        l2_compatible = builder.to_l2_compatible(beam_models)

        canonical = {
            "model_version": self.MODEL_VERSION,
            "source": "Phase R.1.3 EngineeringBarModel",
            "beam_count": len(beam_models),
            "total_bars": adapter_stats["total_bars"],
            "beams": [bm.to_dict() for bm in beam_models],
        }

        eng_path = self._out / "engineering_bar_models.json"
        prod_path = self._out / ReinforcementSourceSelector.R13_PRODUCTION_FILENAME
        eng_path.write_text(json.dumps(canonical, indent=2), encoding="utf-8")
        prod_path.write_text(json.dumps(l2_compatible, indent=2), encoding="utf-8")

        elapsed = time.perf_counter() - t0
        return {
            "engineering_bar_models_path": str(eng_path),
            "production_models_path": str(prod_path),
            "adapter_stats": adapter_stats,
            "processing_report": processing_report,
            "beam_count": len(beam_models),
            "beams_with_bars": adapter_stats["beams_with_bars"],
            "total_bars": adapter_stats["total_bars"],
            "elapsed_seconds": round(elapsed, 3),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_production_models_path(self) -> pathlib.Path:
        return self._out / ReinforcementSourceSelector.R13_PRODUCTION_FILENAME
