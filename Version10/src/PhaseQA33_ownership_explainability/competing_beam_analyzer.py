"""
Stage 3 — Competing beam analysis from persisted T18 results.
MODEL_VERSION: 10.0.3
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set


def build_competition_index(
    beam_ownership: Optional[Dict[str, Any]],
    priority_beams: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Scan all beams' ownership results and group by entity id.

    T18 is independent-per-beam (not a global auction). Competing beams are
    those that independently considered the same entity id.
    """
    by = (beam_ownership or {}).get("by_beam") or {}
    # entity_id -> list of {beam_id, score, accepted, reason, rejected_rule, type}
    hits: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    beam_ids = list(priority_beams) if priority_beams else list(by.keys())
    # Always scan all beams for competition, but tag priority
    scan_ids = list(by.keys())

    for bid in scan_ids:
        own = by.get(bid) or {}
        for nid, res in (own.get("bar_results") or {}).items():
            hits[str(nid)].append(
                _hit(bid, nid, "Bar", res or {})
            )
        for nid, res in (own.get("leader_results") or {}).items():
            hits[str(nid)].append(
                _hit(bid, nid, "Leader", res or {})
            )
        for ann in (own.get("accepted_annotations") or []) + (
            own.get("rejected_annotations") or []
        ):
            hits[str(ann.get("id"))].append(
                _hit(bid, ann.get("id"), "Annotation", ann)
            )

    by_entity: Dict[str, Any] = {}
    multi = 0
    for eid, rows in hits.items():
        # Dedup beam rows (keep best score per beam)
        best: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            prev = best.get(r["beam_id"])
            if prev is None or float(r.get("ownership_score") or 0) > float(
                prev.get("ownership_score") or 0
            ):
                best[r["beam_id"]] = r
        rows2 = list(best.values())
        rows2.sort(key=lambda r: (-float(r.get("ownership_score") or 0), r["beam_id"]))
        competing = [r["beam_id"] for r in rows2]
        accepted_beams = [r["beam_id"] for r in rows2 if r.get("accepted")]
        winner = accepted_beams[0] if accepted_beams else (
            rows2[0]["beam_id"] if rows2 else None
        )
        winner_row = next((r for r in rows2 if r["beam_id"] == winner), None)
        second = rows2[1] if len(rows2) > 1 else None
        margin = None
        if winner_row and second:
            margin = round(
                float(winner_row.get("ownership_score") or 0)
                - float(second.get("ownership_score") or 0),
                4,
            )
        if len(competing) >= 2:
            multi += 1

        rankings = [
            {
                "rank": i + 1,
                "beam_id": r["beam_id"],
                "ownership_score": r.get("ownership_score"),
                "accepted": r.get("accepted"),
                "ownership_reason": r.get("ownership_reason"),
                "rejected_rule": r.get("rejected_rule"),
                "entity_type": r.get("entity_type"),
            }
            for i, r in enumerate(rows2)
        ]

        by_entity[eid] = {
            "entity_id": eid,
            "entity_type": rows2[0].get("entity_type") if rows2 else None,
            "considered_by": competing,
            "competing_beams": competing,
            "beam_count": len(competing),
            "rankings": rankings,
            "winning_beam": winner,
            "margin": margin,
            "reason_winner_selected": (
                (winner_row or {}).get("ownership_reason")
                if winner_row and winner_row.get("accepted")
                else "highest_score_among_considering_beams_or_sole_accepter"
            ),
            "losers": [
                {
                    "beam_id": r["beam_id"],
                    "ownership_score": r.get("ownership_score"),
                    "reason_loser_rejected": r.get("ownership_reason")
                    or r.get("rejected_rule")
                    or ("not_accepted_by_this_beam"),
                }
                for r in rows2
                if r["beam_id"] != winner
            ],
            "in_priority_set": any(b in (priority_beams or []) for b in competing),
        }

    # Secondary diagnostic: same annotation TEXT considered by multiple beams
    # (T18 node ids are beam-local; text collision reveals engineering competition)
    text_hits: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for bid in scan_ids:
        own = by.get(bid) or {}
        for ann in (own.get("accepted_annotations") or []) + (
            own.get("rejected_annotations") or []
        ):
            text = str(ann.get("text") or "").strip()
            if not text:
                continue
            text_hits[text].append(
                {
                    "beam_id": bid,
                    "entity_id": str(ann.get("id")),
                    "accepted": bool(ann.get("accepted")),
                    "ownership_score": ann.get("ownership_score"),
                    "ownership_reason": ann.get("ownership_reason"),
                    "rejected_rule": ann.get("rejected_rule"),
                    "neighbour_beam_source": ann.get("neighbour_beam_source"),
                }
            )

    by_text: Dict[str, Any] = {}
    text_multi = 0
    for text, rows in text_hits.items():
        beams = sorted({r["beam_id"] for r in rows})
        if len(beams) < 2:
            continue
        # Restrict to cases touching priority beams
        if priority_beams and not any(b in priority_beams for b in beams):
            continue
        text_multi += 1
        accepted = [r for r in rows if r.get("accepted")]
        by_text[text] = {
            "annotation_text": text,
            "considered_by": beams,
            "beam_count": len(beams),
            "rows": rows,
            "accepted_by": sorted({r["beam_id"] for r in accepted}),
            "rejected_by": sorted(
                {r["beam_id"] for r in rows if not r.get("accepted")}
            ),
            "note": (
                "T18 entity ids are beam-scoped; this groups identical annotation "
                "text across beams for explainability only."
            ),
        }

    return {
        "entity_count": len(by_entity),
        "multi_beam_entity_count": multi,
        "average_competing_beams": round(
            sum(v["beam_count"] for v in by_entity.values()) / max(len(by_entity), 1),
            4,
        ),
        "by_entity": by_entity,
        "by_annotation_text": by_text,
        "multi_beam_annotation_text_count": text_multi,
        "priority_beams": list(beam_ids),
    }


def _hit(beam_id: str, eid: Any, etype: str, res: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "beam_id": beam_id,
        "entity_id": str(eid),
        "entity_type": etype,
        "accepted": bool(res.get("accepted")),
        "ownership_score": res.get("ownership_score"),
        "ownership_reason": res.get("ownership_reason"),
        "rejected_rule": res.get("rejected_rule"),
        "accepted_rules": res.get("accepted_rules") or [],
    }
