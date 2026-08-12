"""Link QuantityIntent to accepted P2.5 evidence (annotation / leader / OWN)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .models import EvidenceLinks


def _chains_by_annotation(evidence: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for ch in (evidence.get("leader_chains") or {}).get("accepted") or []:
        aid = ch.get("annotation_id")
        if not aid:
            continue
        out.setdefault(str(aid), []).append(ch)
    return out


def _owned_by_annotation(evidence: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for og in evidence.get("owned_geometry") or []:
        aid = og.get("annotation_id")
        if aid:
            out.setdefault(str(aid), []).append(og)
    return out


def preferred_chain(
    chains: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Prefer BarCallout over StirrupNote when multiple chains share an annotation."""
    if not chains:
        return None
    for ch in chains:
        if ch.get("semantic_type") == "BarCallout":
            return ch
    return chains[0]


def link_annotation_evidence(
    *,
    beam_id: str,
    annotation: Dict[str, Any],
    evidence: Dict[str, Any],
) -> Tuple[EvidenceLinks, Dict[str, Any]]:
    """
    Build evidence links for an accepted annotation.
    Returns (links, context) where context includes role/semantic from OWN/chain.
    """
    aid = str(annotation.get("annotation_id") or "")
    chains_map = _chains_by_annotation(evidence)
    owned_map = _owned_by_annotation(evidence)
    chains = chains_map.get(aid) or []
    owned = owned_map.get(aid) or []
    ch = preferred_chain(chains)

    leader_id = None
    chain_sem = None
    if ch:
        chain_sem = ch.get("semantic_type")
        lids = ch.get("leaders") or []
        leader_id = lids[0] if lids else None

    ownership_id = None
    source_handle = None
    evidence_id = None
    role = None
    if owned:
        # Prefer TOP_BAR owned geometry when present
        og = next(
            (o for o in owned if str(o.get("semantic_role") or "").upper() == "TOP_BAR"),
            owned[0],
        )
        ownership_id = og.get("ownership_id")
        source_handle = og.get("source_handle")
        evidence_id = og.get("evidence_id")
        role = og.get("semantic_role")
        if not leader_id:
            leader_id = og.get("leader_id")
        if not chain_sem:
            chain_sem = og.get("chain_semantic_type")

    # If chain describes OWN but owned_geometry missing, pull OWN id from describes
    if ch and not ownership_id:
        for d in ch.get("describes") or []:
            if str(d).startswith("OWN::"):
                ownership_id = str(d)
                break

    links = EvidenceLinks(
        beam_id=beam_id,
        annotation_id=aid or None,
        leader_id=leader_id,
        ownership_id=ownership_id,
        source_handle=source_handle,
        evidence_id=evidence_id,
        chain_semantic_type=chain_sem,
    )
    ctx = {
        "chain": ch,
        "owned": owned,
        "role_hint": role,
        "chain_semantic_type": chain_sem,
    }
    return links, ctx


def is_rejected_annotation(annotation_id: str, evidence: Dict[str, Any]) -> bool:
    """Rejected evidence must not produce accepted QuantityIntent."""
    excluded = evidence.get("excluded_rejected_evidence") or {}
    # Annotations themselves are not listed as rejected bars; check rejected chains
    for ch in (evidence.get("leader_chains") or {}).get("rejected") or []:
        if str(ch.get("annotation_id")) == str(annotation_id):
            return True
    # If annotation is not in accepted list, treat as non-eligible (caller filters)
    accepted_ids = {
        str(a.get("annotation_id"))
        for a in evidence.get("annotations") or []
        if a.get("annotation_id")
    }
    return str(annotation_id) not in accepted_ids
