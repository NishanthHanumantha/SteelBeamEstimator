"""Overlay promoted stirrup interpretation onto a sandbox copy of R1.3 models."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .notation_builder import merge_with_deterministic, selected_interpretation


def load_r13(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _index_models(doc: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    models = doc.get("models") or []
    return {m.get("beam_id"): m for m in models if isinstance(m, dict)}


def _match_stirrup(beam: Dict[str, Any], *, diameter_mm: Any) -> List[Dict[str, Any]]:
    """Match an existing stirrup bar. Never patch unrelated diameters when several exist."""
    bars = [b for b in (beam.get("stirrups") or []) if isinstance(b, dict)]
    if not bars:
        return []
    if diameter_mm is not None:
        try:
            d = float(diameter_mm)
            matched = [
                b
                for b in bars
                if b.get("diameter_mm") is not None and abs(float(b["diameter_mm"]) - d) < 0.6
            ]
            if matched:
                return matched
        except Exception:
            pass
    if len(bars) == 1:
        return bars
    return []


def apply_repairs(
    *,
    r13_doc: Dict[str, Any],
    audits: List[Dict[str, Any]],
    promoted: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    doc = copy.deepcopy(r13_doc)
    by_beam = _index_models(doc)
    by_cid: Dict[str, List[Dict[str, Any]]] = {}
    for rec in promoted:
        if rec.get("promotion_decision") != "CONTROLLED_RECOMPUTE":
            continue
        by_cid.setdefault(rec["candidate_id"], []).append(rec)

    provenance: List[Dict[str, Any]] = []
    for audit in audits:
        cid = audit.get("candidate_id")
        recs = by_cid.get(cid) or []
        if not recs:
            continue
        beam_id = audit.get("beam_id")
        beam = by_beam.get(beam_id)
        if beam is None:
            provenance.append({"candidate_id": cid, "beam_id": beam_id, "action": "BEAM_MISSING_IN_R13"})
            continue
        interp = selected_interpretation(recs, fallback_text=str(audit.get("annotation_text") or ""))
        det = audit.get("deterministic_result") or {}
        label, filled = merge_with_deterministic(interp, det)
        if not label:
            provenance.append({"candidate_id": cid, "beam_id": beam_id, "action": "INCOMPLETE_NOTATION"})
            continue
        dia = filled.get("diameter_mm")
        spacing = filled.get("spacing_mm") or []
        bars = _match_stirrup(beam, diameter_mm=dia)
        if not bars:
            bar = {
                "bar_id": f"P258-SHADOW-{beam_id}-STIRRUP",
                "source_bar_id": cid,
                "beam_id": beam_id,
                "semantic_role": "STIRRUP",
                "diameter_mm": float(dia) if dia is not None else 8.0,
                "quantity": None,
                "steel_grade": "Fe415",
                "bar_label": label,
                "position_zone": "TRANSVERSE_ZONE",
                "extent": "FULL_SPAN",
                "continuity": "SINGLE_SPAN",
                "support_zone": "FULL_SPAN",
                "coverage_ratio": None,
                "spacing_mm": float(spacing[0]) if spacing else None,
                "classification_evidence": "P258_VISION_FIELD_REPAIR",
                "classification_confidence": "SHADOW",
                "source_pipeline_role": "P2.5.8_SHADOW",
                "is_corrected": False,
                "spacing_pattern": "/".join(str(s) for s in spacing),
                "p258_shadow_inserted": True,
                "production_write": False,
                "piece_type": "STIRRUP",
                "p258_provenance": [
                    {
                        "field_name": r.get("field_name"),
                        "source": "VISION",
                        "original_value": r.get("original_value"),
                        "promoted_value": r.get("promoted_value"),
                        "reason": r.get("reason"),
                        "validation": r.get("validation_status"),
                        "trigger": r.get("trigger_reason"),
                        "source_model": r.get("source_model"),
                        "prompt_version": r.get("prompt_version"),
                        "timestamp": r.get("timestamp_utc"),
                        "candidate_id": cid,
                    }
                    for r in recs
                ],
            }
            beam.setdefault("stirrups", []).append(bar)
            action = "INSERTED_SHADOW_STIRRUP"
            n = 1
        else:
            n = 0
            for bar in bars:
                bar["bar_label"] = label
                if dia is not None:
                    bar["diameter_mm"] = float(dia)
                if spacing:
                    bar["spacing_mm"] = float(spacing[0])
                    bar["spacing_pattern"] = "/".join(str(s) for s in spacing)
                bar["p258_overlay"] = True
                bar["p258_source_candidate"] = cid
                bar["p258_provenance"] = [
                    {
                        "field_name": r.get("field_name"),
                        "source": "VISION",
                        "original_value": r.get("original_value"),
                        "promoted_value": r.get("promoted_value"),
                        "reason": r.get("reason"),
                        "validation": r.get("validation_status"),
                        "trigger": r.get("trigger_reason"),
                        "source_model": r.get("source_model"),
                        "prompt_version": r.get("prompt_version"),
                        "timestamp": r.get("timestamp_utc"),
                        "candidate_id": cid,
                    }
                    for r in recs
                ]
                bar["production_write"] = False
                n += 1
            action = "PATCHED_EXISTING_STIRRUP"
        provenance.append(
            {
                "candidate_id": cid,
                "beam_id": beam_id,
                "action": action,
                "bar_label": label,
                "bars_touched": n,
                "fields": [r.get("field_name") for r in recs],
                "source": "VISION",
                "production_write": False,
            }
        )
    return doc, provenance


__all__ = ["apply_repairs", "load_r13"]
