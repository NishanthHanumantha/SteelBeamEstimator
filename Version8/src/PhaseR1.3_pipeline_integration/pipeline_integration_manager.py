"""Pipeline integration manager — build and export engineering bar models."""
from __future__ import annotations
import importlib.util
import json
import pathlib
import sys
import time
import types
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .engineering_bar_builder import EngineeringBarBuilder
from .engineering_bar_model import BeamEngineeringModel, EngineeringBarModel
from .l2_engineering_processor import L2EngineeringProcessor
from .reinforcement_pipeline_adapter import ReinforcementPipelineAdapter
from .reinforcement_source_selector import ReinforcementSourceSelector

_BAR_FIELDS = {
    "beam_id", "bar_role", "diameter_mm", "quantity", "zone", "spacing_mm",
    "development_length_mm", "cover_mm", "steel_grade", "concrete_grade",
    "hook_rule", "lap_rule_mm", "source_phase", "bar_label", "engineering_metadata",
}


class PipelineIntegrationManager:

    MODEL_VERSION = "8.5.0"

    def __init__(self, v7_root: pathlib.Path, output_dir: Optional[pathlib.Path] = None):
        self._v7 = v7_root
        self._selector = ReinforcementSourceSelector(v7_root)
        self._out = output_dir or (
            v7_root / "data/output/PhaseR1.3_pipeline_integration"
        )
        self._out.mkdir(parents=True, exist_ok=True)
        self._ctx: Dict[str, Any] = {}
        self._loader = None
        self._last_consolidation: Dict[str, Any] = {}

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

        # Phase R.1.2B — consolidate duplicate physical reinforcement
        bars_before = sum(len(bm.bars) for bm in beam_models)
        beam_models, consol_payload = self._apply_consolidation(beam_models)
        bars_after = sum(len(bm.bars) for bm in beam_models)
        adapter_stats = dict(adapter_stats)
        adapter_stats["total_bars_before_consolidation"] = bars_before
        adapter_stats["total_bars"] = bars_after
        adapter_stats["beams_with_bars"] = sum(1 for bm in beam_models if bm.bars)
        self._last_consolidation = consol_payload

        builder = EngineeringBarBuilder(
            self._selector.r1_models_path(),
            self._selector.beam_registry_path(),
            self._ctx,
        )
        l2_compatible = builder.to_l2_compatible(beam_models)

        canonical = {
            "model_version": self.MODEL_VERSION,
            "source": "Phase R.1.3 EngineeringBarModel + R.1.2B Consolidation",
            "beam_count": len(beam_models),
            "total_bars": adapter_stats["total_bars"],
            "total_bars_before_consolidation": bars_before,
            "consolidation": (consol_payload.get("report") or {}),
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
            "consolidation": consol_payload.get("report") or {},
            "beam_count": len(beam_models),
            "beams_with_bars": adapter_stats["beams_with_bars"],
            "total_bars": adapter_stats["total_bars"],
            "elapsed_seconds": round(elapsed, 3),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _apply_consolidation(
        self, beam_models: List[BeamEngineeringModel]
    ) -> Tuple[List[BeamEngineeringModel], Dict[str, Any]]:
        """Run R.1.2B consolidator; on failure return originals unchanged."""
        try:
            pkg_dir = self._v7 / "src/PhaseR1_2B_engineeringbar_consolidation"
            pkg_name = "PhaseR12B"
            if pkg_name not in sys.modules:
                pkg = types.ModuleType(pkg_name)
                pkg.__path__ = [str(pkg_dir)]
                pkg.__package__ = pkg_name
                sys.modules[pkg_name] = pkg
            for sub in (
                "physical_reinforcement_model",
                "engineeringbar_duplicate_detector",
                "engineeringbar_consolidator",
                "consolidation_service",
            ):
                key = f"{pkg_name}.{sub}"
                if key in sys.modules:
                    continue
                spec = importlib.util.spec_from_file_location(
                    key, pkg_dir / f"{sub}.py"
                )
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = pkg_name
                sys.modules[key] = mod
                spec.loader.exec_module(mod)

            Service = sys.modules[f"{pkg_name}.consolidation_service"].EngineeringBarConsolidationService
            consolidated_dicts, payload = Service().apply(
                [bm.to_dict() for bm in beam_models]
            )
            out: List[BeamEngineeringModel] = []
            for src, d in zip(beam_models, consolidated_dicts):
                bars: List[EngineeringBarModel] = []
                for b in d.get("bars") or []:
                    kwargs = {k: b[k] for k in _BAR_FIELDS if k in b}
                    kwargs.setdefault("beam_id", src.beam_id)
                    bars.append(EngineeringBarModel(**kwargs))
                out.append(
                    BeamEngineeringModel(
                        beam_id=src.beam_id,
                        beam_name=src.beam_name,
                        bars=bars,
                        geometry=dict(src.geometry or {}),
                        source_phase="R.1.3+R.1.2B",
                        classification_complete=src.classification_complete,
                    )
                )
            return out, payload
        except Exception as exc:
            return beam_models, {
                "report": {
                    "status": "SKIPPED",
                    "error": str(exc),
                    "bars_before": sum(len(bm.bars) for bm in beam_models),
                    "bars_after": sum(len(bm.bars) for bm in beam_models),
                },
                "physical_members": [],
                "traceability": [],
            }

    def get_production_models_path(self) -> pathlib.Path:
        return self._out / ReinforcementSourceSelector.R13_PRODUCTION_FILENAME
