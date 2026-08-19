"""P2.6.10-A evaluation: reusability, B55 diagnostics, phase status."""
from __future__ import annotations

from typing import Any, Dict, List

from .config import ALLOWED_FINAL, PRODUCTION_ACTION, TARGET_BEAMS


def _yes_no(flag: bool) -> str:
    return "YES" if flag else "NO"


def b55_diagnostics(record: Dict[str, Any]) -> Dict[str, Any]:
    detail = (record.get("crops") or {}).get("detail") or {}
    context = (record.get("crops") or {}).get("context") or {}
    q = detail.get("quality") or {}
    cq = context.get("quality") or {}
    mark = record.get("mark") or {}
    title_ok = bool(mark.get("x") is not None and q.get("beam_title_included"))
    geom_ok = bool(q.get("beam_geometry_included"))
    neighbors_ctx = list(cq.get("neighbor_titles_in_crop") or [])
    neighbors_det = list(q.get("neighbor_titles_in_crop") or [])
    reinf = int(q.get("reinforcement_text_near_mark") or 0)
    unrelated = bool(neighbors_det)
    clip = bool(q.get("clipping_detected"))
    read = str(q.get("readability_status") or "POOR")
    correct = bool(title_ok and geom_ok and reinf > 0)
    ready = "NOT_READY"
    if correct and read == "GOOD" and not clip:
        ready = "READY"
    elif title_ok and geom_ok:
        ready = "PARTIAL"
    return {
        "B55_title_located": _yes_no(title_ok),
        "B55_beam_geometry_located": _yes_no(geom_ok),
        "correct_visual_detail_captured": _yes_no(correct),
        "neighboring_detail_visible": _yes_no(bool(neighbors_ctx)),
        "target_reinforcement_visually_present": _yes_no(reinf > 0),
        "unrelated_reinforcement_captured": _yes_no(unrelated),
        "clipping": _yes_no(clip),
        "text_readability": read,
        "Vision_readiness": ready,
        "neighbor_titles_in_context": neighbors_ctx,
        "neighbor_titles_in_detail": neighbors_det,
        "detail_reinforcement_text_count": reinf,
        "notes": list(record.get("notes") or []),
    }


def classify_reusability(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "NO_EXISTING_CAPABILITY"
    rendered = all((r.get("crops") or {}).get("detail") and (r.get("crops") or {}).get("context") for r in records)
    titles = all((r.get("mark") or {}).get("x") is not None for r in records)
    independent = all(r.get("annotation_association_dependency") is False for r in records)
    geom = all(((r.get("crops") or {}).get("detail") or {}).get("quality", {}).get("beam_geometry_included") for r in records)
    if rendered and titles and independent and geom:
        return "REUSABLE_WITH_SMALL_ADAPTER"
    if rendered and not titles:
        return "RENDERER_EXISTS_LOCALIZATION_MISSING"
    if not rendered and titles:
        return "RENDERER_EXISTS_LOCALIZATION_MISSING"
    return "EXISTING_CODE_NOT_SUITABLE"


def classify_final_decision(
    *,
    reusability: str,
    records: List[Dict[str, Any]],
    b55: Dict[str, Any],
    tests_ok: bool,
    fingerprints_ok: bool,
) -> str:
    if not tests_ok or not fingerprints_ok:
        return "INVESTIGATION_FAILED"
    ready_n = sum(
        1
        for r in records
        if ((r.get("crops") or {}).get("detail") or {}).get("quality", {}).get("vision_readiness") in ("READY", "PARTIAL")
    )
    b55_ready = b55.get("Vision_readiness") in ("READY", "PARTIAL")
    if reusability == "REUSABLE_WITH_SMALL_ADAPTER" and ready_n == TARGET_BEAMS and b55_ready:
        if b55.get("Vision_readiness") == "READY":
            return "RENDERING_READY_WITH_ADAPTER"
        return "RENDERING_READY_WITH_ADAPTER"
    if reusability == "RENDERER_EXISTS_LOCALIZATION_MISSING":
        return "LOCALIZATION_GAP_REQUIRES_IMPLEMENTATION"
    if reusability == "NO_EXISTING_CAPABILITY":
        return "INVESTIGATION_FAILED"
    if ready_n < TARGET_BEAMS or not b55_ready:
        return "LOCALIZATION_GAP_REQUIRES_IMPLEMENTATION"
    return "EXISTING_RENDERER_NOT_SUITABLE"


def classify_phase_status(
    *,
    tests_ok: bool,
    fingerprints_ok: bool,
    six_beams: bool,
    crops_complete: bool,
    reusability: str,
    final_decision: str,
) -> str:
    if not tests_ok or not fingerprints_ok or not six_beams or not crops_complete:
        return "FAILED"
    if final_decision in ("RENDERING_READY_FOR_P2_6_10", "RENDERING_READY_WITH_ADAPTER"):
        return "PASS"
    if final_decision == "LOCALIZATION_GAP_REQUIRES_IMPLEMENTATION":
        return "PARTIAL"
    return "FAILED"


def production_invariants(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "all_shadow_only": all(r.get("shadow_only") is True for r in records) if records else False,
        "all_no_change": all(r.get("production_action") == PRODUCTION_ACTION for r in records) if records else False,
        "any_production_routing_changed": any(r.get("production_routing_changed") for r in records),
        "count": len(records),
        "live_vision_invoked": False,
    }


def assert_allowed_final(decision: str) -> str:
    if decision not in ALLOWED_FINAL:
        raise ValueError(f"illegal final decision {decision!r}")
    return decision


__all__ = [
    "assert_allowed_final",
    "b55_diagnostics",
    "classify_final_decision",
    "classify_phase_status",
    "classify_reusability",
    "production_invariants",
]
