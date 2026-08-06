"""Classify empty/missing beams without benchmark assumptions."""
from __future__ import annotations
from typing import Any, Dict, Set

from .pipeline_data_loader import PipelineDataLoader


class CoverageClassifier:

    CAT_NO_REINFORCEMENT = "CATEGORY_1_NO_REINFORCEMENT"
    CAT_PARSING_FAILED = "CATEGORY_2_PARSING_FAILED"
    CAT_DISCOVERY_FAILURE = "CATEGORY_3_DISCOVERY_FAILURE"
    CAT_PROPAGATION_FAILURE = "CATEGORY_4_PROPAGATION_FAILURE"

    def classify_all(self, loader: PipelineDataLoader) -> Dict[str, Dict[str, Any]]:
        registry_ids = loader.registry_beam_ids()
        eng_map = {b["beam_id"]: b for b in loader.engineering_beams()}
        r1_ids = loader.r1_beam_ids()
        results: Dict[str, Dict[str, Any]] = {}

        for bid in registry_ids:
            results[bid] = self._classify_beam(
                bid, eng_map, loader, r1_ids
            )
        return results

    def _classify_beam(
        self,
        beam_id: str,
        eng_map: Dict[str, Any],
        loader: PipelineDataLoader,
        r1_ids: Set[str],
    ) -> Dict[str, Any]:
        eng_beam = eng_map.get(beam_id)
        eng_bars = eng_beam.get("bars", []) if eng_beam else []
        in_r1 = beam_id in r1_ids
        r1_has_groups = loader.r1_beam_has_groups(beam_id) if in_r1 else False

        if eng_bars:
            return {
                "category": "COVERED",
                "status": "PASS",
                "reason": "EngineeringBarModel contains reinforcement bars",
            }

        if in_r1 and r1_has_groups:
            return {
                "category": self.CAT_PROPAGATION_FAILURE,
                "status": "ERROR",
                "reason": (
                    "R.1 discovered reinforcement groups but "
                    "EngineeringBarModel has no bars"
                ),
            }

        if in_r1 and not r1_has_groups:
            return {
                "category": self.CAT_NO_REINFORCEMENT,
                "status": "WARNING" if True else "PASS",
                "reason": "R.1 model exists with zero-quantity groups",
            }

        if not in_r1:
            return {
                "category": self.CAT_DISCOVERY_FAILURE,
                "status": "WARNING",
                "reason": "Beam in registry but absent from R.1 discovery",
            }

        return {
            "category": self.CAT_PARSING_FAILED,
            "status": "WARNING",
            "reason": "Reinforcement may exist but parsing produced no bars",
        }
