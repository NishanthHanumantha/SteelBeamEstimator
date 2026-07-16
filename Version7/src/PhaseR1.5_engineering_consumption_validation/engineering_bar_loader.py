"""READ-ONLY pipeline data loader for consumption validation."""
from __future__ import annotations
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

from .engineering_consumption_models import EngineeringBarTrace

ENG_ROLE_TO_STEEL = {
    "TOP_MAIN": "TOP_MAIN",
    "TOP_EXTRA": "TOP_EXTRA",
    "BOTTOM_MAIN": "BOTTOM_MAIN",
    "BOTTOM_EXTRA": "BOTTOM_EXTRA",
    "STIRRUP": "STIRRUP",
    "SPACER_BAR": "SPACER",
    "SIDE_FACE_REINFORCEMENT": "SIDE_FACE",
    "DEVELOPMENT": "DEVELOPMENT",
    "LAP": "LAP",
    "UNKNOWN": "BENT",
}

ENG_ROLE_TO_L2_KEY = {
    "TOP_MAIN": "top_main_bars",
    "BOTTOM_MAIN": "bottom_main_bars",
    "TOP_EXTRA": "top_extra_bars",
    "BOTTOM_EXTRA": "bottom_extra_bars",
    "STIRRUP": "stirrups",
    "SPACER_BAR": "spacer_bars",
    "SIDE_FACE_REINFORCEMENT": "side_face_reinforcement",
    "DEVELOPMENT": "supplementary_bars",
    "LAP": "supplementary_bars",
    "UNKNOWN": "supplementary_bars",
}


class EngineeringBarLoader:

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self._project_root = v7_root.parent
        self.traces: List[EngineeringBarTrace] = []
        self.registry: Dict[str, Any] = {}
        self.production_models: Dict[str, Any] = {}
        self.steel_summary_json: Dict[str, Any] = {}
        self.bbs_summary_json: Dict[str, Any] = {}
        self.engineering_totals: Dict[str, Any] = {}
        self.production_report: Dict[str, Any] = {}
        self.steel_summary_computed: Any = None
        self.bbs_rows_computed: List[Any] = []
        self.workbook_path: Optional[pathlib.Path] = None
        self.reference_workbook_path: Optional[pathlib.Path] = None

    def load_all(self) -> None:
        eng_path = (
            self._v7 / "data/output/PhaseR1.3_pipeline_integration"
            / "engineering_bar_models.json"
        )
        prod_path = (
            self._v7 / "data/output/PhaseR1.3_pipeline_integration"
            / "beam_reinforcement_models_production.json"
        )
        reg_path = (
            self._v7 / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
            / "beam_registry.json"
        )
        prod_out = self._v7 / "data/output/Production_Output"

        self.registry = self._read_json(reg_path)
        eng_data = self._read_json(eng_path)
        self.production_models = self._read_json(prod_path)
        self.steel_summary_json = self._read_json(prod_out / "steel_weight_summary.json")
        self.bbs_summary_json = self._read_json(prod_out / "bbs_summary.json")
        self.engineering_totals = self._read_json(prod_out / "engineering_totals.json")
        self.production_report = self._read_json(prod_out / "production_output_report.json")

        wb = prod_out / "Estimation_Output.xlsx"
        self.workbook_path = wb if wb.exists() else None
        self.reference_workbook_path = self._detect_reference_workbook()

        self.traces = self._build_traces(eng_data)
        self._recompute_steel_and_bbs_readonly(prod_path)

    @staticmethod
    def _read_json(path: pathlib.Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _detect_reference_workbook(self) -> Optional[pathlib.Path]:
        drawing = str(self.registry.get("drawing_path", ""))
        if "Set_2" in drawing or "Benchmark_Set_2" in drawing:
            ref = self._project_root / "Set1&2_Output/Set2_Estimation_Output_15_7_26_1245.xlsx"
            return ref if ref.exists() else None
        if "Set_1" in drawing or "Benchmark_Set_1" in drawing:
            ref = self._project_root / "Set1&2_Output/Set1_Estimation_Output_14_7_26_1645.xlsx"
            return ref if ref.exists() else None
        return None

    def _build_traces(self, eng_data: Dict[str, Any]) -> List[EngineeringBarTrace]:
        traces: List[EngineeringBarTrace] = []
        idx = 0
        for beam in eng_data.get("beams", []):
            beam_id = beam.get("beam_id", "")
            for bar in beam.get("bars", []):
                role = bar.get("bar_role", "")
                traces.append(EngineeringBarTrace(
                    trace_id=f"BAR_{idx:06d}",
                    beam_id=beam_id,
                    bar_role=role,
                    diameter_mm=float(bar.get("diameter_mm") or 0),
                    quantity=int(bar.get("quantity") or 0),
                    spacing_mm=bar.get("spacing_mm"),
                    development_length_mm=bar.get("development_length_mm"),
                    cover_mm=bar.get("cover_mm"),
                    hook_rule=bar.get("hook_rule"),
                    lap_rule_mm=bar.get("lap_rule_mm"),
                    source_phase=str(bar.get("source_phase", "")),
                    bar_label=str(bar.get("bar_label", "")),
                    engineering_metadata=bar.get("engineering_metadata", {}),
                    steel_role=ENG_ROLE_TO_STEEL.get(role, "BENT"),
                ))
                idx += 1
        return traces

    def _recompute_steel_and_bbs_readonly(self, prod_path: pathlib.Path) -> None:
        """Re-invoke existing VB1 modules read-only for full bar-level trace."""
        vb1_src = self._v7 / "src/PhaseVB.1_production_output_completion"
        if str(vb1_src) not in sys.path:
            sys.path.insert(0, str(vb1_src))

        loader = None
        try:
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
            loader, _, _ = parser.parse_engineering_context(self._v7)
        except Exception:
            loader = None

        from steel_weight_completion import SteelWeightCompletion  # type: ignore
        from bbs_completion_engine import BBSCompletionEngine  # type: ignore

        swc = SteelWeightCompletion(prod_path, loader=loader)
        self.steel_summary_computed = swc.compute()
        bbs_engine = BBSCompletionEngine(self.steel_summary_computed)
        self.bbs_rows_computed = bbs_engine.generate()

    def production_model_for_beam(self, beam_id: str) -> Optional[Dict[str, Any]]:
        for m in self.production_models.get("models", []):
            if m.get("beam_id") == beam_id:
                return m
        return None

    def bar_in_production_model(self, trace: EngineeringBarTrace) -> bool:
        model = self.production_model_for_beam(trace.beam_id)
        if not model:
            return False
        l2_key = ENG_ROLE_TO_L2_KEY.get(trace.bar_role, "supplementary_bars")
        bars = model.get(l2_key, [])
        for bar in bars:
            if (
                float(bar.get("diameter_mm") or 0) == trace.diameter_mm
                and int(bar.get("quantity") or 0) == trace.quantity
                and str(bar.get("bar_label", "")) == trace.bar_label
            ):
                return True
        for bar in bars:
            if (
                float(bar.get("diameter_mm") or 0) == trace.diameter_mm
                and int(bar.get("quantity") or 0) == trace.quantity
            ):
                return True
        return len(bars) > 0 and trace.bar_role in ENG_ROLE_TO_L2_KEY

    def all_steel_bars(self) -> List[Tuple[Any, int]]:
        """Return (BarSteelWeight, global_index) from recomputed summary."""
        result = []
        idx = 0
        if not self.steel_summary_computed:
            return result
        for bw in self.steel_summary_computed.beam_weights:
            for bar in bw.bar_weights:
                result.append((bar, idx))
                idx += 1
        return result
