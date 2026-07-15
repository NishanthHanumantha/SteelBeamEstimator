"""
root_cause_locator.py — Assigns a deterministic root cause to every beam loss event.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List, Optional
from .engineering_trace_models import (
    LossCategory, LostBeam, RootCause, StageSnapshot
)

# Stage-to-module mapping (informational, not modifying)
_STAGE_MODULE = {
    "VROOT1":      "dynamic_beam_discovery.py / beam_registry_builder.py",
    "V5_ADAPTER":  "engineering_object_initializer.py (adapter writer)",
    "L2":          "InterpretationCollector (loads V5 adapter JSONs)",
    "SI0":         "StirrupRecoveryEngine",
    "SI1":         "StirrupImprovementEngine",
    "L22":         "GeometryRecoveryEngine",
    "L21":         "FeatureExtractionEngine",
    "L3":          "PatternRecognitionEngine",
    "VB1":         "ExcelOutputEngine (V.B.1)",
}

_RECOMMENDATION = {
    LossCategory.STALE_OUTPUT: (
        "Re-run the failing stage against the current V5 adapter files. "
        "V.ROOT.1 has already written 65 Benchmark Set 2 beams to the V5 adapter "
        "paths. The pipeline must be executed in order: "
        "L.2 → SI.0 → SI.1 → L.2.2 → L.2.1 → L.3 → V.B.1."
    ),
    LossCategory.NOT_CREATED: (
        "Beam was never written to any downstream stage. Verify that V.ROOT.1 "
        "beam registry export succeeded and all V5 adapter files were written "
        "with the correct beam IDs."
    ),
    LossCategory.FILTERED: (
        "Investigate the filtering logic in the losing stage module. Check "
        "whether beam validation rules or schema checks silently drop beams."
    ),
    LossCategory.PIPELINE_SKIP: (
        "One or more pipeline stages were not re-executed after V.ROOT.1 "
        "updated the V5 adapter files. Re-run the pipeline from the first "
        "stage that shows a count mismatch."
    ),
    LossCategory.EMPTY_OBJECT: (
        "The engineering object for this beam was created but contains no "
        "reinforcement data. Check the reinforcement_objects.json adapter."
    ),
    LossCategory.UNKNOWN: (
        "Root cause not deterministically identified. Manual inspection of "
        "the stage input/output files is required."
    ),
}


class RootCauseLocator:
    """
    For every lost beam, assigns the most specific root cause explanation.
    """

    def __init__(self, snapshots: Dict[str, StageSnapshot]):
        self._snapshots = snapshots

    def locate_all(
        self,
        lost_beams: List[LostBeam],
        comparisons: List[dict],
    ) -> List[RootCause]:
        # Group lost beams by first_lost_stage
        by_stage: Dict[str, List[LostBeam]] = {}
        for lb in lost_beams:
            by_stage.setdefault(lb.first_lost_stage, []).append(lb)

        root_causes = []
        for stage_id, beams in sorted(by_stage.items()):
            snap        = self._snapshots.get(stage_id)
            in_snap_id  = self._prev_stage(stage_id, comparisons)
            in_snap     = self._snapshots.get(in_snap_id) if in_snap_id else None

            loss_cat    = beams[0].loss_category  # all beams in same stage share cause
            module      = _STAGE_MODULE.get(stage_id, "unknown_module")
            recommendation = _RECOMMENDATION.get(loss_cat, _RECOMMENDATION[LossCategory.UNKNOWN])

            mv = snap.raw_metadata.get("model_version", "?") if snap else "?"
            reason_prefix = (
                f"Stage '{stage_id}' (model_version={mv}) output contains "
                f"{snap.beam_count if snap else 0} beam(s) vs "
                f"{in_snap.beam_count if in_snap else '?'} in the preceding stage."
            )

            root_causes.append(RootCause(
                stage_id          = stage_id,
                module_name       = module,
                input_beam_count  = in_snap.beam_count if in_snap else 0,
                output_beam_count = snap.beam_count if snap else 0,
                failure_category  = loss_cat,
                reason            = f"{reason_prefix} {beams[0].loss_reason}",
                confidence        = beams[0].confidence,
                affected_beams    = sorted([b.beam_id for b in beams]),
                recommendation    = recommendation,
            ))

        return root_causes

    def _prev_stage(self, stage_id: str, comparisons: List[dict]) -> Optional[str]:
        for c in comparisons:
            if c.get("to_stage") == stage_id:
                return c.get("from_stage")
        return None
