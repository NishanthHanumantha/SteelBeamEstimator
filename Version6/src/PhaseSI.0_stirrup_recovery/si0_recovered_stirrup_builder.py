"""
Recovered Stirrup Builder — Phase SI.0 MODULE 6

Constructs a fully-formed stirrup bar dictionary (matching the L.2 schema)
from a BeamRecoveryResult so it can be inserted into the beam model.
"""
from typing import Dict, Any, List

from si0_stirrup_recovery_models import BeamRecoveryResult, RecoveryDecision


def build_recovered_stirrup(
    result: BeamRecoveryResult,
    original_bar: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Returns a dict that matches the L.2 bar schema and can replace
    the invalid stirrup entry in the beam model.

    If result.decision == RETAINED → returns original_bar unchanged.
    """
    if result.decision == RecoveryDecision.RETAINED:
        return original_bar

    # Compose the recovered bar
    spacings = result.recovered_spacings_mm or []
    spacing_mm = result.recovered_spacing_mm

    bar = {
        "bar_id": original_bar.get("bar_id", f"BAR::SI0::{result.beam_id}"),
        "source_bar_id": original_bar.get("source_bar_id", ""),
        "beam_id": result.beam_id,
        "semantic_role": "STIRRUP",
        "diameter_mm": result.recovered_diameter_mm,
        "quantity": result.recovered_legs,
        "steel_grade": "Y",
        "bar_label": result.recovered_label,
        "position_zone": "TRANSVERSE_ZONE",
        "extent": "FULL_SPAN",
        "continuity": "SINGLE_BEAM",
        "support_zone": None,
        "coverage_ratio": 1.0,
        "spacing_mm": spacing_mm,
        "spacing_list_mm": spacings,
        "classification_evidence": result.engineering_evidence,
        "classification_confidence": _confidence_str(result.recovery_confidence),
        "source_pipeline_role": "STIRRUP",
        "is_corrected": True,
        "is_reference_anchored": False,
        # SI.0 traceability fields
        "recovered": True,
        "recovery_source": result.source.value,
        "recovery_confidence": result.recovery_confidence,
        "recovery_engineering_note": result.engineering_evidence,
        "recovery_traceability": result.traceability,
    }
    return bar


def _confidence_str(conf: float) -> str:
    if conf >= 0.8:
        return "HIGH"
    if conf >= 0.55:
        return "MEDIUM"
    return "LOW"
