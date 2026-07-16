"""Load all pipeline artefacts for propagation audit (read-only)."""
from __future__ import annotations
import json
import pathlib
from typing import Any, Dict, List, Optional

from .propagation_models import L2_BAR_KEYS


class ReinforcementModelReader:
    """Loads V.ROOT.1, R.1, L.2, SI, VB.1 artefacts without modification."""

    def __init__(self, v7_root: pathlib.Path):
        self._out = v7_root / "data" / "output"
        self._loaded: Dict[str, Any] = {}
        self._paths: Dict[str, Optional[pathlib.Path]] = {}

    @property
    def paths(self) -> Dict[str, Optional[str]]:
        return {k: str(v) if v else None for k, v in self._paths.items()}

    def load_all(self) -> Dict[str, Any]:
        self._paths["registry"] = self._out / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
        self._paths["r1"] = self._out / "PhaseR.1_generalized_reinforcement_discovery" / "beam_reinforcement_models.json"
        self._paths["l2"] = self._out / "PhaseL.2 - engineering_reinforcement_interpretation" / "beam_reinforcement_models.json"
        self._paths["adapter"] = self._out / "PhaseR.1.1_production_validation" / "beam_reinforcement_models_r1.json"
        self._paths["si0"] = self._out / "PhaseSI.0_stirrup_recovery" / "phase_si0_summary.json"
        self._paths["si1"] = self._out / "PhaseSI.1_stirrup_improvement" / "stirrup_statistics.json"
        self._paths["steel"] = self._out / "Production_Output" / "steel_weight_summary.json"
        self._paths["bbs"] = self._out / "Production_Output" / "bbs_summary.json"
        self._paths["production"] = self._out / "Production_Output" / "production_output_report.json"
        self._paths["excel"] = self._out / "Production_Output" / "Estimation_Output.xlsx"

        for key, path in self._paths.items():
            if path and path.exists() and path.suffix == ".json":
                self._loaded[key] = json.loads(path.read_text(encoding="utf-8"))
            elif key == "excel" and path and path.exists():
                self._loaded[key] = {"exists": True, "path": str(path)}
            else:
                self._loaded[key] = None

        self._index_artefacts()
        return self._loaded

    def _index_artefacts(self) -> None:
        reg = self._loaded.get("registry") or {}
        self._beam_ids: List[str] = sorted(
            reg.get("beam_ids") or list((reg.get("beams") or {}).keys())
        )
        self._registry_beams = reg.get("beams") or {}

        r1 = self._loaded.get("r1") or {}
        self._r1_models = r1.get("models") or {}

        l2 = self._loaded.get("l2") or {}
        self._l2_by_id = {
            m["beam_id"]: m for m in (l2.get("models") or [])
            if m.get("beam_id")
        }

        adapter = self._loaded.get("adapter") or {}
        self._adapter_by_id = {
            m["beam_id"]: m for m in (adapter.get("models") or [])
            if m.get("beam_id")
        }

        steel = self._loaded.get("steel") or {}
        self._steel_by_id = {
            b["beam_id"]: b for b in (steel.get("beam_weights") or [])
        }

        bbs = self._loaded.get("bbs") or {}
        self._bbs_rows = bbs.get("rows") or bbs.get("bbs_rows") or []

    def beam_ids(self) -> List[str]:
        return list(self._beam_ids)

    def registry_beam(self, beam_id: str) -> Dict[str, Any]:
        return self._registry_beams.get(beam_id) or {}

    def r1_model(self, beam_id: str) -> Dict[str, Any]:
        return self._r1_models.get(beam_id) or {}

    def l2_model(self, beam_id: str) -> Dict[str, Any]:
        return self._l2_by_id.get(beam_id) or {}

    def adapter_model(self, beam_id: str) -> Dict[str, Any]:
        return self._adapter_by_id.get(beam_id) or {}

    def steel_beam(self, beam_id: str) -> Dict[str, Any]:
        return self._steel_by_id.get(beam_id) or {}

    def bbs_rows_for_beam(self, beam_id: str) -> List[Dict[str, Any]]:
        return [
            r for r in self._bbs_rows
            if r.get("beam_id") == beam_id
        ]

    @staticmethod
    def count_l2_bars(model: Dict[str, Any]) -> tuple:
        roles: Dict[str, int] = {}
        total = 0
        for key in L2_BAR_KEYS:
            bars = model.get(key) or []
            if isinstance(bars, list) and bars:
                roles[key] = len(bars)
                total += len(bars)
        return total, roles

    @staticmethod
    def count_r1_groups(model: Dict[str, Any]) -> tuple:
        groups = model.get("groups") or {}
        roles: Dict[str, int] = {}
        total_qty = 0
        group_count = 0
        for role, grp in groups.items():
            if not isinstance(grp, dict):
                continue
            qty = int(grp.get("total_quantity") or 0)
            if qty > 0:
                roles[role] = qty
                total_qty += qty
                group_count += 1
        return group_count, total_qty, roles
