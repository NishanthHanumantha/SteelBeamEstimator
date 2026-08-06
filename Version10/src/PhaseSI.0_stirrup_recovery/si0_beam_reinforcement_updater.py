"""
Beam Reinforcement Updater — Phase SI.0 MODULE 7

Accepts the full beam_reinforcement_models list and a dict of
beam_id → recovered_stirrup_bar, then returns a new model list where
ONLY the stirrup objects have been replaced.

All other bar types (TOP_MAIN, BOTTOM_MAIN, SIDE_FACE, SPACER, etc.)
are preserved exactly as they came from L.2.
"""
import copy
from typing import List, Dict, Any

from si0_stirrup_recovery_models import BeamRecoveryResult, RecoveryDecision
from si0_recovered_stirrup_builder import build_recovered_stirrup


class BeamReinforcementUpdater:
    """
    Merges recovered stirrup data into the L.2 model without touching
    any longitudinal reinforcement or other engineering data.
    """

    def apply(
        self,
        original_models: List[Dict[str, Any]],
        recovery_results: List[BeamRecoveryResult],
    ) -> List[Dict[str, Any]]:
        """
        Returns a deep copy of the model list with only stirrup[] updated.
        """
        result_map = {r.beam_id: r for r in recovery_results}
        updated_models = []

        for model in original_models:
            beam_id = model.get("beam_id", "")
            result  = result_map.get(beam_id)

            if result is None or result.decision == RecoveryDecision.RETAINED:
                updated_models.append(copy.deepcopy(model))
                continue

            # Deep copy the model — only replace stirrups
            new_model = copy.deepcopy(model)
            original_stirrups = new_model.get("stirrups") or []

            if not original_stirrups:
                updated_models.append(new_model)
                continue

            # Replace each invalid stirrup with the recovered version
            new_stirrups = []
            for bar in original_stirrups:
                recovered_bar = build_recovered_stirrup(result, bar)
                new_stirrups.append(recovered_bar)
            new_model["stirrups"] = new_stirrups

            # Update traceability
            notes = new_model.get("engineering_notes") or []
            notes.append(
                f"Phase SI.0 stirrup recovery: {result.source.value} "
                f"(confidence={result.recovery_confidence:.2f}) "
                f"→ {result.recovered_label}"
            )
            new_model["engineering_notes"] = notes

            updated_models.append(new_model)

        return updated_models
