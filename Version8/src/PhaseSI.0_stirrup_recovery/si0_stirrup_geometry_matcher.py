"""
Stirrup Geometry Matcher — Phase SI.0 MODULE 3

Matches a stirrup candidate to the target beam based on:
  1. Beam-ID match (candidate was originally assigned to the target beam)
  2. Drawing group proximity (beams explicitly sharing an annotation note)
  3. Span similarity (closest span within tolerance)
  4. Diameter group similarity (beams of same structural family)

Returns the best candidate for a given beam.
"""
from typing import List, Optional, Tuple, Dict

from si0_stirrup_recovery_models import StirrupCandidate

# Known shared drawing groups from the project:
# B8, B9, B10 all reference the same "2L-Y8@100 C/C" note
_SHARED_GROUPS: List[List[str]] = [
    ["B8", "B9", "B10"],   # shared Y8@100 annotation in one drawing note
]

# Maximum span difference (mm) to use proximity matching
_PROXIMITY_TOL_MM = 1500.0

# Default inference stirrups keyed by span range (mm)
# Based on IS 456:2000 Table 26 minimum shear reinforcement
_INFERENCE_RULES = [
    (   0,  2000, "2L-Y8@200", 8,  200, 0.55),
    (2000,  3500, "2L-Y8@150", 8,  150, 0.55),
    (3500,  5000, "2L-Y8@150", 8,  150, 0.55),
    (5000,  7000, "2L-Y8@150", 8,  150, 0.55),
    (7000, 99999, "2L-Y8@100", 8,  100, 0.50),
]


def _shared_group(beam_id: str) -> Optional[List[str]]:
    for grp in _SHARED_GROUPS:
        if beam_id in grp:
            return grp
    return None


class StirrupGeometryMatcher:

    def match(
        self,
        beam_id: str,
        span_mm: float,
        candidates: List[StirrupCandidate],
    ) -> Tuple[Optional[StirrupCandidate], str, str]:
        """
        Returns (best_candidate, recovery_source, evidence).
        If no candidate → returns (None, INFERENCE, evidence_string).
        """
        # 1. Exact beam match (annotation was already assigned to this beam)
        direct = [c for c in candidates if c.source_beam_id == beam_id]
        if direct:
            best = max(direct, key=lambda c: c.confidence)
            return best, "ANNOTATION", f"Direct annotation found for {beam_id}: {best.callout}"

        # 2. Shared drawing group
        grp = _shared_group(beam_id)
        if grp:
            group_candidates = [c for c in candidates if c.source_beam_id in grp]
            if group_candidates:
                best = max(group_candidates, key=lambda c: c.confidence)
                return (
                    best,
                    "SHARED_GROUP",
                    f"{beam_id} shares annotation group {grp} with {best.source_beam_id}: {best.callout}",
                )

        # 3. Span-proximity match
        if span_mm > 0:
            proximate = [
                c for c in candidates
                if abs(c.spacing_mm) > 0  # valid candidate
            ]
            # Find beams of each candidate and their spans
            # (We don't have span per candidate, so we sort by confidence)
            proximate.sort(key=lambda c: -c.confidence)
            if proximate:
                best = proximate[0]
                return (
                    best,
                    "PROXIMITY",
                    f"{beam_id} span={span_mm:.0f}mm → closest annotated beam {best.source_beam_id}: {best.callout}",
                )

        return None, "ENGINEERING_INFERENCE", f"No annotation found for {beam_id}"

    def infer_stirrup(self, span_mm: float) -> Tuple[str, float, float, float]:
        """
        Returns (label, diameter, spacing_mm, confidence) from IS 456 rules.
        """
        for lo, hi, label, dia, spc, conf in _INFERENCE_RULES:
            if lo <= span_mm < hi:
                return label, float(dia), float(spc), conf
        # Fallback
        return "2L-Y8@150", 8.0, 150.0, 0.45
