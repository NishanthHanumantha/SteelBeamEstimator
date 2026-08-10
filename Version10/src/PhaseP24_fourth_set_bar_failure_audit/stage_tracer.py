"""
Stage-by-stage GT bar failure attribution.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .artefacts import FourthSetBundle
from .config import TEXT_PRIMARY_ROLES, TOP_ROLES
from .dxf_probe import classify_dxf

_ROLE_EQUIV = {"STIRRUP_HOOK": "STIRRUP", "STIRRUP": "STIRRUP"}


def _role_key(role: Optional[str]) -> str:
    r = (role or "UNKNOWN").upper()
    return _ROLE_EQUIV.get(r, r)


def _is_top(role: str) -> bool:
    r = role.upper()
    return r in TOP_ROLES or r.startswith("TOP_")


def _is_bottom(role: str) -> bool:
    r = role.upper()
    return r.startswith("BOTTOM_")


def _qty_close(a: float, b: float) -> bool:
    if a <= 0 and b <= 0:
        return True
    if a <= 0 or b <= 0:
        return False
    return abs(a - b) <= max(0.5, 0.05 * max(a, b))


def _parse_callout_dia(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"[YyTt]\s*(\d{1,2})\b", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d{1,2})\s*mm\b", text, re.I)
    if m:
        return int(m.group(1))
    return None


def _parse_callout_qty(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d+)\s*[-xX]?\s*[YyTt]\s*\d+", text)
    if m:
        return float(m.group(1))
    return None


def _r13_bars(model: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key in (
        "top_main_bars",
        "bottom_main_bars",
        "top_extra_bars",
        "bottom_extra_bars",
        "side_face_reinforcement",
        "stirrups",
        "spacer_bars",
        "chair_bars",
        "supplementary_bars",
    ):
        for b in model.get(key) or []:
            out.append(b)
    return out


def _zone_bars(physical: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
    role_u = role.upper()
    out = []
    for b in physical:
        attrs = b.get("attributes") or b
        place = str(attrs.get("vertical_placement") or "").upper()
        if _is_top(role_u) and "TOP" in place:
            out.append(b)
        elif _is_bottom(role_u) and "BOTTOM" in place:
            out.append(b)
        elif role_u in TEXT_PRIMARY_ROLES:
            out.append(b)
        elif place:
            out.append(b)
    return out


def _beam_ctx(bundle: FourthSetBundle, beam_id: str) -> Dict[str, Any]:
    own = (bundle.beam_ownership.get("by_beam") or {}).get(beam_id) or {}
    t16 = bundle.t16_by_beam.get(beam_id) or []
    graph_bars = bundle.bars_by_beam.get(beam_id) or []
    r31 = bundle.r31_by_beam.get(beam_id) or []
    r13 = bundle.r13_by_beam.get(beam_id)
    accepted_anns = list(own.get("accepted_annotations") or [])
    rejected_anns = list(own.get("rejected_annotations") or [])
    accepted_chains = list(own.get("accepted_chains") or [])
    rejected_chains = list(own.get("rejected_chains") or [])
    bar_results = list(own.get("bar_results") or [])
    leaders = list(own.get("leader_results") or [])

    line_ents = [
        e
        for e in t16
        if str(e.get("type") or "").upper()
        in {"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "SPLINE"}
    ]
    return {
        "beam_id": beam_id,
        "ownership": own,
        "t16": t16,
        "t16_lines": line_ents,
        "graph_bars": graph_bars,
        "r31_bars": r31,
        "r13": r13,
        "r13_bars": _r13_bars(r13) if r13 else [],
        "accepted_anns": accepted_anns,
        "rejected_anns": rejected_anns,
        "accepted_chains": accepted_chains,
        "rejected_chains": rejected_chains,
        "bar_results": bar_results,
        "leaders": leaders,
        "beam_in_ownership": bool(own),
        "beam_in_r13": r13 is not None,
    }


def _find_r13_candidate(
    r13_bars: List[Dict[str, Any]], role: str, diameter: Any, quantity: float
) -> Optional[Dict[str, Any]]:
    rk = _role_key(role)
    role_hits = [
        b for b in r13_bars if _role_key(str(b.get("semantic_role") or "")) == rk
    ]
    if not role_hits:
        return None
    for b in role_hits:
        dia = b.get("diameter_mm")
        if diameter is not None and dia is not None and int(dia) == int(diameter):
            if _qty_close(float(b.get("quantity") or 0), float(quantity or 0)):
                return b
    for b in role_hits:
        dia = b.get("diameter_mm")
        if diameter is not None and dia is not None and int(dia) == int(diameter):
            return b
    return role_hits[0]


def _annotation_match(
    anns: List[Dict[str, Any]], diameter: Any, quantity: float, role: str
) -> Tuple[Optional[Dict[str, Any]], str]:
    if not anns:
        return None, "NO_ANNOTATION"
    scored = []
    for a in anns:
        text = str(a.get("text") or "")
        dia = _parse_callout_dia(text)
        qty = _parse_callout_qty(text)
        score = 0
        if diameter is not None and dia is not None and int(dia) == int(diameter):
            score += 2
        if qty is not None and _qty_close(qty, float(quantity or 0)):
            score += 1
        role_u = role.upper()
        if role_u in TEXT_PRIMARY_ROLES and (
            "STIRR" in text.upper() or "@" in text or "SPACER" in text.upper()
        ):
            score += 2
        if score:
            scored.append((score, a))
    if not scored:
        # any accepted annotation present → ambiguous association
        return anns[0], "AMBIGUOUS"
    scored.sort(key=lambda x: (-x[0], str(x[1].get("id") or "")))
    best = scored[0]
    if best[0] >= 2:
        return best[1], "CORRECT"
    return best[1], "AMBIGUOUS"


def _leader_status(
    ctx: Dict[str, Any], ann: Optional[Dict[str, Any]], role: str
) -> Tuple[str, Optional[str]]:
    if role.upper() in TEXT_PRIMARY_ROLES and ann is None:
        return "NO_LEADER_REQUIRED", None
    if ann is None:
        return "AMBIGUOUS", None
    ann_id = ann.get("id") or ann.get("annotation_id")
    for ch in ctx["accepted_chains"]:
        if (ch.get("annotation_id") or ch.get("id")) == ann_id:
            leaders = ch.get("leaders") or []
            describes = ch.get("describes") or []
            has_bar = any(str(d).startswith("BAR::") for d in describes)
            if leaders and (has_bar or role.upper() in TEXT_PRIMARY_ROLES):
                return "VALID_CHAIN", leaders[0] if leaders else None
            if leaders:
                return "WRONG_TARGET", leaders[0]
            return "BROKEN_CHAIN", None
    for ch in ctx["rejected_chains"]:
        if (ch.get("annotation_id") or ch.get("id")) == ann_id:
            leaders = ch.get("leaders") or []
            return "BROKEN_CHAIN", leaders[0] if leaders else None
    # annotation accepted without chain detail
    if ann.get("accepted"):
        return "NO_LEADER_REQUIRED", None
    return "AMBIGUOUS", None


def classify_match_status(status: str) -> str:
    if status == "MATCH":
        return "MATCHED"
    if status in ("WRONG_DIAMETER", "WRONG_QUANTITY", "WRONG_ROLE", "PARTIAL_MATCH"):
        return "PARTIALLY_MATCHED"
    if status == "MISSING":
        return "UNMATCHED"
    return "AMBIGUOUS"


def trace_gt_bar(
    gt: Dict[str, Any],
    match_row: Optional[Dict[str, Any]],
    bundle: FourthSetBundle,
    model_beam_ids: set,
) -> Dict[str, Any]:
    beam_id = gt["beam_id"]
    role = str(gt.get("bar_role") or "UNKNOWN")
    diameter = gt.get("diameter")
    quantity = float(gt.get("quantity") or 0)
    steel = float(gt.get("steel_weight") or 0)
    ctx = _beam_ctx(bundle, beam_id)
    status = (match_row or {}).get("status") or "MISSING"
    model_role = (match_row or {}).get("model_role")
    model_dia = (match_row or {}).get("model_diameter")
    model_qty = float((match_row or {}).get("model_qty") or 0)
    model_kg = float((match_row or {}).get("model_steel_kg") or 0)

    # --- Stage 1 DXF ---
    t16_lines = ctx["t16_lines"]
    graph_bars = ctx["graph_bars"]
    handle_n = 0
    sample_handle = "UNKNOWN"
    for e in t16_lines:
        if e.get("handle"):
            handle_n += 1
            if sample_handle == "UNKNOWN":
                sample_handle = str(e["handle"])
    for b in graph_bars:
        h = (b.get("attributes") or {}).get("dxf_handle")
        if h:
            handle_n += 1
            if sample_handle == "UNKNOWN":
                sample_handle = str(h)
    dxf_rec = classify_dxf(
        beam_id,
        t16_line_count=len(t16_lines),
        graph_bar_handles=handle_n,
        envelope_present=beam_id in bundle.envelope_beams,
        dxf_index=bundle.dxf_beam_index,
        text_primary=role.upper() in TEXT_PRIMARY_ROLES,
    )
    dxf_status = dxf_rec["status"]
    dxf_handle = (
        sample_handle
        if sample_handle != "UNKNOWN"
        else (dxf_rec.get("handle") or "UNKNOWN")
    )
    dxf_type = dxf_rec.get("entity_type") or "UNKNOWN"

    # --- Stage 2 Physical detection ---
    zone = _zone_bars(graph_bars, role)
    r31_zone = _zone_bars(ctx["r31_bars"], role)
    text_primary = role.upper() in TEXT_PRIMARY_ROLES
    stirrup_notes = [
        a
        for a in (ctx["accepted_anns"] + ctx["rejected_anns"])
        if "STIRR" in str(a.get("text") or "").upper()
        or "@" in str(a.get("text") or "")
        or "SPACER" in str(a.get("text") or "").upper()
    ]
    if zone or r31_zone:
        phys_status = "DETECTED"
        phys_id = (zone or r31_zone)[0].get("id") or (zone or r31_zone)[0].get(
            "bar_id"
        )
        phys_source = "AnnotationGraph" if zone else "R3.1"
    elif text_primary and (stirrup_notes or ctx["accepted_anns"]):
        phys_status = "DETECTED"
        phys_id = "TEXT_PRIMARY"
        phys_source = "Annotation/StirrupNote"
    elif t16_lines and not text_primary:
        # geometry owned but not promoted to PhysicalBar
        phys_status = "NOT_DETECTED"
        phys_id = "UNKNOWN"
        phys_source = "T16_ONLY"
    else:
        phys_status = "NOT_DETECTED"
        phys_id = "UNKNOWN"
        phys_source = "NONE"

    # --- Stage 3 Ownership ---
    if not ctx["beam_in_ownership"]:
        if beam_id in model_beam_ids:
            own_status = "UNRESOLVED"
            owner_beam = beam_id
        else:
            own_status = "DROPPED"
            owner_beam = "UNKNOWN"
    elif phys_status == "DETECTED":
        # bars listed in bar_results or annotations accepted
        if ctx["bar_results"] or ctx["accepted_anns"]:
            own_status = "CORRECT_BEAM"
            owner_beam = beam_id
        else:
            own_status = "UNRESOLVED"
            owner_beam = beam_id
    else:
        own_status = "UNRESOLVED"
        owner_beam = beam_id if ctx["beam_in_ownership"] else "UNKNOWN"

    # --- Stage 4 Annotation ---
    ann, ann_class = _annotation_match(ctx["accepted_anns"], diameter, quantity, role)
    if ann is None and ctx["rejected_anns"]:
        ann_r, ann_class_r = _annotation_match(
            ctx["rejected_anns"], diameter, quantity, role
        )
        if ann_r and ann_class_r in ("CORRECT", "AMBIGUOUS"):
            ann, ann_class = ann_r, "WRONG_ANNOTATION"

    # --- Stage 5 Leader ---
    leader_class, leader_id = _leader_status(ctx, ann, role)

    # --- Stage 6-8 via match / R13 ---
    r13_cand = _find_r13_candidate(ctx["r13_bars"], role, diameter, quantity)
    if status == "MATCH":
        role_class = "CORRECT_ROLE"
        dia_class = "CORRECT_DIAMETER"
        qty_class = "CORRECT_QUANTITY"
    elif status == "WRONG_ROLE":
        role_class = "WRONG_ROLE"
        dia_class = (
            "CORRECT_DIAMETER"
            if diameter is not None
            and model_dia is not None
            and int(diameter) == int(model_dia)
            else ("MISSING_DIAMETER" if model_dia is None else "WRONG_DIAMETER")
        )
        qty_class = (
            "CORRECT_QUANTITY"
            if _qty_close(quantity, model_qty)
            else ("MISSING_QUANTITY" if model_qty <= 0 else "UNDERCOUNT")
        )
    elif status == "WRONG_DIAMETER":
        role_class = "CORRECT_ROLE"
        dia_class = "WRONG_DIAMETER"
        qty_class = (
            "CORRECT_QUANTITY"
            if _qty_close(quantity, model_qty)
            else ("UNDERCOUNT" if model_qty < quantity else "OVERCOUNT")
        )
    elif status == "WRONG_QUANTITY":
        role_class = "CORRECT_ROLE"
        dia_class = "CORRECT_DIAMETER"
        if model_qty <= 0:
            qty_class = "MISSING_QUANTITY"
        elif model_qty < quantity:
            qty_class = "UNDERCOUNT"
        else:
            qty_class = "OVERCOUNT"
    elif status == "PARTIAL_MATCH":
        role_class = (
            "CORRECT_ROLE"
            if _role_key(role) == _role_key(str(model_role or ""))
            else "WRONG_ROLE"
        )
        dia_class = (
            "CORRECT_DIAMETER"
            if diameter is not None
            and model_dia is not None
            and int(diameter) == int(model_dia)
            else "WRONG_DIAMETER"
        )
        qty_class = (
            "CORRECT_QUANTITY"
            if _qty_close(quantity, model_qty)
            else "UNDERCOUNT"
        )
    else:  # MISSING
        if r13_cand:
            rr = _role_key(str(r13_cand.get("semantic_role") or ""))
            role_class = "CORRECT_ROLE" if rr == _role_key(role) else "WRONG_ROLE"
            rd = r13_cand.get("diameter_mm")
            dia_class = (
                "CORRECT_DIAMETER"
                if diameter is not None and rd is not None and int(rd) == int(diameter)
                else ("MISSING_DIAMETER" if rd is None else "WRONG_DIAMETER")
            )
            rq = float(r13_cand.get("quantity") or 0)
            qty_class = (
                "CORRECT_QUANTITY"
                if _qty_close(quantity, rq)
                else ("UNDERCOUNT" if rq < quantity else "OVERCOUNT")
            )
            model_role = r13_cand.get("semantic_role")
            model_dia = int(rd) if rd is not None else None
            model_qty = rq
        else:
            role_class = "MISSING_ROLE"
            dia_class = "MISSING_DIAMETER"
            qty_class = "MISSING_QUANTITY"

    # --- Stage 9 Engineering object ---
    if r13_cand:
        eng_status = "PRESENT"
        eng_id = r13_cand.get("bar_id") or r13_cand.get("source_bar_id") or "UNKNOWN"
    elif status != "MISSING":
        eng_status = "PRESENT"
        eng_id = f"VB1::{beam_id}::{model_role}"
    else:
        eng_status = "MISSING"
        eng_id = "UNKNOWN"

    # --- Stage 10 VB1 ---
    if status != "MISSING":
        vb1_status = "CONSUMED"
    elif beam_id in model_beam_ids and r13_cand:
        vb1_status = "NOT_CONSUMED"
    elif beam_id in model_beam_ids:
        vb1_status = "NOT_CONSUMED"
    else:
        vb1_status = "NOT_CONSUMED"

    # --- Stage 11 Steel ---
    if status == "MATCH" and abs(model_kg - steel) <= max(0.05, 0.02 * max(steel, 1)):
        steel_class = "CORRECT"
    elif status == "MISSING":
        steel_class = "MISSING"
    elif status == "WRONG_DIAMETER":
        steel_class = "WRONG_DIAMETER_EFFECT"
    elif status == "WRONG_QUANTITY":
        steel_class = "WRONG_QUANTITY_EFFECT"
    else:
        steel_class = "OTHER"

    # --- First fail ---
    first_fail, reason, confidence = _first_fail(
        status=status,
        dxf_status=dxf_status,
        phys_status=phys_status,
        own_status=own_status,
        ann_class=ann_class,
        leader_class=leader_class,
        role_class=role_class,
        dia_class=dia_class,
        qty_class=qty_class,
        eng_status=eng_status,
        vb1_status=vb1_status,
        steel_class=steel_class,
        text_primary=text_primary,
        role=role,
    )

    return {
        "beam_id": beam_id,
        "gt_bar_id": gt["gt_bar_id"],
        "gt_description": gt.get("original_wording")
        or gt.get("source_description")
        or f"{role} Y{diameter} x{quantity}",
        "gt_role": role,
        "gt_diameter": diameter,
        "gt_quantity": quantity,
        "gt_steel_kg": steel,
        "match_status": classify_match_status(status),
        "excel_status": status,
        "dxf_entity_found": dxf_status == "DXF_GEOMETRY_FOUND",
        "dxf_status": dxf_status,
        "dxf_entity_handle": dxf_handle,
        "dxf_entity_type": dxf_type,
        "physical_bar_detected": phys_status == "DETECTED",
        "physical_status": phys_status,
        "physical_bar_id": phys_id,
        "physical_source": phys_source,
        "owned_by_correct_beam": own_status in ("CORRECT_BEAM", "SHARED_CORRECT"),
        "ownership_status": own_status,
        "owner_beam_id": owner_beam,
        "annotation_found": ann is not None and ann_class != "NO_ANNOTATION",
        "annotation_status": ann_class,
        "annotation_id": (ann or {}).get("id") or (ann or {}).get("annotation_id") or "UNKNOWN",
        "annotation_text": (ann or {}).get("text") or "UNKNOWN",
        "leader_found": leader_id is not None and leader_id != "UNKNOWN",
        "leader_id": leader_id or "UNKNOWN",
        "leader_chain_valid": leader_class == "VALID_CHAIN",
        "leader_status": leader_class,
        "role_correct": role_class == "CORRECT_ROLE",
        "role_status": role_class,
        "model_role": model_role if model_role is not None else "UNKNOWN",
        "diameter_correct": dia_class == "CORRECT_DIAMETER",
        "diameter_status": dia_class,
        "model_diameter": model_dia if model_dia is not None else "UNKNOWN",
        "quantity_correct": qty_class == "CORRECT_QUANTITY",
        "quantity_status": qty_class,
        "model_quantity": model_qty,
        "engineering_object_found": eng_status == "PRESENT",
        "engineering_status": eng_status,
        "engineering_object_id": eng_id,
        "vb1_consumed": vb1_status == "CONSUMED",
        "vb1_status": vb1_status,
        "steel_contribution_correct": steel_class == "CORRECT",
        "steel_status": steel_class,
        "model_steel_kg": model_kg,
        "first_failure_stage": first_fail,
        "failure_reason": reason,
        "confidence": confidence,
        "is_top_reinforcement": _is_top(role),
    }


def _first_fail(
    *,
    status: str,
    dxf_status: str,
    phys_status: str,
    own_status: str,
    ann_class: str,
    leader_class: str,
    role_class: str,
    dia_class: str,
    qty_class: str,
    eng_status: str,
    vb1_status: str,
    steel_class: str,
    text_primary: bool,
    role: str,
) -> Tuple[str, str, str]:
    if status == "MATCH":
        return "NO_FAILURE", "excel_semantic_match", "HIGH"

    # Partial excel matches — interpretation first-fail
    if status == "WRONG_ROLE":
        return "ROLE_RESOLUTION", "excel_wrong_role", "HIGH"
    if status == "WRONG_DIAMETER":
        return "DIAMETER_RESOLUTION", "excel_wrong_diameter", "HIGH"
    if status == "WRONG_QUANTITY":
        return "QUANTITY_RESOLUTION", "excel_wrong_quantity", "HIGH"
    if status == "PARTIAL_MATCH":
        if role_class != "CORRECT_ROLE":
            return "ROLE_RESOLUTION", "partial_role", "MEDIUM"
        if dia_class != "CORRECT_DIAMETER":
            return "DIAMETER_RESOLUTION", "partial_diameter", "MEDIUM"
        if qty_class != "CORRECT_QUANTITY":
            return "QUANTITY_RESOLUTION", "partial_quantity", "MEDIUM"
        return "UNKNOWN", "partial_unspecified", "LOW"

    # MISSING — earliest pipeline loss
    if dxf_status == "DXF_GEOMETRY_NOT_FOUND" and not text_primary:
        return "DXF_GEOMETRY", "no_dxf_geometry_for_beam_role", "MEDIUM"

    if phys_status != "DETECTED":
        # Geometry may exist in DXF/T16 but never became a PhysicalBar
        reason = "no_physical_bar_or_text_primary_evidence"
        if dxf_status == "DXF_GEOMETRY_FOUND":
            reason = "dxf_geometry_present_but_not_detected_as_physical_bar"
        return (
            "PHYSICAL_BAR_DETECTION",
            reason,
            "HIGH" if not text_primary else "MEDIUM",
        )

    if own_status in ("WRONG_BEAM", "DROPPED"):
        return "OWNERSHIP", f"ownership_{own_status.lower()}", "HIGH"
    if own_status == "UNRESOLVED" and not text_primary:
        # detected geometry but ownership unresolved
        return "OWNERSHIP", "ownership_unresolved", "MEDIUM"

    if ann_class in ("NO_ANNOTATION", "WRONG_ANNOTATION"):
        return "ANNOTATION_ASSOCIATION", f"annotation_{ann_class.lower()}", "HIGH"

    if leader_class in ("BROKEN_CHAIN", "WRONG_TARGET"):
        return "LEADER_CHAIN", f"leader_{leader_class.lower()}", "MEDIUM"

    if role_class in ("WRONG_ROLE", "MISSING_ROLE"):
        return "ROLE_RESOLUTION", f"role_{role_class.lower()}", "HIGH"

    if dia_class in ("WRONG_DIAMETER", "MISSING_DIAMETER"):
        return "DIAMETER_RESOLUTION", f"diameter_{dia_class.lower()}", "HIGH"

    if qty_class in ("UNDERCOUNT", "OVERCOUNT", "MISSING_QUANTITY"):
        return "QUANTITY_RESOLUTION", f"quantity_{qty_class.lower()}", "HIGH"

    if eng_status != "PRESENT":
        return "ENGINEERING_OBJECT", "missing_engineering_object", "MEDIUM"

    if vb1_status != "CONSUMED":
        return "VB1_INTEGRATION", "not_consumed_by_vb1", "MEDIUM"

    if steel_class != "CORRECT":
        return "FINAL_STEEL", f"steel_{steel_class.lower()}", "LOW"

    return "UNKNOWN", f"missing_unclassified_role={role}", "LOW"


def enrich_model_registry(
    model_registry: List[Dict[str, Any]], bundle: FourthSetBundle
) -> List[Dict[str, Any]]:
    out = []
    for m in model_registry:
        bid = m["beam_id"]
        ctx = _beam_ctx(bundle, bid)
        bars = ctx["graph_bars"]
        r13 = _find_r13_candidate(
            ctx["r13_bars"], m.get("bar_role") or "", m.get("diameter"), float(m.get("quantity") or 0)
        )
        ann, _ = _annotation_match(
            ctx["accepted_anns"], m.get("diameter"), float(m.get("quantity") or 0), m.get("bar_role") or ""
        )
        row = dict(m)
        row["physical_bar_id"] = (bars[0].get("id") if bars else "UNKNOWN")
        row["entity_handle"] = (
            (bars[0].get("attributes") or {}).get("dxf_handle") if bars else "UNKNOWN"
        )
        row["entity_type"] = (
            (bars[0].get("attributes") or {}).get("entity_type") if bars else "UNKNOWN"
        )
        row["annotation_id"] = (ann or {}).get("id") or "UNKNOWN"
        row["ownership_state"] = "OWNED" if ctx["beam_in_ownership"] else "UNKNOWN"
        row["engineering_object_id"] = (r13 or {}).get("bar_id") or "UNKNOWN"
        row["confidence"] = (r13 or {}).get("classification_confidence") or "UNKNOWN"
        out.append(row)
    return out
