"""
Append-only P2 leader recovery engine.
MODEL_VERSION: 10.5.2
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS
from PhaseQA42_candidate_search_envelope_recovery.contamination import (
    build_owned_elsewhere_index,
)

from .config import DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID, LeaderRecoveryConfig
from .eligibility import evaluate_eligibility
from .ownership_bridge import (
    existing_engine_outcome_for_leader,
    index_graph,
    production_accepted_index,
)


def _sort_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (
            str(r.get("beam_id") or ""),
            str(r.get("entity_id") or ""),
            str(r.get("stable_key") or ""),
        ),
    )


def run_leader_recovery(
    *,
    leader_population: List[Dict[str, Any]],
    beam_ownership: Dict[str, Any],
    graph: Dict[str, Any],
    migration_doc: Optional[Dict[str, Any]],
    qa42_entity_keys: Optional[set] = None,
    config: LeaderRecoveryConfig = DEFAULT_CONFIG,
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
) -> Dict[str, Any]:
    nodes, _edges = index_graph(graph or {})
    accepted_by_beam = production_accepted_index(beam_ownership, list(priority_beams))
    owned_elsewhere = build_owned_elsewhere_index(migration_doc)
    by_beam_own = (beam_ownership or {}).get("by_beam") or {}
    qa42_keys = qa42_entity_keys or set()

    audit_rows: List[Dict[str, Any]] = []
    recovery_candidates: List[Dict[str, Any]] = []

    for row in _sort_rows(list(leader_population)):
        bid = str(row.get("beam_id") or "")
        eid = str(row.get("entity_id") or "")
        stable = str(row.get("stable_key") or f"{bid}::{eid}")
        elig = evaluate_eligibility(
            row, config=config, owned_elsewhere_ids=owned_elsewhere
        )

        other_owners = [
            ob
            for ob, s in accepted_by_beam.items()
            if ob != bid and eid in s
        ]
        contamination_blocked = bool(
            elig.get("neighbour_ambiguity")
            or elig.get("inside_other_beam_envelope")
            or eid in owned_elsewhere
            or other_owners
        )

        outcome = "recovery_excluded"
        candidate_generated = False
        candidate_added = False
        recovery_changed = False
        engine: Dict[str, Any] = {}

        if contamination_blocked and not elig.get("recovery_eligible"):
            # already excluded by eligibility; strengthen reason
            pass
        elif contamination_blocked and elig.get("recovery_eligible"):
            elig = {
                **elig,
                "recovery_eligible": False,
                "recovery_exclusion_reason": (
                    (elig.get("recovery_exclusion_reason") or "")
                    + ";contamination"
                    + (f":{','.join(other_owners)}" if other_owners else "")
                ).strip(";"),
            }
            outcome = "recovery_excluded"

        if not elig.get("recovery_eligible"):
            # Still query T18 for full audit transparency on excluded cases
            engine = existing_engine_outcome_for_leader(
                beam_id=bid,
                entity_id=eid,
                entity_type=row.get("entity_type"),
                beam_own=by_beam_own.get(bid) or {},
                nodes=nodes,
            )
            if elig.get("recovery_potential") in ("LOW", "UNKNOWN") or elig.get(
                "spatial_relationship"
            ) == "FAR_OUTSIDE":
                outcome = "diagnostic_only"
            else:
                outcome = "recovery_excluded"
            audit_rows.append(
                _build_audit_row(
                    row,
                    elig,
                    engine,
                    outcome=outcome,
                    candidate_generated=False,
                    candidate_added=False,
                    recovery_changed=False,
                    other_owners=other_owners,
                    qa42_overlap=stable in qa42_keys or eid in qa42_keys,
                )
            )
            continue

        # Eligible — generate recovery candidate and defer to T18
        candidate_generated = True
        engine = existing_engine_outcome_for_leader(
            beam_id=bid,
            entity_id=eid,
            entity_type=row.get("entity_type"),
            beam_own=by_beam_own.get(bid) or {},
            nodes=nodes,
        )

        if engine.get("already_in_production_candidate_pool"):
            outcome = "already_in_production_pool"
            candidate_added = False
        elif engine.get("already_in_t18_scoring_pool") and engine.get(
            "final_ownership_decision"
        ) == "REJECTED":
            # Already scored by T18 — do not newly add; record rejection
            outcome = "ownership_rejected"
            candidate_added = False
        elif engine.get("final_ownership_decision") == "ACCEPTED":
            outcome = "ownership_accepted"
            candidate_added = True
            recovery_changed = True
        elif engine.get("final_ownership_decision") == "REJECTED":
            outcome = "ownership_rejected"
            candidate_added = True  # newly evaluated then rejected
        else:
            outcome = "unresolved"
            candidate_added = True

        cand = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "beam_id": bid,
            "entity_id": eid,
            "stable_key": stable,
            "entity_type": row.get("entity_type"),
            "original_status": "Dropped",
            "original_rejection_reason": row.get("original_rejection_reason"),
            "recovery_category": elig.get("recovery_category"),
            "recovery_potential": elig.get("recovery_potential"),
            "spatial_relationship": elig.get("spatial_relationship"),
            "min_distance_to_production_envelope": elig.get(
                "min_distance_to_production_envelope"
            ),
            "longitudinal_overlap": elig.get("longitudinal_overlap"),
            "transverse_alignment": elig.get("transverse_alignment"),
            "beam_axis_alignment": elig.get("beam_axis_alignment"),
            "endpoint_near_envelope": elig.get("endpoint_near_envelope"),
            "target_beam_context": elig.get("target_beam_context"),
            "neighbour_ambiguity": elig.get("neighbour_ambiguity"),
            "inside_other_beam_envelope": elig.get("inside_other_beam_envelope"),
            "recovery_eligible": True,
            "recovery_exclusion_reason": None,
            "recovery_candidate_generated": True,
            "recovery_candidate_added_to_pool": candidate_added,
            "deduped_already_present": bool(
                engine.get("already_in_production_candidate_pool")
                or (
                    engine.get("already_in_t18_scoring_pool")
                    and not candidate_added
                )
            ),
            "existing_ownership_result": engine.get("existing_ownership_result"),
            "existing_ownership_score": engine.get("existing_ownership_score"),
            "final_ownership_decision": engine.get("final_ownership_decision"),
            "recovery_changed_decision": recovery_changed,
            "qa43_assigned_ownership": False,
            "engine_path": engine.get("engine_path"),
            "engine_input_id": engine.get("engine_input_id"),
            "parent_leader_id": engine.get("parent_leader_id"),
            "ownership_reason": engine.get("ownership_reason"),
            "rejected_rule": engine.get("rejected_rule"),
            "source_phase": "QA.4.1",
            "source_audit_record": stable,
            "production_envelope_unchanged": True,
            "recovery_outcome": outcome,
        }
        recovery_candidates.append(cand)
        audit_rows.append(
            _build_audit_row(
                row,
                elig,
                engine,
                outcome=outcome,
                candidate_generated=True,
                candidate_added=candidate_added,
                recovery_changed=recovery_changed,
                other_owners=other_owners,
                qa42_overlap=stable in qa42_keys or eid in qa42_keys,
            )
        )

    audit_rows = _sort_rows(audit_rows)
    recovery_candidates = _sort_rows(recovery_candidates)

    keys = [r["stable_key"] for r in audit_rows]
    dup_keys = sorted({k for k in keys if keys.count(k) > 1})
    multi = []
    by_eid: Dict[str, List[str]] = {}
    for c in recovery_candidates:
        if c.get("final_ownership_decision") == "ACCEPTED" and c.get(
            "recovery_candidate_added_to_pool"
        ):
            by_eid.setdefault(c["entity_id"], []).append(c["beam_id"])
    multi = [
        {"entity_id": eid, "beams": sorted(set(beams))}
        for eid, beams in by_eid.items()
        if len(set(beams)) > 1
    ]

    contamination = {
        "cross_beam_contamination_count": len(multi),
        "duplicate_stable_key_count": len(dup_keys),
        "duplicate_stable_keys": dup_keys,
        "multi_beam_assignments": multi,
        "illegal_cross_beam": multi,
        "outcomes": dict(Counter(r.get("recovery_outcome") for r in audit_rows)),
        "pass": len(multi) == 0 and len(dup_keys) == 0,
    }

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "audit_rows": audit_rows,
        "recovery_candidates": recovery_candidates,
        "contamination": contamination,
    }


def _build_audit_row(
    row,
    elig,
    engine,
    *,
    outcome,
    candidate_generated,
    candidate_added,
    recovery_changed,
    other_owners,
    qa42_overlap,
) -> Dict[str, Any]:
    return {
        **elig,
        "original_status": "Dropped",
        "original_rejection_reason": row.get("original_rejection_reason"),
        "rejected_rule_original": row.get("rejected_rule"),
        "recovery_candidate_generated": candidate_generated,
        "recovery_candidate_added_to_pool": candidate_added,
        "deduped_already_present": bool(
            engine.get("already_in_production_candidate_pool")
            or (
                engine.get("already_in_t18_scoring_pool")
                and not candidate_added
                and candidate_generated
            )
        ),
        "existing_ownership_result": engine.get("existing_ownership_result"),
        "existing_ownership_score": engine.get("existing_ownership_score"),
        "final_ownership_decision": engine.get("final_ownership_decision"),
        "recovery_changed_decision": recovery_changed,
        "qa43_assigned_ownership": False,
        "engine_path": engine.get("engine_path"),
        "engine_input_id": engine.get("engine_input_id"),
        "parent_leader_id": engine.get("parent_leader_id"),
        "ownership_reason": engine.get("ownership_reason"),
        "rejected_rule": engine.get("rejected_rule"),
        "already_in_production_candidate_pool": engine.get(
            "already_in_production_candidate_pool"
        ),
        "already_in_t18_scoring_pool": engine.get("already_in_t18_scoring_pool"),
        "other_beam_owners": other_owners,
        "qa42_stable_key_overlap": qa42_overlap,
        "source_phase": "QA.4.1",
        "source_audit_record": elig.get("stable_key"),
        "production_envelope_unchanged": True,
        "recovery_outcome": outcome,
        "text": row.get("text"),
    }
