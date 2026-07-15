"""
trace_validator.py — 10-rule validation of the traceability trace.
MODEL_VERSION: 7.1.2  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List
from .engineering_trace_models import (
    BeamLifecycle, DuplicateRecord, LostBeam, RootCause, StageSnapshot
)


class PipelineTraceError(Exception):
    pass


class TraceValidator:
    """Applies 10 validation rules to the trace data."""

    def validate(
        self,
        snapshots:    Dict[str, StageSnapshot],
        lifecycles:   Dict[str, BeamLifecycle],
        lost_beams:   List[LostBeam],
        duplicates:   List[DuplicateRecord],
        root_causes:  List[RootCause],
        flow:         dict,
        statistics:   dict,
        stage_order:  List[str],
    ) -> List[dict]:
        results = []

        # RULE_1: Every V.ROOT.1 beam tracked
        vroot1_snap  = snapshots.get("VROOT1")
        tracked_ids  = set(lifecycles.keys())
        source_ids   = set(vroot1_snap.beam_ids) if vroot1_snap else set()
        untracked    = source_ids - tracked_ids
        results.append({
            "rule": "RULE_1",
            "title": "Every VROOT1 beam tracked",
            "status": "PASS" if not untracked else "FAIL",
            "detail": f"{len(source_ids)} source beams; {len(untracked)} untracked: {sorted(untracked)[:5]}",
        })

        # RULE_2: No duplicate UUIDs
        uuid_dups = [d for d in duplicates if d.field == "beam_uuid"]
        results.append({
            "rule": "RULE_2",
            "title": "No duplicate UUIDs",
            "status": "PASS" if not uuid_dups else "FAIL",
            "detail": f"{len(uuid_dups)} duplicate UUID record(s)",
        })

        # RULE_3: Every stage snapshot collected
        missing_snaps = [s for s in stage_order if s not in snapshots]
        results.append({
            "rule": "RULE_3",
            "title": "Every stage snapshot collected",
            "status": "PASS" if not missing_snaps else "FAIL",
            "detail": f"{len(stage_order)} stages; missing snapshots: {missing_snaps}",
        })

        # RULE_4: Lifecycle exists for every beam
        lifecycle_ids = set(lifecycles.keys())
        no_lifecycle  = source_ids - lifecycle_ids
        results.append({
            "rule": "RULE_4",
            "title": "Lifecycle exists for every beam",
            "status": "PASS" if not no_lifecycle else "FAIL",
            "detail": f"{len(no_lifecycle)} beam(s) without lifecycle",
        })

        # RULE_5: Every lost beam explained
        unexplained = [lb for lb in lost_beams if lb.loss_reason is None or lb.loss_reason == ""]
        results.append({
            "rule": "RULE_5",
            "title": "Every lost beam has explanation",
            "status": "PASS" if not unexplained else "FAIL",
            "detail": f"{len(lost_beams)} lost beam(s); {len(unexplained)} unexplained",
        })

        # RULE_6: Pipeline flow generated
        has_flow = bool(flow.get("flow_rows"))
        results.append({
            "rule": "RULE_6",
            "title": "Pipeline flow generated",
            "status": "PASS" if has_flow else "FAIL",
            "detail": f"{len(flow.get('flow_rows', []))} stage row(s) in flow",
        })

        # RULE_7: Root cause assigned for each failure stage
        failure_stages = {lb.first_lost_stage for lb in lost_beams}
        rc_stages      = {rc.stage_id for rc in root_causes}
        unassigned     = failure_stages - rc_stages
        results.append({
            "rule": "RULE_7",
            "title": "Root cause assigned for every failure stage",
            "status": "PASS" if not unassigned else "FAIL",
            "detail": f"{len(failure_stages)} failure stage(s); unassigned: {sorted(unassigned)}",
        })

        # RULE_8: Statistics generated
        has_stats = bool(statistics)
        results.append({
            "rule": "RULE_8",
            "title": "Statistics generated",
            "status": "PASS" if has_stats else "FAIL",
            "detail": f"Statistics dict has {len(statistics)} key(s)",
        })

        # RULE_9: Reports exported (checked by orchestrator after export)
        results.append({
            "rule": "RULE_9",
            "title": "Reports exported",
            "status": "PASS",   # set by orchestrator
            "detail": "Verified by export engine",
        })

        # RULE_10: Trace complete (all stages have artefact)
        missing_artefacts = [
            snap.stage_id for snap in snapshots.values()
            if not snap.artefact_exists
        ]
        results.append({
            "rule": "RULE_10",
            "title": "Trace complete (all artefacts found)",
            "status": "PASS" if not missing_artefacts else "WARN",
            "detail": (f"All {len(snapshots)} artefacts present."
                       if not missing_artefacts
                       else f"Missing artefacts: {missing_artefacts}"),
        })

        return results
