"""
Stirrup Candidate Finder — Phase SI.0 MODULE 1

Searches ALL annotation features for valid stirrup callouts regardless of
the semantic role assigned by L.2.

A valid candidate must contain:
  • '@'  in the callout text
  • A recognisable 2L / 4L / nL pattern OR a standard spacing value

Returns a list of StirrupCandidate objects ranked by confidence.
"""
import re
from typing import List, Dict, Any

from si0_stirrup_recovery_models import StirrupCandidate

_AT_RE  = re.compile(r"@([\d/]+)", re.IGNORECASE)
_LEGS_RE = re.compile(r"(\d+)L", re.IGNORECASE)
_DIA_RE  = re.compile(r"Y(\d+(?:\.\d+)?)", re.IGNORECASE)

# Labels that look like stirrups only because of misclassification (skip these)
_EXCLUDE_PREFIXES = ("25T", "16T", "20T", "12T", "10T")


def _confidence(callout: str) -> float:
    score = 0.0
    if "@" in callout:
        score += 0.5
    if re.search(r"\d+L", callout, re.IGNORECASE):
        score += 0.3
    if re.search(r"C/?C", callout, re.IGNORECASE):
        score += 0.1
    if "/" in callout:
        score += 0.05   # variable spacing bonus
    return min(score, 1.0)


class StirrupCandidateFinder:
    """
    Searches annotation_features.json for all valid stirrup callouts.
    Does NOT trust the semantic role — inspects every annotation text.
    """

    def find_all(
        self,
        annotation_features: List[Dict[str, Any]],
    ) -> List[StirrupCandidate]:
        """
        Returns all stirrup-format candidates from the full annotation set.
        """
        candidates: List[StirrupCandidate] = []
        for feat in annotation_features:
            callout = str(feat.get("callout") or "").strip()
            if not callout:
                continue
            # Skip if starts with a known non-stirrup prefix
            if any(callout.startswith(p) for p in _EXCLUDE_PREFIXES):
                continue

            m_at = _AT_RE.search(callout)
            if not m_at:
                continue   # no @spacing → not a candidate

            conf = _confidence(callout)
            if conf < 0.4:
                continue

            # Extract spacing list
            raw_s = m_at.group(1)
            try:
                spacings = [int(x) for x in raw_s.split("/") if x.isdigit()]
            except ValueError:
                continue
            if not spacings:
                continue

            # Extract diameter
            m_d = _DIA_RE.search(callout)
            dia = float(m_d.group(1)) if m_d else float(feat.get("diameter_mm") or 8)

            # Extract legs
            m_l = _LEGS_RE.search(callout)
            legs = int(m_l.group(1)) if m_l else 2

            candidates.append(StirrupCandidate(
                feature_id=str(feat.get("feature_id") or ""),
                bar_id=str(feat.get("bar_id") or ""),
                source_beam_id=str(feat.get("beam_id") or ""),
                callout=callout,
                diameter_mm=dia,
                legs=legs,
                spacings_mm=spacings,
                spacing_mm=float(spacings[0]),
                has_hook=bool(feat.get("has_hook_symbol")),
                confidence=conf,
                annotation_layer=str(feat.get("annotation_layer") or ""),
                has_at_sign=True,
            ))

        # Highest confidence first
        candidates.sort(key=lambda c: -c.confidence)
        return candidates
