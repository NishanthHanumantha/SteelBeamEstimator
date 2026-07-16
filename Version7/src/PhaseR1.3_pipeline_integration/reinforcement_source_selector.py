"""Deterministic reinforcement source selector."""
from __future__ import annotations
import pathlib
from typing import Tuple


class ReinforcementSourceSelector:
    """
    Priority:
      1. EngineeringBarModel (R.1.3 production path)
      2. Legacy L.2 reference classification (fallback)
    """

    R13_PRODUCTION_FILENAME = "beam_reinforcement_models_production.json"
    L2_FILENAME = "beam_reinforcement_models.json"

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self._r13_dir = v7_root / "data/output/PhaseR1.3_pipeline_integration"
        self._l2_dir = v7_root / "data/output/PhaseL.2 - engineering_reinforcement_interpretation"

    def select(self) -> Tuple[pathlib.Path, str]:
        r13_path = self._r13_dir / self.R13_PRODUCTION_FILENAME
        if r13_path.exists():
            return r13_path, "EngineeringBarModel_R1.3"

        eng_path = self._r13_dir / "engineering_bar_models.json"
        if eng_path.exists():
            return r13_path, "EngineeringBarModel_R1.3_PENDING_BUILD"

        l2_path = self._l2_dir / self.L2_FILENAME
        if l2_path.exists():
            return l2_path, "REFERENCE_CLASSIFICATION_LEGACY"

        raise FileNotFoundError(
            "No reinforcement source available: R.1.3 or L.2 models missing"
        )

    def engineering_bar_models_exist(self) -> bool:
        return (self._r13_dir / self.R13_PRODUCTION_FILENAME).exists()

    def r1_models_path(self) -> pathlib.Path:
        return (
            self._v7
            / "data/output/PhaseR.1_generalized_reinforcement_discovery"
            / "beam_reinforcement_models.json"
        )

    def beam_registry_path(self) -> pathlib.Path:
        return (
            self._v7
            / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
            / "beam_registry.json"
        )
