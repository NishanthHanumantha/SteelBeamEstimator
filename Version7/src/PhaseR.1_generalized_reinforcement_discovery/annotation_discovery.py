"""
annotation_discovery.py — Discover and classify every engineering annotation.

For each beam detail, the raw entity records (from segmenter) are parsed to
produce ReinforcementAnnotation objects with:
  - Parsed quantity, diameter, steel grade, spacing
  - Position zone (TOP / BOTTOM / UNKNOWN) based on dy from centroid
  - is_reinforcement flag

Pattern coverage:
  2-Y20         → 2 bars, Y460, 20mm
  3Y16          → 3 bars, Y460, 16mm
  2-Y16+1Y12    → two sub-bars (split into separate annotations)
  Y8@150C/C     → stirrups, Y460, 8mm, 150mm spacing
  2L-Y8@100/200 → 2-leg stirrups, 100/200mm spacing
  R8@200        → mild steel stirrup, R250, 8mm
  4Y16          → 4 bars Y16
  2 -Y12        → handles space in label
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Dict, List, Optional

from .reinforcement_models import (
    BeamDetail,
    ReinforcementAnnotation,
    GRADE_Y, GRADE_R, GRADE_T,
    ZONE_TOP, ZONE_BOTTOM, ZONE_SIDE, ZONE_UNKNOWN,
    ROLE_UNKNOWN,
)

log = logging.getLogger(__name__)

# ── Regex patterns for reinforcement callouts ─────────────────────────────────

# Primary bar group: "N-YD" or "NY D" or "N Y D" (e.g. 2-Y20, 3Y16, 4 Y20)
_RE_BAR = re.compile(
    r"(\d+)\s*[-–]?\s*([YyRrTt])\s*(\d+)",
    re.IGNORECASE,
)

# Stirrup: "YD@S" or "NYD@S C/C" (e.g. Y8@150C/C, 2L-Y8@100)
_RE_STIRRUP = re.compile(
    r"(?:(\d+)\s*[Ll][-–]\s*)?([YyRrTt])\s*(\d+)\s*@\s*(\d+(?:[/]\d+)*)",
    re.IGNORECASE,
)

# Composite: "N-YA+MYB" (e.g. 2-Y16+1Y12)
_RE_COMPOSITE = re.compile(
    r"(\d+)\s*[-–]?\s*([YyRrTt])\s*(\d+)\s*\+\s*(\d+)\s*([YyRrTt])\s*(\d+)",
    re.IGNORECASE,
)

# Non-reinforcement noise
_NOISE_PATTERNS = re.compile(
    r"RETAINING|WALL|SECTION|NOTES?|SEE|REFER|EXISTING|GRID|LEVEL|DRAWN|"
    r"CHECKED|APPROVED|DATE|SCALE|DWG|NO\.|SHEET|TITLE|%%|INVERT|INV\b",
    re.IGNORECASE,
)

_GRADE_MAP = {"Y": GRADE_Y, "y": GRADE_Y, "R": GRADE_R, "r": GRADE_R, "T": GRADE_T, "t": GRADE_T}


def _is_noise(text: str) -> bool:
    return bool(_NOISE_PATTERNS.search(text))


def _position_zone(dy: float, neutral: float = 200.0) -> str:
    if dy > neutral:
        return ZONE_TOP
    if dy < -neutral:
        return ZONE_BOTTOM
    return ZONE_UNKNOWN


def _confidence(quantity: int, diameter: float, has_match: bool) -> str:
    if has_match and quantity >= 1 and diameter >= 6:
        return "HIGH"
    if has_match:
        return "MEDIUM"
    return "LOW"


class AnnotationDiscovery:
    """Extracts ReinforcementAnnotation objects from raw entity records."""

    def __init__(self, config: dict):
        self._neutral_zone = float(
            config.get("geometry", {}).get("neutral_zone_half_height", 200.0)
        )

    # ──────────────────────────────────────────────────────────────────────────
    def discover(
        self,
        details:   List[BeamDetail],
        beam_map:  Dict[str, List[dict]],
    ) -> Dict[str, List[ReinforcementAnnotation]]:
        """Return beam_id → [ReinforcementAnnotation, ...]"""
        result: Dict[str, List[ReinforcementAnnotation]] = {}
        for detail in details:
            records = beam_map.get(detail.beam_id, [])
            annotations = []
            for rec in records:
                anns = self._parse_record(rec, detail)
                annotations.extend(anns)
            result[detail.beam_id] = annotations
        total = sum(len(v) for v in result.values())
        log.info("AnnotationDiscovery: %d annotations across %d beams", total, len(result))
        return result

    # ──────────────────────────────────────────────────────────────────────────
    def _parse_record(
        self,
        rec:    dict,
        detail: BeamDetail,
    ) -> List[ReinforcementAnnotation]:
        """Parse one raw entity record into zero or more annotations."""
        clean = rec.get("clean_text", "").strip()
        if not clean or _is_noise(clean):
            return []

        x   = rec["x"]
        y   = rec["y"]
        dy  = y - detail.centroid_y
        zone = _position_zone(dy, self._neutral_zone)

        # Try composite pattern first: "2-Y16+1Y12"
        m_comp = _RE_COMPOSITE.match(clean)
        if m_comp:
            return self._parse_composite(m_comp, clean, rec, detail, dy, zone)

        # Stirrup pattern: "Y8@150C/C"
        m_stir = _RE_STIRRUP.search(clean)
        if m_stir:
            return [self._build_stirrup(m_stir, clean, rec, detail, dy)]

        # Simple bar pattern: "2-Y20", "3Y16"
        m_bar = _RE_BAR.search(clean)
        if m_bar:
            return [self._build_bar(m_bar, clean, rec, detail, dy, zone)]

        # Beam label itself — skip
        if re.match(r"^B\d+\w*\s*[\(\[]?\d*[xX]?\d*[\)\]]?", clean, re.IGNORECASE):
            return []

        # Unrecognized — store as UNKNOWN annotation
        ann = ReinforcementAnnotation(
            annotation_id    = f"ANN-{uuid.uuid4().hex[:8]}",
            beam_id          = detail.beam_id,
            raw_text         = rec["raw_text"],
            clean_text       = clean,
            x=x, y=y,
            dy_from_centroid = round(dy, 1),
            entity_type      = rec["entity_type"],
            role             = ROLE_UNKNOWN,
            position_zone    = zone,
            is_reinforcement = False,
            confidence       = "LOW",
        )
        return [ann]

    # ──────────────────────────────────────────────────────────────────────────
    def _build_bar(self, m, clean, rec, detail, dy, zone) -> ReinforcementAnnotation:
        qty    = int(m.group(1))
        grade_char = m.group(2).upper()
        dia    = float(m.group(3))
        grade  = _GRADE_MAP.get(grade_char, GRADE_Y)
        label  = f"{qty}Y{int(dia)}" if grade_char in ("Y","y","T","t") else f"{qty}R{int(dia)}"
        return ReinforcementAnnotation(
            annotation_id    = f"ANN-{uuid.uuid4().hex[:8]}",
            beam_id          = detail.beam_id,
            raw_text         = rec["raw_text"],
            clean_text       = clean,
            x=rec["x"], y=rec["y"],
            dy_from_centroid = round(dy, 1),
            entity_type      = rec["entity_type"],
            role             = ROLE_UNKNOWN,
            position_zone    = zone,
            quantity         = qty,
            diameter_mm      = dia,
            steel_grade      = grade,
            bar_label        = label,
            confidence       = _confidence(qty, dia, True),
            is_reinforcement = True,
        )

    def _build_stirrup(self, m, clean, rec, detail, dy) -> ReinforcementAnnotation:
        legs = int(m.group(1)) if m.group(1) else 2
        grade_char = m.group(2).upper()
        dia    = float(m.group(3))
        spacing_str = m.group(4).split("/")[0]
        spacing = float(spacing_str)
        grade  = _GRADE_MAP.get(grade_char, GRADE_Y)
        label  = f"{legs}L-Y{int(dia)}@{int(spacing)}"
        return ReinforcementAnnotation(
            annotation_id    = f"ANN-{uuid.uuid4().hex[:8]}",
            beam_id          = detail.beam_id,
            raw_text         = rec["raw_text"],
            clean_text       = clean,
            x=rec["x"], y=rec["y"],
            dy_from_centroid = round(dy, 1),
            entity_type      = rec["entity_type"],
            role             = "STIRRUP",
            position_zone    = ZONE_UNKNOWN,
            quantity         = legs,
            diameter_mm      = dia,
            steel_grade      = grade,
            spacing_mm       = spacing,
            bar_label        = label,
            confidence       = "HIGH",
            is_reinforcement = True,
        )

    def _parse_composite(self, m, clean, rec, detail, dy, zone) -> List[ReinforcementAnnotation]:
        """Split 2-Y16+1Y12 into two separate annotations."""
        anns = []
        pairs = [
            (int(m.group(1)), m.group(2), float(m.group(3))),
            (int(m.group(4)), m.group(5), float(m.group(6))),
        ]
        for qty, grade_char, dia in pairs:
            grade = _GRADE_MAP.get(grade_char.upper(), GRADE_Y)
            label = f"{qty}Y{int(dia)}"
            ann = ReinforcementAnnotation(
                annotation_id    = f"ANN-{uuid.uuid4().hex[:8]}",
                beam_id          = detail.beam_id,
                raw_text         = rec["raw_text"],
                clean_text       = f"{qty}-{grade_char.upper()}{int(dia)}",
                x=rec["x"], y=rec["y"],
                dy_from_centroid = round(dy, 1),
                entity_type      = rec["entity_type"],
                role             = ROLE_UNKNOWN,
                position_zone    = zone,
                quantity         = qty,
                diameter_mm      = dia,
                steel_grade      = grade,
                bar_label        = label,
                confidence       = _confidence(qty, dia, True),
                is_reinforcement = True,
            )
            anns.append(ann)
        return anns
