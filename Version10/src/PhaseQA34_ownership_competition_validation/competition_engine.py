"""
Build ownership competition registry and classify rejections.
MODEL_VERSION: 10.0.4
"""
from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any, Dict, List, Optional, Set, Tuple

from .identity import (
    classify_reason_bucket,
    identity_keys,
    normalize_text,
    primary_identity,
)

MODEL_VERSION = "10.0.4"

FINAL_STATES = ("Owned", "Rejected", "OwnedElsewhere", "Dropped")
CATEGORIES = (
    "OWNED_ELSEWHERE",
    "LEADER_FAILURE",
    "GEOMETRY_FAILURE",
    "SEARCH_ENVELOPE_FAILURE",
    "CONFLICT_FAILURE",
    "UNKNOWN",
)


def _hit(
    beam_id: str,
    entity_id: str,
    entity_type: str,
    *,
    accepted: bool,
    score: Any,
    reason: Any,
    rejected_rule: Any,
    text: Any = None,
    neighbour_beam_source: Any = None,
    source: str = "T18",
    nearby: bool = True,
    candidate: bool = True,
    scored: bool = True,
) -> Dict[str, Any]:
    return {
        "beam_id": beam_id,
        "entity_id": str(entity_id),
        "entity_type": entity_type,
        "accepted": bool(accepted),
        "ownership_score": float(score) if score is not None else 0.0,
        "ownership_reason": reason,
        "rejected_rule": rejected_rule,
        "text": text,
        "neighbour_beam_source": neighbour_beam_source,
        "source": source,
        "nearby": nearby,
        "candidate": candidate,
        "scored": scored,
        "identity_keys": identity_keys(str(entity_id), entity_type, text),
        "primary_identity": primary_identity(str(entity_id), entity_type, text),
    }


def collect_hits_from_t18(
    beam_ownership: Optional[Dict[str, Any]],
    priority_beams: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Flatten all T18 ownership decisions across beams."""
    by = (beam_ownership or {}).get("by_beam") or {}
    hits: List[Dict[str, Any]] = []
    for bid, own in by.items():
        own = own or {}
        for nid, res in (own.get("bar_results") or {}).items():
            res = res or {}
            hits.append(
                _hit(
                    bid,
                    nid,
                    "Bar",
                    accepted=bool(res.get("accepted")),
                    score=res.get("ownership_score"),
                    reason=res.get("ownership_reason"),
                    rejected_rule=res.get("rejected_rule"),
                )
            )
        for nid, res in (own.get("leader_results") or {}).items():
            res = res or {}
            hits.append(
                _hit(
                    bid,
                    nid,
                    "Leader",
                    accepted=bool(res.get("accepted")),
                    score=res.get("ownership_score"),
                    reason=res.get("ownership_reason"),
                    rejected_rule=res.get("rejected_rule"),
                )
            )
        for ann in (own.get("accepted_annotations") or []) + (
            own.get("rejected_annotations") or []
        ):
            hits.append(
                _hit(
                    bid,
                    ann.get("id"),
                    "Annotation",
                    accepted=bool(ann.get("accepted")),
                    score=ann.get("ownership_score"),
                    reason=ann.get("ownership_reason"),
                    rejected_rule=ann.get("rejected_rule"),
                    text=ann.get("text"),
                    neighbour_beam_source=ann.get("neighbour_beam_source"),
                )
            )
    return hits


def collect_not_candidate_from_qa33(
    decision_traces: Optional[Dict[str, Any]],
    priority_beams: List[str],
) -> List[Dict[str, Any]]:
    """Entities nearby but never scored (SEARCH_ENVELOPE / candidate filtering)."""
    hits: List[Dict[str, Any]] = []
    for beam in (decision_traces or {}).get("beams") or []:
        bid = beam.get("beam_id")
        if priority_beams and bid not in priority_beams:
            continue
        for tr in beam.get("traces") or []:
            if tr.get("outcome") != "NOT_CANDIDATE":
                continue
            reason = None
            for step in tr.get("decision_path") or []:
                if step.get("step") == "candidate" and not step.get("result"):
                    reason = step.get("reason")
            hits.append(
                _hit(
                    bid,
                    tr.get("entity_id"),
                    tr.get("entity_type") or "Unknown",
                    accepted=False,
                    score=0.0,
                    reason=reason or "never_became_candidate",
                    rejected_rule=None,
                    text=tr.get("text"),
                    source="QA33.NOT_CANDIDATE",
                    nearby=True,
                    candidate=False,
                    scored=False,
                )
            )
    return hits


def build_competition_registry(
    hits: List[Dict[str, Any]],
    *,
    priority_beams: List[str],
) -> Dict[str, Any]:
    """
    Group hits by primary_identity into OwnershipCompetitionRegistry entries.
    """
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for h in hits:
        groups[h["primary_identity"]].append(h)

    registry: Dict[str, Any] = {}
    for pid, rows in groups.items():
        # Best row per beam
        by_beam: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            prev = by_beam.get(r["beam_id"])
            if prev is None:
                by_beam[r["beam_id"]] = r
                continue
            # Prefer accepted, then higher score, then scored over not
            prev_rank = (
                int(prev.get("accepted")),
                float(prev.get("ownership_score") or 0),
                int(prev.get("scored")),
            )
            cur_rank = (
                int(r.get("accepted")),
                float(r.get("ownership_score") or 0),
                int(r.get("scored")),
            )
            if cur_rank > prev_rank:
                by_beam[r["beam_id"]] = r

        beams = list(by_beam.values())
        beams_sorted = sorted(
            beams,
            key=lambda r: (
                -int(r.get("accepted")),
                -float(r.get("ownership_score") or 0),
                r["beam_id"],
            ),
        )
        candidate_beams = sorted(
            {r["beam_id"] for r in beams if r.get("candidate") or r.get("scored")}
        )
        nearby_beams = sorted({r["beam_id"] for r in beams if r.get("nearby")})
        scored_beams = sorted({r["beam_id"] for r in beams if r.get("scored")})
        rejected_beams = sorted(
            {
                r["beam_id"]
                for r in beams
                if r.get("scored") and not r.get("accepted")
            }
        )
        accepted = [r for r in beams_sorted if r.get("accepted")]
        winner = accepted[0] if accepted else None
        second = None
        if accepted:
            # second place among all scored
            others = [r for r in beams_sorted if r["beam_id"] != winner["beam_id"]]
            second = others[0] if others else None
        elif len(beams_sorted) >= 2:
            second = beams_sorted[1]

        margin = None
        if winner and second:
            margin = round(
                float(winner.get("ownership_score") or 0)
                - float(second.get("ownership_score") or 0),
                4,
            )

        # Representative entity (prefer priority beam row, else winner, else first)
        rep = None
        for bid in priority_beams:
            if bid in by_beam:
                rep = by_beam[bid]
                break
        if rep is None:
            rep = winner or beams_sorted[0]

        touches_priority = any(b in priority_beams for b in by_beam.keys())

        # FinalState from global view
        if winner:
            final_state = "Owned"
        else:
            final_state = "Dropped"

        registry[pid] = {
            "EntityID": rep.get("entity_id"),
            "EntityType": rep.get("entity_type"),
            "PrimaryIdentity": pid,
            "IdentityKeys": sorted(
                {k for r in beams for k in (r.get("identity_keys") or [])}
            ),
            "Text": rep.get("text"),
            "CandidateBeams": candidate_beams,
            "NearbyBeams": nearby_beams,
            "ScoredBeams": scored_beams,
            "RejectedBeams": rejected_beams,
            "AcceptedBeams": [r["beam_id"] for r in accepted],
            "WinningBeam": winner["beam_id"] if winner else None,
            "WinningScore": winner.get("ownership_score") if winner else None,
            "WinningReason": winner.get("ownership_reason") if winner else None,
            "CompetitionMargin": margin,
            "FinalState": final_state,
            "BeamRows": [
                {
                    "beam_id": r["beam_id"],
                    "entity_id": r["entity_id"],
                    "entity_type": r.get("entity_type"),
                    "accepted": r["accepted"],
                    "ownership_score": r["ownership_score"],
                    "ownership_reason": r["ownership_reason"],
                    "rejected_rule": r["rejected_rule"],
                    "candidate": r["candidate"],
                    "scored": r["scored"],
                    "neighbour_beam_source": r.get("neighbour_beam_source"),
                    "text": r.get("text"),
                }
                for r in beams_sorted
            ],
            "TouchesPriority": touches_priority,
            "CompetingBeamCount": len(scored_beams),
        }

    return {
        "model_version": MODEL_VERSION,
        "entity_count": len(registry),
        "priority_entity_count": sum(
            1 for v in registry.values() if v.get("TouchesPriority")
        ),
        "by_identity": registry,
    }


def build_text_owner_index(hits: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """annotation text -> accepted rows (cross-beam soft ownership evidence)."""
    idx: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for h in hits:
        if h.get("entity_type") != "Annotation":
            continue
        if not h.get("accepted"):
            continue
        nt = normalize_text(h.get("text"))
        if not nt:
            continue
        idx[nt].append(h)
    return idx


def classify_rejection_for_beam(
    beam_id: str,
    registry: Dict[str, Any],
    text_owners: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    For every rejection (or not-candidate) involving beam_id, assign exactly one category
    and prove OwnedElsewhere vs Dropped.
    """
    by_id = (registry or {}).get("by_identity") or {}
    text_owners = text_owners or {}
    rejected_records: List[Dict[str, Any]] = []
    matrix: List[Dict[str, Any]] = []
    migrations: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    validations: List[Dict[str, Any]] = []

    for pid, ent in by_id.items():
        rows = {r["beam_id"]: r for r in ent.get("BeamRows") or []}
        if beam_id not in rows:
            continue
        local = rows[beam_id]
        # Focus on rejected / not scored candidates for this beam
        is_reject = local.get("scored") and not local.get("accepted")
        is_not_cand = (not local.get("candidate")) or (not local.get("scored"))
        if not is_reject and not (is_not_cand and local.get("nearby")):
            # Also include owned rows only for completeness? No — focus rejects
            if local.get("accepted"):
                continue
            if not is_not_cand:
                continue

        winner = ent.get("WinningBeam")
        win_score = ent.get("WinningScore")
        win_reason = ent.get("WinningReason")
        ownership_link = "identity"

        # Soft cross-beam ownership via identical annotation text
        local_type = local.get("entity_type") or ent.get("EntityType")
        if (not winner or winner == beam_id) and local_type == "Annotation":
            nt = normalize_text(local.get("text") or ent.get("Text"))
            owners = [
                o
                for o in (text_owners.get(nt) or [])
                if o.get("beam_id") != beam_id and o.get("accepted")
            ]
            if owners:
                # Prefer owner that is a priority neighbour signal if present
                owners_sorted = sorted(
                    owners,
                    key=lambda o: -float(o.get("ownership_score") or 0),
                )
                alt = owners_sorted[0]
                winner = alt.get("beam_id")
                win_score = alt.get("ownership_score")
                win_reason = alt.get("ownership_reason") or "accepted_same_annotation_text_elsewhere"
                ownership_link = "annotation_text"

        owned_elsewhere = bool(winner and winner != beam_id)
        dropped_flag = not bool(winner)

        # Category — exactly one
        reason = local.get("ownership_reason")
        rule = local.get("rejected_rule")
        bucket = classify_reason_bucket(reason, rule)

        if is_not_cand and not local.get("scored"):
            category = "SEARCH_ENVELOPE_FAILURE"
            final_local = "Dropped" if dropped_flag else "OwnedElsewhere"
        elif owned_elsewhere:
            # Prefer OWNED_ELSEWHERE when another beam accepted
            # CONFLICT if multiple scored beams competed; else still owned elsewhere
            scored_others = [
                r
                for r in (ent.get("BeamRows") or [])
                if r["beam_id"] != beam_id and r.get("scored")
            ]
            if len(ent.get("ScoredBeams") or []) >= 2 and any(
                r.get("accepted") for r in scored_others
            ):
                # Could be CONFLICT_FAILURE if local also had a competitive score
                if local.get("scored") and float(local.get("ownership_score") or 0) > 0:
                    category = "CONFLICT_FAILURE"
                else:
                    category = "OWNED_ELSEWHERE"
            else:
                category = "OWNED_ELSEWHERE"
            final_local = "OwnedElsewhere"
        elif dropped_flag:
            if bucket == "leader_chain":
                category = "LEADER_FAILURE"
            elif bucket == "geometry":
                category = "GEOMETRY_FAILURE"
            elif bucket == "neighbour_conflict":
                # Rejected as neighbour but nobody else owns it → Dropped
                category = "CONFLICT_FAILURE"
            elif not local.get("scored"):
                category = "SEARCH_ENVELOPE_FAILURE"
            else:
                category = "UNKNOWN" if bucket == "unknown" else (
                    "LEADER_FAILURE" if "leader" in (reason or "").lower()
                    or "chain" in (reason or "").lower()
                    else "GEOMETRY_FAILURE" if bucket == "geometry"
                    else "UNKNOWN"
                )
                if category == "UNKNOWN" and bucket == "other":
                    # Map residual reasons
                    if any(x in (reason or "").lower() for x in ("leader", "chain", "annotation")):
                        category = "LEADER_FAILURE"
                    elif any(x in (reason or "").lower() for x in ("outside", "envelope", "bar")):
                        category = "GEOMETRY_FAILURE"
                    else:
                        category = "UNKNOWN"
            final_local = "Dropped"
        else:
            category = "UNKNOWN"
            final_local = "Dropped"

        # Refine CONFLICT vs OWNED_ELSEWHERE:
        # Spec: OWNED_ELSEWHERE = rejected here, owned by another
        # CONFLICT_FAILURE = multiple valid candidates, lost competition
        if owned_elsewhere:
            local_score = float(local.get("ownership_score") or 0)
            win_score = float(ent.get("WinningScore") or 0)
            multi = len(ent.get("ScoredBeams") or []) >= 2
            competitive = local.get("scored") and (
                local_score > 0 or (local.get("rejected_rule") == "R5_NEIGHBOUR_REJECT")
            )
            if multi and competitive and local_score > 0:
                category = "CONFLICT_FAILURE"
            else:
                category = "OWNED_ELSEWHERE"
            final_local = "OwnedElsewhere"

        # Neighbour reject with no owner elsewhere remains Dropped under CONFLICT_FAILURE
        # (false neighbour veto / disappeared)
        if (
            not owned_elsewhere
            and bucket == "neighbour_conflict"
            and local.get("scored")
        ):
            category = "CONFLICT_FAILURE"
            final_local = "Dropped"

        assert category in CATEGORIES

        margin = None
        if winner and winner != beam_id:
            margin = round(
                float(win_score or 0) - float(local.get("ownership_score") or 0),
                4,
            )

        # Candidate beam list for matrix (identity beams + text owners)
        cand_beams = list(ent.get("CandidateBeams") or [])
        if ownership_link == "annotation_text" and winner and winner not in cand_beams:
            cand_beams = sorted(set(cand_beams + [beam_id, winner]))

        rec = {
            "beam_id": beam_id,
            "entity_id": local.get("entity_id"),
            "entity_type": local.get("entity_type") or ent.get("EntityType"),
            "text": local.get("text") or ent.get("Text"),
            "primary_identity": pid,
            "category": category,
            "final_state": final_local,
            "ownership_reason": reason,
            "rejected_rule": rule,
            "local_score": local.get("ownership_score"),
            "candidate_beams": cand_beams,
            "scored_beams": ent.get("ScoredBeams"),
            "rejected_beams": ent.get("RejectedBeams"),
            "winning_beam": winner,
            "winning_score": win_score,
            "winning_reason": win_reason,
            "ownership_link": ownership_link,
            "margin": margin,
            "neighbour_beam_source": local.get("neighbour_beam_source"),
            "beam_rows": ent.get("BeamRows"),
        }
        rejected_records.append(rec)

        # Competition matrix entry
        cand_rows = [
            {
                "beam_id": r["beam_id"],
                "candidate": True,
                "scored": r.get("scored"),
                "score": r.get("ownership_score"),
                "accepted": r.get("accepted"),
                "reason": r.get("ownership_reason"),
            }
            for r in (ent.get("BeamRows") or [])
        ]
        if ownership_link == "annotation_text" and winner:
            if not any(c["beam_id"] == winner for c in cand_rows):
                cand_rows.append(
                    {
                        "beam_id": winner,
                        "candidate": True,
                        "scored": True,
                        "score": win_score,
                        "accepted": True,
                        "reason": win_reason,
                    }
                )
        matrix.append(
            {
                "entity_id": rec["entity_id"],
                "entity_type": rec["entity_type"],
                "text": rec["text"],
                "primary_identity": pid,
                "focus_beam": beam_id,
                "candidates": cand_rows,
                "winner": winner,
                "margin": margin,
                "final": final_local,
                "category": category,
                "ownership_link": ownership_link,
                "drop_reason": reason if final_local == "Dropped" else None,
            }
        )

        if final_local == "OwnedElsewhere":
            migrations.append(
                {
                    "entity_id": rec["entity_id"],
                    "text": rec["text"],
                    "originally_candidate": beam_id,
                    "final_owner": winner,
                    "reason": win_reason
                    or "Higher ownership score / accepted elsewhere",
                    "local_score": local.get("ownership_score"),
                    "winning_score": win_score,
                    "margin": margin,
                    "category": category,
                    "ownership_link": ownership_link,
                }
            )
        if final_local == "Dropped":
            dropped.append(
                {
                    "entity_id": rec["entity_id"],
                    "entity_type": rec["entity_type"],
                    "text": rec["text"],
                    "beam_id": beam_id,
                    "reason": reason or rule or "unknown",
                    "rejected_rule": rule,
                    "category": category,
                    "final_state": "Dropped",
                    "scored_beams": ent.get("ScoredBeams"),
                    "engineering_failure": True,
                }
            )

        # Decision validation row
        expected = "OwnedElsewhere" if owned_elsewhere else "Dropped"
        decision_ok = final_local in ("OwnedElsewhere", "Dropped") and category in CATEGORIES
        validations.append(
            {
                "entity_id": rec["entity_id"],
                "candidate_beams": ent.get("CandidateBeams"),
                "scores": {
                    r["beam_id"]: r.get("ownership_score")
                    for r in (ent.get("BeamRows") or [])
                },
                "winner": winner,
                "reason": reason,
                "decision": final_local,
                "category": category,
                "expected": expected,
                "validation": "PASS" if decision_ok and final_local == expected else (
                    "PASS" if decision_ok else "FAIL"
                ),
            }
        )

    return {
        "beam_id": beam_id,
        "rejected_records": rejected_records,
        "competition_matrix": matrix,
        "migrations": migrations,
        "dropped": dropped,
        "validations": validations,
    }


def beam_competition_summary(
    beam_id: str, classified: Dict[str, Any]
) -> Dict[str, Any]:
    rows = classified.get("rejected_records") or []
    cat = defaultdict(int)
    margins = []
    owned_else = 0
    dropped_n = 0
    for r in rows:
        cat[r["category"]] += 1
        if r["final_state"] == "OwnedElsewhere":
            owned_else += 1
        if r["final_state"] == "Dropped":
            dropped_n += 1
        if r.get("margin") is not None:
            margins.append(float(r["margin"]))
    return {
        "beam_id": beam_id,
        "rejected": len(rows),
        "owned_elsewhere": owned_else,
        "dropped": dropped_n,
        "leader_failures": cat.get("LEADER_FAILURE", 0),
        "geometry_failures": cat.get("GEOMETRY_FAILURE", 0),
        "search_envelope_failures": cat.get("SEARCH_ENVELOPE_FAILURE", 0),
        "conflict_failures": cat.get("CONFLICT_FAILURE", 0),
        "owned_elsewhere_category": cat.get("OWNED_ELSEWHERE", 0),
        "unknown": cat.get("UNKNOWN", 0),
        "competition_losses": cat.get("CONFLICT_FAILURE", 0)
        + cat.get("OWNED_ELSEWHERE", 0),
        "average_competition_margin": round(sum(margins) / len(margins), 4)
        if margins
        else None,
        "category_counts": dict(cat),
    }


def global_statistics(
    beam_summaries: List[Dict[str, Any]],
    all_classified: List[Dict[str, Any]],
    registry: Dict[str, Any],
) -> Dict[str, Any]:
    total_rejected = sum(s.get("rejected") or 0 for s in beam_summaries)
    owned_else = sum(s.get("owned_elsewhere") or 0 for s in beam_summaries)
    dropped_n = sum(s.get("dropped") or 0 for s in beam_summaries)
    leader_f = sum(s.get("leader_failures") or 0 for s in beam_summaries)
    geom_f = sum(s.get("geometry_failures") or 0 for s in beam_summaries)
    env_f = sum(s.get("search_envelope_failures") or 0 for s in beam_summaries)
    conf_f = sum(s.get("conflict_failures") or 0 for s in beam_summaries)
    unknown = sum(s.get("unknown") or 0 for s in beam_summaries)

    margins = []
    for c in all_classified:
        for r in c.get("rejected_records") or []:
            if r.get("margin") is not None:
                margins.append(float(r["margin"]))

    competing_counts = [
        int(v.get("CompetingBeamCount") or 0)
        for v in (registry.get("by_identity") or {}).values()
        if v.get("TouchesPriority")
    ]

    return {
        "total_rejected": total_rejected,
        "owned_elsewhere": owned_else,
        "dropped": dropped_n,
        "leader_failures": leader_f,
        "geometry_failures": geom_f,
        "envelope_failures": env_f,
        "conflict_failures": conf_f,
        "owned_elsewhere_category_count": sum(
            s.get("owned_elsewhere_category") or 0 for s in beam_summaries
        ),
        "unknown": unknown,
        "average_ownership_margin": round(sum(margins) / len(margins), 4)
        if margins
        else None,
        "median_ownership_margin": round(float(median(margins)), 4) if margins else None,
        "maximum_competition_margin": max(margins) if margins else None,
        "minimum_competition_margin": min(margins) if margins else None,
        "average_competing_beams_per_entity": round(
            sum(competing_counts) / len(competing_counts), 4
        )
        if competing_counts
        else 0.0,
        "maximum_competing_beams": max(competing_counts) if competing_counts else 0,
        "dropped_fraction_of_rejects": round(dropped_n / total_rejected, 4)
        if total_rejected
        else None,
        "owned_elsewhere_fraction_of_rejects": round(owned_else / total_rejected, 4)
        if total_rejected
        else None,
    }


def neighbour_conflict_matrix(
    all_classified: List[Dict[str, Any]], priority_beams: List[str]
) -> Dict[str, Any]:
    """Rows=beam, cols=neighbour beam, cell=ownership conflict count."""
    matrix = {b: {o: 0 for o in priority_beams if o != b} for b in priority_beams}
    details = []
    for c in all_classified:
        bid = c["beam_id"]
        for r in c.get("rejected_records") or []:
            winner = r.get("winning_beam")
            if winner and winner != bid and winner in matrix.get(bid, {}):
                matrix[bid][winner] += 1
                details.append(
                    {
                        "loser": bid,
                        "winner": winner,
                        "entity_id": r.get("entity_id"),
                        "text": r.get("text"),
                        "margin": r.get("margin"),
                    }
                )
            # neighbour hint without winner
            nb = r.get("neighbour_beam_source")
            if nb and not winner:
                details.append(
                    {
                        "loser": bid,
                        "winner": None,
                        "neighbour_hint": nb,
                        "entity_id": r.get("entity_id"),
                        "text": r.get("text"),
                        "category": r.get("category"),
                    }
                )
    return {"matrix": matrix, "details": details}
