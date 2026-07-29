"""Deterministic reinforcement source selector."""
from __future__ import annotations
import pathlib
from typing import Optional, Tuple


class ReinforcementSourceSelector:
    """
    Priority:
      1. EngineeringBarModel (R.1.3 production path)
      2. Legacy L.2 reference classification (fallback)
    """

    R13_PRODUCTION_FILENAME = "beam_reinforcement_models_production.json"
    L2_FILENAME = "beam_reinforcement_models.json"

    def __init__(
        self,
        v7_root: Optional[pathlib.Path] = None,
        run_root: Optional[pathlib.Path] = None,
        output_root: Optional[pathlib.Path] = None,
    ):
        # Prefer explicit output_root; else run_root/data/output; else legacy v7_root
        if output_root is not None:
            out = pathlib.Path(output_root)
            self._run = out.parent.parent if out.name == "output" else out
        elif run_root is not None:
            self._run = pathlib.Path(run_root)
            out = self._run / "data" / "output"
        elif v7_root is not None:
            self._run = pathlib.Path(v7_root)
            out = self._run / "data" / "output"
        else:
            raise ValueError("output_root, run_root, or v7_root required")
        self._v7 = self._run  # backward-compat alias (data root)
        self._r13_dir = out / "PhaseR1.3_pipeline_integration"
        self._l2_dir = out / "PhaseL.2 - engineering_reinforcement_interpretation"

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
            self._run
            / "data/output/PhaseR.1_generalized_reinforcement_discovery"
            / "beam_reinforcement_models.json"
        )

    def beam_registry_path(self) -> pathlib.Path:
        return (
            self._run
            / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
            / "beam_registry.json"
        )
