"""Deterministic spatial completeness + failure taxonomy. No LLM. No GT coords."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from PhaseP2610B_adaptive_beam_detail_crop.completeness import evaluate_completeness

STATUS_PRESENT = "PRESENT"
STATUS_NA = "NOT_APPLICABLE"
STATUS_UNKNOWN = "NOT_DETERMINABLE"
STATUS_MISSING = "MISSING"

FAILURE_CATEGORIES = (
    "MISSING_TITLE",
    "MISSING_GEOMETRY",
    "MISSING_TOP_EVIDENCE",
    "MISSING_BOTTOM_EVIDENCE",
    "MISSING_STIRRUP_EVIDENCE",
    "MISSING_DIMENSION_EVIDENCE",
    "MISSING_LEADER_EVIDENCE",
    "VERTICAL_TRUNCATION",
    "HORIZONTAL_TRUNCATION",
    "NEIGHBOR_TITLE_CONTAMINATION",
    "NEIGHBOR_DETAIL_CONTAMINATION",
    "EXCESSIVE_SLIVER",
    "EMPTY_OR_NEAR_EMPTY_CROP",
    "RENDER_FAILURE",
    "DISCOVERY_ASSOCIATION_FAILURE",
    "OTHER_DETERMINISTIC_FAILURE",
)


def _yna_to_status(val: Any) -> str:
    if val in ("YES", True):
        return STATUS_PRESENT
    if val in ("N/A", None):
        return STATUS_NA
    if val in ("NO", False):
        return STATUS_MISSING
    return STATUS_UNKNOWN


def _inside(x: float, y: float, box: Sequence[float], margin: float = 0.0) -> bool:
    xmin, ymin, xmax, ymax = box
    return (xmin - margin) <= x <= (xmax + margin) and (ymin - margin) <= y <= (ymax + margin)


def _empty_extent(extent: Optional[Sequence[float]]) -> bool:
    if not extent or len(extent) < 4:
        return True
    xmin, ymin, xmax, ymax = (float(v) for v in extent[:4])
    return (xmax - xmin) < 200.0 or (ymax - ymin) < 200.0


def _sliver_status(beam_id: str, extent: Sequence[float], titles: List[Dict[str, Any]]) -> str:
    """Neighbor titles just outside the crop are packed-sheet slivers, not contamination."""
    if not extent:
        return STATUS_NA
    xmin, ymin, xmax, ymax = (float(v) for v in extent[:4])
    near = 0
    for t in titles or []:
        nid = str(t.get("beam_id") or "")
        if not nid or nid.upper() == beam_id.upper():
            continue
        try:
            x, y = float(t["x"]), float(t["y"])
        except (TypeError, ValueError, KeyError):
            continue
        if _inside(x, y, extent, margin=-40.0):
            continue
        pad = 220.0
        if _inside(x, y, extent, margin=pad):
            near += 1
    if near:
        return STATUS_PRESENT
    return STATUS_NA


def validate_detail(
    *,
    beam_id: str,
    extent: Optional[Sequence[float]],
    mark: Optional[Dict[str, Any]],
    outline: Optional[Sequence[float]],
    evidence: List[Dict[str, Any]],
    titles: List[Dict[str, Any]],
    rendered: bool,
    discovery_ok: bool,
) -> Dict[str, Any]:
    failures: List[str] = []
    notes: List[str] = []
    if not discovery_ok or mark is None:
        failures.append("DISCOVERY_ASSOCIATION_FAILURE")
        return _record(
            beam_id,
            failures,
            notes + ["no independent title mark"],
            rendered=rendered,
            title=STATUS_MISSING,
        )
    if not rendered:
        failures.append("RENDER_FAILURE")
    if _empty_extent(extent):
        failures.append("EMPTY_OR_NEAR_EMPTY_CROP")
    raw = evaluate_completeness(
        beam_id=beam_id,
        extent=extent or (0.0, 0.0, 0.0, 0.0),
        mark=mark,
        outline=outline,
        evidence=list(evidence or []),
        titles=titles,
    )
    title = STATUS_PRESENT if raw.get("title_visible") == "YES" else STATUS_MISSING
    geom = STATUS_PRESENT if raw.get("beam_geometry_visible") == "YES" else STATUS_MISSING
    top = _yna_to_status(raw.get("top_reinforcement_visible"))
    bottom = _yna_to_status(raw.get("bottom_reinforcement_visible"))
    stirrup = _yna_to_status(raw.get("stirrup_visible"))
    dims = _yna_to_status(raw.get("relevant_dimensions_visible_when_present"))
    neighbor_title = (
        STATUS_PRESENT if raw.get("unrelated_neighbor_detail_present") == "YES" else STATUS_NA
    )
    if title == STATUS_MISSING:
        failures.append("MISSING_TITLE")
    if geom == STATUS_MISSING:
        failures.append("MISSING_GEOMETRY")
    if top == STATUS_MISSING:
        failures.append("MISSING_TOP_EVIDENCE")
    if bottom == STATUS_MISSING:
        failures.append("MISSING_BOTTOM_EVIDENCE")
    if stirrup == STATUS_MISSING:
        failures.append("MISSING_STIRRUP_EVIDENCE")
    if dims == STATUS_MISSING:
        failures.append("MISSING_DIMENSION_EVIDENCE")
    if neighbor_title == STATUS_PRESENT:
        failures.append("NEIGHBOR_TITLE_CONTAMINATION")
    missing = list(raw.get("missing_evidence") or [])
    for row in missing:
        try:
            dx, dy = abs(float(row.get("dx") or 0.0)), abs(float(row.get("dy") or 0.0))
        except (TypeError, ValueError):
            dx = dy = 0.0
        if dy >= dx:
            if "VERTICAL_TRUNCATION" not in failures:
                failures.append("VERTICAL_TRUNCATION")
        elif "HORIZONTAL_TRUNCATION" not in failures:
            failures.append("HORIZONTAL_TRUNCATION")
    sliver = _sliver_status(beam_id, extent or (0, 0, 0, 0), titles)
    # Leaders are not a first-class P2.6.10-B evidence kind; do not invent PRESENT/MISSING.
    leader = STATUS_UNKNOWN
    notes.append("leader_status=NOT_DETERMINABLE; P2.6.10-B does not collect LEADER entities")
    notes.append(
        "PASS requires title+geometry present, no MISSING applicable evidence, "
        "no neighbor titles inside the crop, and a successful render. "
        "Packed-sheet slivers outside the title insert do not fail the crop."
    )
    overall = "PASS" if not failures else "FAIL"
    return {
        "beam_id": beam_id,
        "source_set": "Fourth",
        "title_status": title,
        "geometry_status": geom,
        "top_evidence_status": top,
        "bottom_evidence_status": bottom,
        "stirrup_evidence_status": stirrup,
        "dimension_evidence_status": dims,
        "leader_evidence_status": leader,
        "neighbor_title_status": neighbor_title,
        "neighbor_detail_status": STATUS_UNKNOWN,
        "sliver_status": sliver,
        "completeness_status": overall,
        "failure_categories": failures,
        "deterministic_notes": notes,
        "p2610b_complete_flag": raw.get("complete"),
        "missing_evidence": missing,
        "neighbor_titles_in_crop": raw.get("neighbor_titles_in_crop") or [],
        "evidence_in_crop": raw.get("evidence_in_crop"),
        "evidence_total": raw.get("evidence_total"),
        "pass_logic": (
            "FAIL if any failure_categories; else PASS. "
            "NOT_APPLICABLE evidence does not fail. Slivers do not fail."
        ),
    }


def _record(
    beam_id: str,
    failures: List[str],
    notes: List[str],
    *,
    rendered: bool,
    title: str,
) -> Dict[str, Any]:
    return {
        "beam_id": beam_id,
        "source_set": "Fourth",
        "title_status": title,
        "geometry_status": STATUS_UNKNOWN,
        "top_evidence_status": STATUS_UNKNOWN,
        "bottom_evidence_status": STATUS_UNKNOWN,
        "stirrup_evidence_status": STATUS_UNKNOWN,
        "dimension_evidence_status": STATUS_UNKNOWN,
        "leader_evidence_status": STATUS_UNKNOWN,
        "neighbor_title_status": STATUS_UNKNOWN,
        "neighbor_detail_status": STATUS_UNKNOWN,
        "sliver_status": STATUS_UNKNOWN,
        "completeness_status": "FAIL",
        "failure_categories": failures,
        "deterministic_notes": notes,
        "rendered": rendered,
    }


__all__ = ["FAILURE_CATEGORIES", "validate_detail"]
