"""
T1.3 — Fuse GEOMETRY_STIRRUP evidence into R.2.1D enriched facts.
Additive only; residual-scoped. MODEL_VERSION: 9.3.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

MODEL_VERSION = "9.3.0"

EVIDENCE_TYPE = "GEOMETRY_STIRRUP"
FLAG_SYNTHESIZED = "SYNTHESIZED_GEOMETRY"
FLAG_GEOMETRY_ONLY = "GEOMETRY_ONLY"
FLAG_CONFLICT = "GEOMETRY_TEXT_CONFLICT"
FLAG_AGREE = "GEOMETRY_TEXT_AGREE"


def fuse_geometry_into_facts(
    enriched_by_beam: Dict[str, List[Any]],
    geometry_by_beam: Dict[str, Dict[str, Any]],
    residual_beam_ids: Set[str],
    *,
    models: Any,
    fusion_cfg: Optional[Dict[str, Any]] = None,
    target_missing_ids: Optional[Set[str]] = None,
    default_diameter_mm: float = 8.0,
) -> Dict[str, Any]:
    """
    Mutates enriched_by_beam in place (HypothesisEnrichedFact objects).

    *models* must expose: HypothesisEnrichedFact, IntentHypothesis,
    ObservableEvidence, INTENT_UNKNOWN, ZONE_UNKNOWN.
    """
    fusion_cfg = fusion_cfg or {}
    synth_conf = str(fusion_cfg.get("synthesized_confidence") or "WARN")
    agree_conf = str(fusion_cfg.get("agree_confidence") or "HIGH")
    do_synth = bool(fusion_cfg.get("synthesize_geometry_only", True))
    target_missing_ids = target_missing_ids or set()

    HypothesisEnrichedFact = models.HypothesisEnrichedFact
    IntentHypothesis = models.IntentHypothesis
    ObservableEvidence = models.ObservableEvidence
    INTENT_UNKNOWN = models.INTENT_UNKNOWN
    ZONE_UNKNOWN = models.ZONE_UNKNOWN

    summary = {
        "beams_considered": 0,
        "agree": 0,
        "text_only": 0,
        "geometry_only_synthesized": 0,
        "conflict": 0,
        "skipped_non_residual": 0,
        "actions": [],
    }

    for beam_id, facts in list(enriched_by_beam.items()):
        if beam_id not in residual_beam_ids:
            summary["skipped_non_residual"] += 1
            continue
        summary["beams_considered"] += 1
        geo = geometry_by_beam.get(beam_id) or {}
        geo_ok = bool(geo.get("accepted"))
        agreement = geo.get("text_spacing_agreement")

        stirrup_facts = [
            f for f in facts
            if str(getattr(f, "role", "")).upper() == "STIRRUP"
        ]

        geo_conf = float(geo.get("confidence") or 0.0)
        # Weak geometry must not override / conflict with text (R2 false-positive guard)
        geo_strong = geo_ok and geo_conf >= 0.55

        if stirrup_facts and geo_strong and agreement is True:
            for f in stirrup_facts:
                _annotate_fact(f, FLAG_AGREE, geo, agree_conf)
            summary["agree"] += 1
            summary["actions"].append({"beam_id": beam_id, "case": "AGREE"})

        elif stirrup_facts and geo_strong and agreement is False:
            for f in stirrup_facts:
                _annotate_fact(f, FLAG_CONFLICT, geo, "WARN")
                notes = list(getattr(f, "engineering_notes", []) or [])
                notes.append(
                    f"CONFLICT text_spacing={geo.get('text_spacing_mm')} "
                    f"measured_pitch={geo.get('median_pitch_mm')}"
                )
                f.engineering_notes = notes
            summary["conflict"] += 1
            summary["actions"].append({"beam_id": beam_id, "case": "CONFLICT"})

        elif stirrup_facts and (not geo_ok or not geo_strong or agreement == "no_text_to_compare"):
            summary["text_only"] += 1
            summary["actions"].append({
                "beam_id": beam_id,
                "case": "TEXT_ONLY",
                "geo_ok": geo_ok,
                "geo_conf": geo_conf,
            })

        elif (
            do_synth
            and not stirrup_facts
            and geo_strong
            and beam_id in target_missing_ids
        ):
            pitch = geo.get("median_pitch_mm")
            if pitch is None:
                mp = geo.get("measured_pitch_mm") or []
                pitch = mp[0] if mp else None
            if pitch is None:
                summary["actions"].append(
                    {"beam_id": beam_id, "case": "SYNTH_SKIP_NO_PITCH"}
                )
                continue
            dia = float(default_diameter_mm)
            ann_id = f"T1-GEO-{beam_id}"
            evidence = ObservableEvidence(
                annotation_id=ann_id,
                beam_id=beam_id,
                original_text="",
                clean_text=f"SYNTH:2L-Y{int(dia)}@{int(round(float(pitch)))}C/C",
                role_source=EVIDENCE_TYPE,
                placement_source=EVIDENCE_TYPE,
                quantity=2,
                diameter=dia,
                grade="Y460",
                spacing=float(pitch),
                modifiers=[],
                semantic_flags=[FLAG_SYNTHESIZED, FLAG_GEOMETRY_ONLY, EVIDENCE_TYPE],
                annotation_zone=ZONE_UNKNOWN,
                r1_original_role="STIRRUP",
                confidence_source=EVIDENCE_TYPE,
                notes=[
                    "GEOMETRY_ONLY synthesis from measured tick pitch",
                    f"detection_method={geo.get('detection_method')}",
                    f"confidence={geo.get('confidence')}",
                ],
            )
            hyps = [
                IntentHypothesis(
                    intent="STIRRUP",
                    priority=1,
                    reason=(
                        "GEOMETRY_STIRRUP synthesis — no text; "
                        "Track 2 VLM confirmation pending"
                    ),
                )
            ]
            fact = HypothesisEnrichedFact(
                annotation_id=ann_id,
                beam_id=beam_id,
                clean_text=evidence.clean_text,
                quantity=2,
                diameter=dia,
                grade="Y460",
                spacing=float(pitch),
                role="STIRRUP",
                placement="UNKNOWN",
                intent=INTENT_UNKNOWN,
                modifiers=[],
                semantic_flags=[FLAG_SYNTHESIZED, FLAG_GEOMETRY_ONLY, EVIDENCE_TYPE],
                confidence=synth_conf,
                source=EVIDENCE_TYPE,
                engineering_notes=[
                    "SYNTHESIZED_GEOMETRY",
                    "GEOMETRY_ONLY",
                    f"measured_pitch_mm={pitch}",
                ],
                geometry_required=False,
                intent_deferred_reason="geometry_only_synthesis",
                observable_evidence=evidence,
                intent_hypotheses=hyps,
                intent_candidates=["STIRRUP"],
            )
            enriched_by_beam.setdefault(beam_id, []).append(fact)
            summary["geometry_only_synthesized"] += 1
            summary["actions"].append(
                {"beam_id": beam_id, "case": "GEOMETRY_ONLY_SYNTH"}
            )

    return summary


def _annotate_fact(fact: Any, flag: str, geo: Dict[str, Any], conf: str) -> None:
    flags = list(getattr(fact, "semantic_flags", []) or [])
    if flag not in flags:
        flags.append(flag)
    if EVIDENCE_TYPE not in flags:
        flags.append(EVIDENCE_TYPE)
    fact.semantic_flags = flags
    notes = list(getattr(fact, "engineering_notes", []) or [])
    notes.append(
        f"{EVIDENCE_TYPE}:{flag}:method={geo.get('detection_method')}"
        f":pitch={geo.get('median_pitch_mm')}:conf={geo.get('confidence')}"
    )
    fact.engineering_notes = notes
    if flag == FLAG_AGREE and conf:
        fact.confidence = conf
