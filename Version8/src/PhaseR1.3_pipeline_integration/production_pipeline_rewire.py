"""Production pipeline rewire — resolve reinforcement path for VB1."""
from __future__ import annotations
import pathlib
from typing import Optional, Tuple

from .pipeline_integration_manager import PipelineIntegrationManager
from .reinforcement_source_selector import ReinforcementSourceSelector


class ProductionPipelineRewire:
    """Rewires VB1 to consume EngineeringBarModel instead of REFERENCE_CLASSIFICATION."""

    def __init__(
        self,
        v7_root: pathlib.Path,
        auto_build: bool = True,
        engine_root: Optional[pathlib.Path] = None,
        run_root: Optional[pathlib.Path] = None,
        output_root: Optional[pathlib.Path] = None,
    ):
        self._run = pathlib.Path(run_root or v7_root)
        self._engine = pathlib.Path(engine_root or v7_root)
        self._v7 = self._run  # data root for selector
        self._selector = ReinforcementSourceSelector(
            run_root=self._run, output_root=output_root
        )
        self._auto_build = auto_build

    def resolve_models_path(self) -> Tuple[pathlib.Path, str]:
        if self._auto_build and not self._selector.engineering_bar_models_exist():
            if self._selector.r1_models_path().exists():
                mgr = PipelineIntegrationManager(
                    engine_root=self._engine,
                    run_root=self._run,
                )
                mgr.build_and_export()
        return self._selector.select()

    def get_source_report(self) -> dict:
        path, source = self.resolve_models_path()
        return {
            "models_path": str(path),
            "source": source,
            "reference_classification_in_path": "REFERENCE_CLASSIFICATION" in source,
            "engineering_bar_model_in_path": "EngineeringBarModel" in source,
        }
