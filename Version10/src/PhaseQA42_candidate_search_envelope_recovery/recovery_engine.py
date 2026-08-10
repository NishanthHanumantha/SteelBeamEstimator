"""
Append-only candidate / search envelope recovery engine.
MODEL_VERSION: 10.5.1

Production envelope semantics are UNCHANGED.
Recovery is a candidate layer; existing T18 ownership decides.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from PhaseQA31_pipeline_diagnostics.artefact_locator import PRIORITY_FOURTH_BEAMS

from .config import CandidateRecoveryConfig, DEFAULT_CONFIG, MODEL_VERSION, PHASE_ID
from .contamination import build_owned_elsewhere_index, contamination_report, guard_candidate
from .eligibility import evaluate_eligibility
from .ownership_bridge import (
    build_parent_leader_map,
    existing_engine_outcome_for_entity,
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


def run_recovery(
    *,
    high_population: List[Dict[str, Any]],
    medium_population: List[Dict[str, Any]],
    low_population: List[Dict[str, Any]],
    beam_ownership: Dict[str, Any],
    graph: Dict[str, Any],
    migration_doc: Optional[Dict[str, Any]],
    config: CandidateRecoveryConfig = DEFAULT_CONFIG,
    priority_beams: Sequence[str] = PRIORITY_FOURTH_BEAMS,
) -> Dict[str, Any]:
    nodes, edges = index_graph(graph or {})
    parent_leaders = build_parent_leader_map(edges, nodes)
    accepted_by_beam = production_accepted_index(beam_ownership, list(priority_beams))
    owned_elsewhere = build_owned_elsewhere_index(migration_doc)
    by_beam_own = (beam_ownership or {}).get("by_beam") or {}

    audit_rows: List[Dict[str, Any]] = []
    recovery_candidates: List[Dict[str, Any]] = []
    diagnostic_rows: List[Dict[str, Any]] = []

    # --- P1 HIGH recovery pass ---
    for row in _sort_rows(list(high_population)):
        bid = str(row.get("beam_id") or "")
        eid = str(row.get("entity_id") or "")
        stable = str(row.get("stable_key") or f"{bid}::{eid}")
        elig = evaluate_eligibility(
            row, config=config, owned_elsewhere_ids=owned_elsewhere
        )
        guard = guard_candidate(
            eligibility=elig,
            audit_row=row,
            production_accepted=accepted_by_beam.get(bid) or set(),
            production_accepted_other_beams=accepted_by_beam,
            owned_elsewhere_ids=owned_elsewhere,
        )

        outcome = "recovery_excluded"
        candidate_generated = False
        candidate_added = False
        recovery_changed = False

        if not elig.get("recovery_eligible"):
            outcome = "recovery_excluded"
        elif guard.get("contamination_blocked"):
            outcome = "recovery_excluded_contamination"
            elig = {
                **elig,
                "recovery_eligible": False,
                "recovery_exclusion_reason": (
                    (elig.get("recovery_exclusion_reason") or "")
                    + ";contamination:"
                    + ",".join(guard.get("contamination_flags") or [])
                ).strip(";"),
            }
        else:
            # Eligible — generate recovery candidate record (append-only audit layer)
            candidate_generated = True
            engine = existing_engine_outcome_for_entity(
                beam_id=bid,
                entity_id=eid,
                entity_type=row.get("entity_type"),
                beam_own=by_beam_own.get(bid) or {},
                nodes=nodes,
                parent_leaders=parent_leaders,
            )

            if engine.get("already_in_production_candidate_pool"):
                outcome = "already_in_production_pool"
                candidate_added = False  # dedupe — not newly inserted
            elif engine.get("final_ownership_decision") == "ACCEPTED":
                outcome = "ownership_accepted"
                candidate_added = True
                recovery_changed = True  # would change dropped→owned in recovery delta
            elif engine.get("final_ownership_decision") == "REJECTED":
                outcome = "ownership_rejected"
                candidate_added = True  # entered pool, engine rejected
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
                "original_status": row.get("original_ownership_status") or "Dropped",
                "original_rejection_reason": row.get("original_rejection_reason"),
                "recovery_category": row.get("primary_audit_category"),
                "recovery_potential": row.get("recovery_potential"),
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
                ),
                "existing_ownership_result": engine.get("existing_ownership_result"),
                "existing_ownership_score": engine.get("existing_ownership_score"),
                "final_ownership_decision": engine.get("final_ownership_decision"),
                "recovery_changed_decision": recovery_changed,
                "qa42_assigned_ownership": False,
                "engine_path": engine.get("engine_path"),
                "engine_input_id": engine.get("engine_input_id"),
                "parent_leader_id": engine.get("parent_leader_id"),
                "evaluate_leader_invoked": engine.get("evaluate_leader_invoked"),
                "ownership_reason": engine.get("ownership_reason"),
                "rejected_rule": engine.get("rejected_rule"),
                "source_phase": "QA.4.1",
                "source_audit_record": stable,
                "production_envelope_unchanged": True,
                "recovery_outcome": outcome,
            }
            recovery_candidates.append(cand)

            audit_rows.append(
                {
                    **elig,
                    **guard,
                    **{k: engine.get(k) for k in (
                        "existing_ownership_result",
                        "existing_ownership_score",
                        "final_ownership_decision",
                        "already_in_production_candidate_pool",
                        "engine_path",
                        "engine_input_id",
                        "parent_leader_id",
                        "qa42_assigned_ownership",
                        "ownership_reason",
                        "rejected_rule",
                    )},
                    "original_status": row.get("original_ownership_status") or "Dropped",
                    "original_rejection_reason": row.get("original_rejection_reason"),
                    "recovery_candidate_generated": candidate_generated,
                    "recovery_candidate_added_to_pool": candidate_added,
                    "recovery_changed_decision": recovery_changed,
                    "recovery_outcome": outcome,
                    "source_phase": "QA.4.1",
                    "source_audit_record": stable,
                    "production_envelope_unchanged": True,
                    "text": row.get("text"),
                }
            )
            continue

        # Excluded path
        audit_rows.append(
            {
                **elig,
                **guard,
                "original_status": row.get("original_ownership_status") or "Dropped",
                "original_rejection_reason": row.get("original_rejection_reason"),
                "recovery_candidate_generated": False,
                "recovery_candidate_added_to_pool": False,
                "recovery_changed_decision": False,
                "existing_ownership_result": None,
                "existing_ownership_score": None,
                "final_ownership_decision": None,
                "qa42_assigned_ownership": False,
                "recovery_outcome": outcome,
                "source_phase": "QA.4.1",
                "source_audit_record": stable,
                "production_envelope_unchanged": True,
                "text": row.get("text"),
            }
        )

    # --- Diagnostic MEDIUM / LOW (no recovery candidate emission) ---
    if config.diagnostically_evaluate_medium_low:
        for row in _sort_rows(list(medium_population) + list(low_population)):
            bid = str(row.get("beam_id") or "")
            eid = str(row.get("entity_id") or "")
            stable = str(row.get("stable_key") or f"{bid}::{eid}")
            flags = row.get("evidence_flags") or {}
            env = row.get("envelope_audit") or {}
            already = eid in (accepted_by_beam.get(bid) or set())
            diagnostic_rows.append(
                {
                    "beam_id": bid,
                    "entity_id": eid,
                    "stable_key": stable,
                    "entity_type": row.get("entity_type"),
                    "recovery_potential": row.get("recovery_potential"),
                    "spatial_relationship": env.get("spatial_relationship"),
                    "min_distance_to_production_envelope": env.get(
                        "min_distance_to_production_envelope"
                    ),
                    "neighbour_ambiguity": bool(flags.get("neighbour_ambiguity")),
                    "inside_other_beam_envelope": bool(
                        flags.get("inside_other_beam_envelope")
                    ),
                    "target_beam_context": bool(flags.get("target_beam_context")),
                    "already_in_production_accepted": already,
                    "diagnostic_only": True,
                    "recovery_candidate_generated": False,
                    "note": "MEDIUM/LOW not in P1 HIGH recovery emission set",
                }
            )

    audit_rows = _sort_rows(audit_rows)
    recovery_candidates = _sort_rows(recovery_candidates)
    diagnostic_rows = _sort_rows(diagnostic_rows)

    # Stable key uniqueness
    keys = [r["stable_key"] for r in audit_rows]
    dup_keys = sorted({k for k in keys if keys.count(k) > 1})

    # Illegal cross-beam: recovery candidate accepted on >1 beam in this run
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
    illegal = list(multi)

    contam = contamination_report(
        audit_rows,
        duplicate_stable_keys=dup_keys,
        multi_beam_assignments=multi,
        illegal_cross_beam=illegal,
    )

    return {
        "phase_id": PHASE_ID,
        "model_version": MODEL_VERSION,
        "audit_rows": audit_rows,
        "recovery_candidates": recovery_candidates,
        "diagnostic_medium_low": diagnostic_rows,
        "contamination": contam,
        "parent_leader_map_size": len(parent_leaders),
    }
