"""Deterministic P2.5.4 benchmark construction from frozen P2.5.x evidence."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .candidate_loader import load_p250_evidence, load_p2523_candidates, load_quantity_intents, p250_engineering_crop
from .config import (
    MAX_LONGITUDINAL,
    MAX_MULTI_EXTRA,
    MAX_OCR_CONTROL,
    MAX_RESOLVED_STIRRUP,
    MODEL_VERSION,
    TARGET_MAX,
)

_SFR_RE = re.compile(r"S\.?F\.?R\.?|SIDE\.?\s*FACE|EACH\s*FACE|SIDEFACE", re.IGNORECASE)
_DEV_RE = re.compile(r"^Ld(\+.*)?$", re.IGNORECASE)
_OCR_RE = re.compile(r"\\X")
_STIRRUP_ORACLE_RE = re.compile(
    r"(?P<legs>\d+)\s*L?\s*-?\s*Y(?P<dia>\d+(?:\.\d+)?)\s*@"
    r"(?P<spacings>\d+(?:\s*/\s*\d+)*)\s*(?:C/?C)?",
    re.IGNORECASE,
)
_LONG_RE = re.compile(
    r"(?P<qty>\d+)\s*-?\s*Y\s*(?P<dia>\d+(?:\.\d+)?)$",
    re.IGNORECASE,
)


def _candidate_id(beam_id: str, annotation_id: str) -> str:
    return f"VC::{beam_id}::{annotation_id}"


def _stable_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _has_crop(version10_root, beam_id: str) -> bool:
    return p250_engineering_crop(version10_root, beam_id).exists()


def _sfr_note(raw: str) -> bool:
    t = (raw or "").strip()
    return bool(_SFR_RE.search(t)) and "@" not in t


def _is_dev_note(raw: str) -> bool:
    return bool(_DEV_RE.fullmatch((raw or "").strip()))


def derive_ground_truth(intent: Dict[str, Any], *, ocr: bool = False) -> Dict[str, Any]:
    """
    Evaluation-only oracle. Never sent to Claude.
    Uses annotation text parse + P2.5.1 fields when they are text-derived.
    Does not invent role/zone when P2.5.1 left them UNKNOWN.
    """
    raw = intent.get("raw_text") or ""
    status = intent.get("quantity_status") or ""
    sem = intent.get("semantic_type") or "UNKNOWN"
    role = intent.get("reinforcement_role") or "UNKNOWN"

    gt: Dict[str, Any] = {
        "available": False,
        "source": "NONE",
        "semantic_type": None,
        "role": None,
        "quantity": None,
        "diameter_mm": None,
        "legs": None,
        "spacing_mm": [],
        "spacing_pattern": None,
        "beam_association": "TARGET_BEAM",
        "zone": None,
        "normalized_notation": None,
        "fields_available": [],
        "reason": None,
    }

    if _sfr_note(raw):
        gt.update(
            {
                "available": True,
                "source": "SFR_TEXT_PATTERN",
                "semantic_type": "SIDE_FACE_REINFORCEMENT",
                "role": "SIDE_FACE",
                "beam_association": "TARGET_BEAM",
                "fields_available": ["semantic_type", "role", "beam_association"],
            }
        )
        return gt

    if _is_dev_note(raw):
        gt.update(
            {
                "available": True,
                "source": "DEVELOPMENT_NOTE_PATTERN",
                "semantic_type": "DEVELOPMENT_NOTE",
                "role": "UNKNOWN",
                "beam_association": "TARGET_BEAM",
                "fields_available": ["semantic_type", "beam_association"],
            }
        )
        return gt

    cleaned = raw.replace("\\X", "").replace("\x00", "")
    cleaned = re.sub(r"\s+", "", cleaned)
    m_st = _STIRRUP_ORACLE_RE.search(cleaned)
    if m_st or sem == "STIRRUP":
        if m_st:
            legs = int(m_st.group("legs"))
            dia = float(m_st.group("dia"))
            # Spacing tokens live after '@'; letters such as C/C are not numeric GT.
            after_at = cleaned.split("@", 1)[1] if "@" in cleaned else m_st.group("spacings")
            spacings = [int(x) for x in re.findall(r"\d+", after_at)]
            pattern = "VARIABLE" if len(spacings) > 1 else "UNIFORM"
            notation = (
                f"{legs}L-Y{int(dia) if dia == int(dia) else dia}@"
                + "/".join(str(s) for s in spacings)
                + "C/C"
            )
            gt.update(
                {
                    "available": True,
                    "source": "OCR_CLEAN_STIRRUP_ORACLE" if ocr else "STIRRUP_TEXT_ORACLE",
                    "semantic_type": "STIRRUP",
                    "role": "STIRRUP",
                    "quantity": None,
                    "diameter_mm": dia,
                    "legs": legs,
                    "spacing_mm": spacings,
                    "spacing_pattern": pattern,
                    "normalized_notation": notation,
                    "beam_association": "TARGET_BEAM",
                    "fields_available": [
                        "semantic_type",
                        "role",
                        "diameter_mm",
                        "legs",
                        "spacing_mm",
                        "beam_association",
                    ],
                }
            )
            return gt
        # P251 parsed stirrup without regex match
        if status == "SPACING_BASED" and intent.get("diameter_value_mm") is not None:
            spacings = list(intent.get("spacing_values_mm") or [])
            if intent.get("spacing_value_mm") and not spacings:
                spacings = [intent["spacing_value_mm"]]
            gt.update(
                {
                    "available": True,
                    "source": "P251_STIRRUP_PARSE",
                    "semantic_type": "STIRRUP",
                    "role": "STIRRUP",
                    "diameter_mm": float(intent["diameter_value_mm"]),
                    "legs": intent.get("leg_count"),
                    "spacing_mm": [int(x) for x in spacings],
                    "spacing_pattern": "VARIABLE" if len(spacings) > 1 else "UNIFORM",
                    "beam_association": "TARGET_BEAM",
                    "fields_available": ["semantic_type", "role", "diameter_mm", "spacing_mm", "beam_association"]
                    + (["legs"] if intent.get("leg_count") else []),
                }
            )
            return gt

    m_long = _LONG_RE.fullmatch(re.sub(r"\s+", "", raw or ""))
    if m_long or (sem == "LONGITUDINAL_BAR" and status in ("EXPLICIT", "COMPOSITE")):
        qty = intent.get("quantity_value")
        dia = intent.get("diameter_value_mm")
        if m_long and qty is None:
            qty = int(m_long.group("qty"))
        if m_long and dia is None:
            dia = float(m_long.group("dia"))
        fields = ["semantic_type", "beam_association"]
        role_out = None
        if role in ("TOP_BAR", "BOTTOM_BAR", "SUPPORT_TOP", "SUPPORT_BOTTOM", "SIDE_FACE"):
            role_out = role
            fields.append("role")
        if qty is not None:
            fields.append("quantity")
        if dia is not None:
            fields.append("diameter_mm")
        gt.update(
            {
                "available": qty is not None or dia is not None or role_out is not None,
                "source": "LONGITUDINAL_TEXT_ORACLE",
                "semantic_type": "LONGITUDINAL_BAR",
                "role": role_out or "UNKNOWN",
                "quantity": int(qty) if qty is not None else None,
                "diameter_mm": float(dia) if dia is not None else None,
                "beam_association": "TARGET_BEAM",
                "zone": None,
                "normalized_notation": raw,
                "fields_available": fields,
            }
        )
        if not gt["available"]:
            gt["reason"] = "GROUND_TRUTH_UNAVAILABLE"
        return gt

    gt["reason"] = "GROUND_TRUTH_UNAVAILABLE"
    gt["beam_association"] = "TARGET_BEAM"
    gt["fields_available"] = ["beam_association"]
    gt["available"] = True  # association only
    gt["source"] = "OWNERSHIP_ASSOCIATION_ONLY"
    return gt


def _enrich_from_intent(
    intent: Dict[str, Any],
    *,
    version10_root,
    intents_by_beam: Dict[str, List[Dict[str, Any]]],
    semantic_class: str,
    extra_classes: Optional[List[str]] = None,
    evidence_source: str,
    p2523: Optional[Dict[str, Any]] = None,
    candidate_reason: str,
    reason_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    beam_id = intent["beam_id"]
    ann_id = intent["annotation_id"]
    cid = _candidate_id(beam_id, ann_id)
    siblings = intents_by_beam.get(beam_id) or []
    evidence = load_p250_evidence(version10_root, beam_id) or {}
    target = evidence.get("target_beam") or {}
    ocr = bool(_OCR_RE.search(intent.get("raw_text") or ""))
    gt = derive_ground_truth(intent, ocr=ocr)
    links = intent.get("evidence_links") or {}
    rec = {
        "candidate_id": cid,
        "beam_id": beam_id,
        "annotation_id": ann_id,
        "raw_text": intent.get("raw_text"),
        "normalized_text": intent.get("normalized_text"),
        "quantity_status": intent.get("quantity_status"),
        "baseline_semantic_type": intent.get("semantic_type"),
        "baseline_role": intent.get("reinforcement_role"),
        "baseline_quantity": intent.get("quantity_value"),
        "baseline_diameter_mm": intent.get("diameter_value_mm"),
        "baseline_legs": intent.get("leg_count"),
        "baseline_spacing_mm": list(intent.get("spacing_values_mm") or []),
        "baseline_resolved": intent.get("quantity_status")
        in ("EXPLICIT", "SPACING_BASED", "COMPOSITE"),
        "candidate_reason": candidate_reason,
        "candidate_reason_codes": reason_codes or [],
        "semantic_class": semantic_class,
        "semantic_class_tags": sorted(set([semantic_class] + (extra_classes or []))),
        "evidence_source": evidence_source,
        "beam_depth_mm": target.get("depth_mm"),
        "beam_orientation": target.get("orientation"),
        "provenance_ids": {
            "intent_id": intent.get("intent_id"),
            "leader_id": links.get("leader_id"),
            "ownership_id": links.get("ownership_id"),
            "evidence_id": links.get("evidence_id"),
            "source_handle": links.get("source_handle"),
        },
        "sibling_annotation_count": len(siblings),
        "sibling_annotation_texts": [
            s.get("raw_text")
            for s in siblings
            if s.get("annotation_id") != ann_id
        ][:8],
        "p2523_completeness": (p2523 or {}).get("overall_completeness"),
        "ground_truth_available": bool(gt.get("available")),
        "has_p250_crop": _has_crop(version10_root, beam_id),
    }
    return rec, gt


def build_benchmark(version10_root) -> Dict[str, Any]:
    intents = load_quantity_intents(version10_root)
    p2523 = load_p2523_candidates(version10_root)
    p2523_by_id = {c["candidate_id"]: c for c in p2523}
    intent_by_key = {(i["beam_id"], i["annotation_id"]): i for i in intents}
    by_beam: Dict[str, List[Dict[str, Any]]] = {}
    for i in intents:
        by_beam.setdefault(i["beam_id"], []).append(i)

    selected: List[Dict[str, Any]] = []
    gt_map: Dict[str, Dict[str, Any]] = {}
    seen: Set[str] = set()

    def _add(rec: Dict[str, Any], gt: Dict[str, Any]) -> None:
        cid = rec["candidate_id"]
        if cid in seen:
            # merge tags
            for existing in selected:
                if existing["candidate_id"] == cid:
                    tags = set(existing.get("semantic_class_tags") or [])
                    tags.update(rec.get("semantic_class_tags") or [])
                    existing["semantic_class_tags"] = sorted(tags)
                    return
            return
        if not rec.get("has_p250_crop") and rec.get("evidence_source") != "P2523":
            return
        seen.add(cid)
        selected.append(rec)
        gt_map[cid] = gt

    # 1. DIFFICULT_VISUAL — P2523 completeness not PASS (evidence-based, not beam-id hacks)
    for c in p2523:
        if (c.get("overall_completeness") or "PASS") == "PASS":
            continue
        key = (c["beam_id"], c["annotation_id"])
        intent = intent_by_key.get(key)
        if not intent:
            continue
        rec, gt = _enrich_from_intent(
            intent,
            version10_root=version10_root,
            intents_by_beam=by_beam,
            semantic_class="DIFFICULT_VISUAL",
            extra_classes=["STIRRUP", "OCR_CONTROL"] if _OCR_RE.search(intent.get("raw_text") or "") else ["STIRRUP"],
            evidence_source="P2523",
            p2523=c,
            candidate_reason="P2523 completeness not PASS; OCR/visual difficulty",
            reason_codes=c.get("candidate_reason_codes") or ["DIFFICULT_VISUAL"],
        )
        rec["evidence_source"] = "P2523"
        rec["has_p250_crop"] = True
        _add(rec, gt)

    # 2. OCR_CONTROL — unique OCR texts from P2523 PASS set, capped
    ocr_pass = [
        c
        for c in p2523
        if (c.get("overall_completeness") or "PASS") == "PASS"
        and _OCR_RE.search(c.get("raw_text") or "")
    ]
    seen_text: Set[str] = set()
    ocr_picked = 0
    for c in ocr_pass:
        text = c.get("raw_text") or ""
        if text in seen_text:
            continue
        seen_text.add(text)
        if ocr_picked >= MAX_OCR_CONTROL:
            break
        intent = intent_by_key.get((c["beam_id"], c["annotation_id"]))
        if not intent:
            continue
        rec, gt = _enrich_from_intent(
            intent,
            version10_root=version10_root,
            intents_by_beam=by_beam,
            semantic_class="OCR_CONTROL",
            extra_classes=["STIRRUP"],
            evidence_source="P2523",
            p2523=c,
            candidate_reason="OCR-corrupted stirrup control from frozen P2.5.3 set",
            reason_codes=c.get("candidate_reason_codes") or ["OCR_CORRUPTION"],
        )
        rec["evidence_source"] = "P2523"
        rec["has_p250_crop"] = True
        _add(rec, gt)
        ocr_picked += 1

    # 3. SIDE_FACE — all SFR notes with a crop
    for intent in intents:
        if not _sfr_note(intent.get("raw_text") or ""):
            continue
        rec, gt = _enrich_from_intent(
            intent,
            version10_root=version10_root,
            intents_by_beam=by_beam,
            semantic_class="SIDE_FACE",
            extra_classes=["BEAM_ASSOCIATION"],
            evidence_source="P250",
            candidate_reason="Descriptive side-face reinforcement note",
            reason_codes=["SEMANTIC_CONTEXT_REQUIRED", "NON_QUANTITY_NOTE"],
        )
        _add(rec, gt)

    # 4. SUPPORT_TOP / known TOP_BAR role (P251 did not guess; only consume existing role)
    for intent in intents:
        if intent.get("reinforcement_role") not in ("TOP_BAR", "SUPPORT_TOP"):
            continue
        rec, gt = _enrich_from_intent(
            intent,
            version10_root=version10_root,
            intents_by_beam=by_beam,
            semantic_class="SUPPORT_TOP",
            extra_classes=["LONGITUDINAL"],
            evidence_source="P250",
            candidate_reason="Deterministic TOP_BAR / support-top role already present",
            reason_codes=["ROLE_CONTEXT_REQUIRED"],
        )
        _add(rec, gt)

    # 5. LONGITUDINAL — diverse explicit qty/dia, skip already selected
    long_pool = [
        i
        for i in intents
        if i.get("semantic_type") == "LONGITUDINAL_BAR"
        and i.get("quantity_status") in ("EXPLICIT", "COMPOSITE")
        and _has_crop(version10_root, i["beam_id"])
        and not _sfr_note(i.get("raw_text") or "")
    ]
    long_pool.sort(key=lambda x: (x.get("beam_id") or "", x.get("annotation_id") or ""))
    seen_sig: Set[Tuple[Any, Any, str]] = set()
    long_n = 0
    for intent in long_pool:
        cid = _candidate_id(intent["beam_id"], intent["annotation_id"])
        if cid in seen:
            continue
        sig = (
            intent.get("quantity_value"),
            intent.get("diameter_value_mm"),
            (intent.get("raw_text") or "").strip(),
        )
        # Prefer unique (qty, dia) first; allow a second of same sig only if under cap leftover
        if sig[:2] in {(s[0], s[1]) for s in seen_sig} and long_n >= 8:
            continue
        if long_n >= MAX_LONGITUDINAL:
            break
        seen_sig.add(sig)
        rec, gt = _enrich_from_intent(
            intent,
            version10_root=version10_root,
            intents_by_beam=by_beam,
            semantic_class="LONGITUDINAL",
            extra_classes=["BEAM_ASSOCIATION"],
            evidence_source="P250",
            candidate_reason="Explicit longitudinal bar callout — semantic/role/association test",
            reason_codes=["VISION_SEMANTIC_BENCHMARK"],
        )
        _add(rec, gt)
        long_n += 1

    # 6. Resolved STIRRUP control (not OCR) — Vision vs deterministic baseline
    stir_pool = [
        i
        for i in intents
        if i.get("semantic_type") == "STIRRUP"
        and i.get("quantity_status") == "SPACING_BASED"
        and not _OCR_RE.search(i.get("raw_text") or "")
        and _has_crop(version10_root, i["beam_id"])
    ]
    stir_pool.sort(key=lambda x: (x.get("beam_id") or "", x.get("annotation_id") or ""))
    stir_sigs: Set[str] = set()
    stir_n = 0
    for intent in stir_pool:
        cid = _candidate_id(intent["beam_id"], intent["annotation_id"])
        if cid in seen:
            continue
        sig = (intent.get("raw_text") or "").strip()
        if sig in stir_sigs:
            continue
        if stir_n >= MAX_RESOLVED_STIRRUP:
            break
        stir_sigs.add(sig)
        rec, gt = _enrich_from_intent(
            intent,
            version10_root=version10_root,
            intents_by_beam=by_beam,
            semantic_class="STIRRUP",
            extra_classes=["BEAM_ASSOCIATION"],
            evidence_source="P250",
            candidate_reason="Deterministically parsed stirrup — baseline agreement control",
            reason_codes=["VISION_NOT_REQUIRED", "BASELINE_CONTROL"],
        )
        _add(rec, gt)
        stir_n += 1

    # 7. MULTI_ANNOTATION extras from beams already in the set that have mixed types
    selected_beams = {r["beam_id"] for r in selected}
    extra_n = 0
    mixed_beams = []
    for beam_id, group in by_beam.items():
        types = {g.get("semantic_type") for g in group}
        if len(group) >= 2 and len(types) >= 2 and beam_id in selected_beams:
            mixed_beams.append(beam_id)
    mixed_beams.sort()
    for beam_id in mixed_beams:
        if extra_n >= MAX_MULTI_EXTRA:
            break
        for intent in sorted(by_beam[beam_id], key=lambda x: x.get("annotation_id") or ""):
            if extra_n >= MAX_MULTI_EXTRA:
                break
            cid = _candidate_id(intent["beam_id"], intent["annotation_id"])
            if cid in seen:
                # tag existing
                for existing in selected:
                    if existing["candidate_id"] == cid:
                        tags = set(existing.get("semantic_class_tags") or [])
                        tags.add("MULTI_ANNOTATION")
                        existing["semantic_class_tags"] = sorted(tags)
                continue
            if _is_dev_note(intent.get("raw_text") or ""):
                continue
            if not _has_crop(version10_root, beam_id):
                continue
            rec, gt = _enrich_from_intent(
                intent,
                version10_root=version10_root,
                intents_by_beam=by_beam,
                semantic_class="MULTI_ANNOTATION",
                extra_classes=["BEAM_ASSOCIATION"],
                evidence_source="P250",
                candidate_reason="Additional callout on a multi-annotation beam",
                reason_codes=["MULTI_ANNOTATION"],
            )
            _add(rec, gt)
            extra_n += 1
            break  # one extra per mixed beam

    selected.sort(key=lambda r: (r.get("beam_id") or "", r.get("annotation_id") or ""))
    if len(selected) > TARGET_MAX:
        selected = selected[:TARGET_MAX]
        keep = {r["candidate_id"] for r in selected}
        gt_map = {k: v for k, v in gt_map.items() if k in keep}

    dist: Dict[str, int] = {}
    for r in selected:
        dist[r["semantic_class"]] = dist.get(r["semantic_class"], 0) + 1
    tag_dist: Dict[str, int] = {}
    for r in selected:
        for t in r.get("semantic_class_tags") or []:
            tag_dist[t] = tag_dist.get(t, 0) + 1

    fingerprint = _stable_hash(
        [
            {
                "candidate_id": r["candidate_id"],
                "semantic_class": r["semantic_class"],
                "raw_text": r["raw_text"],
                "evidence_source": r["evidence_source"],
            }
            for r in selected
        ]
    )
    return {
        "model_version": MODEL_VERSION,
        "candidates": selected,
        "ground_truth": gt_map,
        "count": len(selected),
        "class_distribution": dist,
        "tag_distribution": tag_dist,
        "fingerprint": fingerprint,
        "p2523_frozen_count": len(p2523),
        "p251_intent_count": len(intents),
    }


__all__ = ["build_benchmark", "derive_ground_truth"]
