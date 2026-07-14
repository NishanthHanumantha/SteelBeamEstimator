"""
Phase QA.1.1 — Module 9: Root Cause Classifier
Classify every diagnostic into exactly one primary root cause.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

from typing import Dict, List

from diagnostic_models import EngineeringDiagnostic, RootCause

# Deterministic mapping: error_type → root cause
ERROR_TO_ROOT_CAUSE: Dict[str, str] = {
    "MISSING_BEAM":             RootCause.PARSER_ERROR,
    "FALSE_POSITIVE_BEAM":      RootCause.PARSER_ERROR,
    "BEAM_NAMING_MISMATCH":     RootCause.PARSER_ERROR,
    "MISSING_BARS":             RootCause.ASSOCIATION_ERROR,
    "EXTRA_BARS":               RootCause.ASSOCIATION_ERROR,
    "GEOMETRY_ERROR":           RootCause.GEOMETRY_ERROR,
    "TOP_BOTTOM_ERROR":         RootCause.ASSOCIATION_ERROR,
    "BBS_ROW_ERROR":            RootCause.BBS_ERROR,
    "WRONG_PATTERN":            RootCause.PATTERN_ERROR,
    "WRONG_STEEL_WEIGHT":       RootCause.CALCULATION_ERROR,
    "FEATURE_ERROR":            RootCause.FEATURE_ERROR,
    "WRONG_DIAMETER":           RootCause.REFERENCE_DATA_ERROR,
    "WRONG_QUANTITY":           RootCause.ASSOCIATION_ERROR,
    # KPI gap types
    "KPI_GAP_BEAM_DETECTION":       RootCause.PARSER_ERROR,
    "KPI_GAP_BEAM_ASSIGNMENT":      RootCause.ASSOCIATION_ERROR,
    "KPI_GAP_GEOMETRY":             RootCause.GEOMETRY_ERROR,
    "KPI_GAP_FEATURE_EXTRACTION":   RootCause.FEATURE_ERROR,
    "KPI_GAP_TOP_BOTTOM":           RootCause.ASSOCIATION_ERROR,
    "KPI_GAP_DIAMETER":             RootCause.REFERENCE_DATA_ERROR,
    "KPI_GAP_QUANTITY":             RootCause.ASSOCIATION_ERROR,
    "KPI_GAP_PATTERN":              RootCause.PATTERN_ERROR,
    "KPI_GAP_BBS":                  RootCause.BBS_ERROR,
    "KPI_GAP_STEEL_WEIGHT":         RootCause.REFERENCE_DATA_ERROR,
}

# Root cause descriptions for reporting
ROOT_CAUSE_DESCRIPTION: Dict[str, str] = {
    RootCause.DRAWING_ERROR:       "Error in the source drawing (annotation, schedule, legend)",
    RootCause.PARSER_ERROR:        "Drawing Parser failed to detect or correctly extract element",
    RootCause.GEOMETRY_ERROR:      "Geometry engine produced incorrect span/depth/width",
    RootCause.ASSOCIATION_ERROR:   "Incorrect bar-to-beam association or top/bottom classification",
    RootCause.FEATURE_ERROR:       "Feature extraction produced incorrect or missing feature entries",
    RootCause.PATTERN_ERROR:       "Pattern recognition misclassified span/continuity/behaviour",
    RootCause.BBS_ERROR:           "BBS generation produced incorrect schedule entries",
    RootCause.CALCULATION_ERROR:   "Numerical calculation error in cut length or steel weight",
    RootCause.REFERENCE_DATA_ERROR:"Reference data (V5 BBS, diameter tables) mismatch",
    RootCause.UNKNOWN:             "Root cause cannot be determined from available data",
}


class RootCauseClassifier:
    """Assigns exactly one root cause to each EngineeringDiagnostic."""

    def classify(self, diagnostic: EngineeringDiagnostic) -> str:
        """Return the primary root cause for this diagnostic."""
        # Use explicit mapping first
        mapped = ERROR_TO_ROOT_CAUSE.get(diagnostic.error_type)
        if mapped:
            return mapped

        # Fallback: check partial match
        et = diagnostic.error_type.upper()
        if "BBS" in et:    return RootCause.BBS_ERROR
        if "GEOM" in et:   return RootCause.GEOMETRY_ERROR
        if "PATTERN" in et: return RootCause.PATTERN_ERROR
        if "FEATURE" in et: return RootCause.FEATURE_ERROR
        if "STEEL" in et:  return RootCause.CALCULATION_ERROR
        if "BAR" in et or "REIN" in et: return RootCause.ASSOCIATION_ERROR
        if "BEAM" in et:   return RootCause.PARSER_ERROR

        return RootCause.UNKNOWN

    def classify_all(self, diagnostics: List[EngineeringDiagnostic]) -> None:
        """In-place: assign root_cause to each diagnostic."""
        for d in diagnostics:
            d.root_cause = self.classify(d)

    @staticmethod
    def description(root_cause: str) -> str:
        return ROOT_CAUSE_DESCRIPTION.get(root_cause, "Unknown root cause")

    @staticmethod
    def distribution(diagnostics: List[EngineeringDiagnostic]) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for d in diagnostics:
            dist[d.root_cause] = dist.get(d.root_cause, 0) + 1
        return dict(sorted(dist.items(), key=lambda kv: kv[1], reverse=True))
