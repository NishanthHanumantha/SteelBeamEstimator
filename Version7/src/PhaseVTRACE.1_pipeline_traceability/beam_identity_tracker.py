"""
beam_identity_tracker.py — Tracks every beam's identity across all stages.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set
from .engineering_trace_models import (
    BeamLifecycle, BeamLifecycleEntry, BeamStatus, StageSnapshot
)


class BeamIdentityTracker:
    """
    Builds a full identity record for every beam that appeared at any stage.
    Source of truth is the V.ROOT.1 (VROOT1) snapshot.
    """

    def __init__(self, stage_order: List[str]):
        self._stage_order = stage_order

    def build_lifecycle_map(
        self,
        snapshots: Dict[str, StageSnapshot],
        source_stage: str = "VROOT1",
    ) -> Dict[str, BeamLifecycle]:
        """
        Return a dict of beam_id → BeamLifecycle.
        Master beam list comes from source_stage (V.ROOT.1).
        """
        source = snapshots.get(source_stage)
        if source is None:
            return {}

        all_beam_ids: Set[str] = set(source.beam_ids)
        # Also add any beams that appear at other stages (anomalous additions)
        for snap in snapshots.values():
            all_beam_ids.update(snap.beam_ids)

        lifecycles: Dict[str, BeamLifecycle] = {}

        for beam_id in sorted(all_beam_ids):
            stages_map: Dict[str, BeamLifecycleEntry] = {}
            first_seen: Optional[str] = None
            last_seen:  Optional[str] = None
            lost_at:    Optional[str] = None

            for stage_id in self._stage_order:
                snap = snapshots.get(stage_id)
                if snap is None:
                    continue

                present = beam_id in snap.beam_ids

                if present:
                    status = BeamStatus.PRESENT
                    uuid   = snap.beam_uuids.get(beam_id)
                    if first_seen is None:
                        first_seen = stage_id
                    last_seen = stage_id
                else:
                    if first_seen is None:
                        status = BeamStatus.MISSING   # never seen before
                    else:
                        status = BeamStatus.MISSING   # was present, now gone
                        if lost_at is None:
                            lost_at = stage_id
                    uuid = None

                stages_map[stage_id] = BeamLifecycleEntry(
                    stage_id  = stage_id,
                    status    = status,
                    beam_uuid = uuid,
                    section   = None,   # section tracking added by orchestrator
                    note      = "" if present else f"Not found in {stage_id}",
                )

            lifecycles[beam_id] = BeamLifecycle(
                beam_id       = beam_id,
                stages        = stages_map,
                first_seen    = first_seen,
                last_seen     = last_seen,
                lost_at       = lost_at,
                loss_category = None,   # assigned later by loss detector
                loss_reason   = None,
            )

        return lifecycles
