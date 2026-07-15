"""
duplication_detector.py — Detects duplicate beam IDs and UUIDs at each stage.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from collections import Counter
from typing import Dict, List
from .engineering_trace_models import DuplicateRecord, StageSnapshot


class DuplicationDetector:
    """Scans each stage snapshot for duplicated beam IDs or UUIDs."""

    def detect_all(
        self,
        snapshots: Dict[str, StageSnapshot],
    ) -> List[DuplicateRecord]:
        records: List[DuplicateRecord] = []
        for stage_id, snap in snapshots.items():
            records.extend(self._check_stage(snap))
        return records

    def _check_stage(self, snap: StageSnapshot) -> List[DuplicateRecord]:
        records: List[DuplicateRecord] = []

        # Duplicate beam IDs
        id_counts = Counter(snap.beam_ids)
        for bid, cnt in id_counts.items():
            if cnt > 1:
                records.append(DuplicateRecord(
                    stage_id = snap.stage_id,
                    field    = "beam_id",
                    value    = bid,
                    count    = cnt,
                    note     = f"Beam ID '{bid}' appears {cnt}× in {snap.stage_id}",
                ))

        # Duplicate UUIDs
        uuid_to_ids: Dict[str, List[str]] = {}
        for bid, uuid in snap.beam_uuids.items():
            uuid_to_ids.setdefault(uuid, []).append(bid)
        for uuid, bids in uuid_to_ids.items():
            if len(bids) > 1:
                records.append(DuplicateRecord(
                    stage_id = snap.stage_id,
                    field    = "beam_uuid",
                    value    = uuid,
                    count    = len(bids),
                    note     = f"UUID '{uuid}' shared by beams: {bids}",
                ))

        return records
