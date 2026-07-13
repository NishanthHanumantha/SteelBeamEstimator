"""
Extent Feature Extractor — what portion of the span the bar covers.
Observations only. No semantic meaning assigned.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from engineering_feature_model import (
    ExtentFeatures,
    EXT_FULL, EXT_LEFT_ONLY, EXT_RIGHT_ONLY, EXT_BOTH_SUPPORTS,
    EXT_PARTIAL, EXT_MIDSPAN, EXT_DEV_LENGTH, EXT_ANCHORAGE, EXT_UNKNOWN,
)

FULL_SPAN_THRESHOLD = 0.80
PARTIAL_THRESHOLD = 0.50


class ExtentFeatureExtractor:
    """Extract span-coverage observations from extent and coverage data."""

    def extract(
        self,
        bar: Dict[str, Any],
        beam_model: Dict[str, Any],
        config: Dict[str, Any],
    ) -> ExtentFeatures:
        extent = (bar.get("extent") or "").upper()
        coverage = bar.get("coverage_ratio")
        support_zone = (bar.get("support_zone") or "").upper()
        bar_label = (bar.get("bar_label") or "").upper()

        # Derive boolean flags from extent string + coverage ratio
        full_span = (
            "FULL_SPAN" in extent
            or (coverage is not None and coverage >= FULL_SPAN_THRESHOLD)
        )
        left_only = "LEFT_SUPPORT_ONLY" in extent or (
            "LEFT" in support_zone and "FULL" not in extent
        )
        right_only = "RIGHT_SUPPORT_ONLY" in extent or (
            "RIGHT" in support_zone and "FULL" not in extent
        )
        both_supports = "BOTH_SUPPORTS" in extent or "SUPPORT_BOTH" in extent or (
            left_only and right_only
        )
        midspan = "MIDSPAN_ONLY" in extent or "MIDSPAN" in extent
        partial = (
            not full_span
            and not left_only
            and not right_only
            and not midspan
            and (coverage is not None and coverage < PARTIAL_THRESHOLD)
        )
        dev_length = "DEV" in extent or "DEVELOPMENT" in extent or "Ld" in bar_label
        anchorage = "ANCHORAGE" in extent

        # Termination
        if left_only:
            term = "LEFT_END"
        elif right_only:
            term = "RIGHT_END"
        elif midspan:
            term = "MIDSPAN"
        elif dev_length:
            term = "DEVELOPMENT_END"
        elif anchorage:
            term = "ANCHORAGE_END"
        elif full_span:
            term = "BOTH_SUPPORTS"
        else:
            term = None

        # Extent type
        if full_span:
            ext_type = EXT_FULL
        elif left_only:
            ext_type = EXT_LEFT_ONLY
        elif right_only:
            ext_type = EXT_RIGHT_ONLY
        elif both_supports:
            ext_type = EXT_BOTH_SUPPORTS
        elif midspan:
            ext_type = EXT_MIDSPAN
        elif dev_length:
            ext_type = EXT_DEV_LENGTH
        elif anchorage:
            ext_type = EXT_ANCHORAGE
        elif partial:
            ext_type = EXT_PARTIAL
        else:
            ext_type = EXT_UNKNOWN

        return ExtentFeatures(
            full_span=full_span,
            left_support_only=left_only,
            right_support_only=right_only,
            both_supports=both_supports,
            partial_span=partial,
            midspan_only=midspan,
            development_length_extension=dev_length,
            anchorage_extension=anchorage,
            termination_region=term,
            coverage_ratio=coverage,
            extent_type=ext_type,
        )
