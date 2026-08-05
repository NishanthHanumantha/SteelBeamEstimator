"""
T1.7 deterministic semantic classification from annotation text.
MODEL_VERSION: 9.4.0

No OCR / ML / LLM — regex + engineering keyword rules only.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

MODEL_VERSION = "9.4.0"

_BAR_RE = re.compile(
    r"(?P<qty>\d+)\s*[-–]?\s*(?P<grade>Y|T|H)?\s*(?P<dia>\d{1,2})\b",
    re.I,
)
_STIRRUP_RE = re.compile(
    r"(?P<legs>\d)\s*L\s*[-–]?\s*(?:Y|T|H)?\s*(?P<dia>\d{1,2})\s*@\s*(?P<spc>[\d/]+)\s*(?:C/?C)?",
    re.I,
)
_SPACING_RE = re.compile(r"@\s*([\d/]+)\s*(?:C/?C)?", re.I)


def classify_annotation_text(
    text: str,
    *,
    r1_role: Optional[str] = None,
    eso: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Return semantic payload:

      semantic_type: StirrupNote | SideFaceReinforcement | DevelopmentLength |
                     SpacerBar | BarCallout | DimensionNote | Unknown
      node_type: preferred graph node type
      engineering_meaning: short label
      quantity, diameter_mm, spacing_mm, grade
      reasons[]
    """
    raw = (text or "").strip()
    upper = raw.upper().replace("%%U", "")
    reasons = []
    qty = dia = spacing = grade = None

    # Prefer ESO if present
    if eso:
        reasons.append("eso_present")
        eso_role = str(eso.get("engineering_role") or "")
        placement = str(eso.get("placement") or "")
        qty = eso.get("quantity")
        dia = eso.get("diameter")
        spacing = eso.get("spacing")
        grade = eso.get("grade")

    # Side face
    if "SIDE FACE" in upper or "SIDE.FACE" in upper or "SFR" in upper:
        m = _BAR_RE.search(upper)
        if m:
            qty = qty or int(m.group("qty"))
            dia = dia or float(m.group("dia"))
            grade = grade or (m.group("grade") or "Y")
        reasons.append("keyword_side_face")
        return {
            "semantic_type": "SideFaceReinforcement",
            "node_type": "SideFaceReinforcement",
            "engineering_meaning": "SIDE_FACE_REINFORCEMENT",
            "quantity": qty,
            "diameter_mm": dia,
            "spacing_mm": spacing,
            "grade": grade,
            "placement": "BOTH_FACE",
            "reasons": reasons,
            "raw_text": raw,
        }

    # Development length
    if re.search(r"\bLD\b", upper) or "DEVELOPMENT" in upper:
        reasons.append("keyword_ld")
        return {
            "semantic_type": "DevelopmentLength",
            "node_type": "DevelopmentLength",
            "engineering_meaning": "DEVELOPMENT_LENGTH",
            "quantity": None,
            "diameter_mm": None,
            "spacing_mm": None,
            "grade": None,
            "placement": None,
            "reasons": reasons,
            "raw_text": raw,
        }

    # Spacer
    if "SPACER" in upper:
        reasons.append("keyword_spacer")
        return {
            "semantic_type": "SpacerBar",
            "node_type": "SpacerBar",
            "engineering_meaning": "SPACER_BAR",
            "quantity": qty,
            "diameter_mm": dia,
            "spacing_mm": spacing,
            "grade": grade,
            "placement": None,
            "reasons": reasons,
            "raw_text": raw,
        }

    # Stirrup / links
    sm = _STIRRUP_RE.search(upper.replace(" ", ""))
    if not sm:
        sm = _STIRRUP_RE.search(upper)
    if sm or "@" in upper and re.search(r"\dL", upper.replace(" ", "")):
        if sm:
            qty = qty or int(sm.group("legs"))
            dia = dia or float(sm.group("dia"))
            spacing = spacing or sm.group("spc")
        else:
            m = _BAR_RE.search(upper)
            if m:
                qty = qty or int(m.group("qty"))
                dia = dia or float(m.group("dia"))
            sp = _SPACING_RE.search(upper)
            if sp:
                spacing = spacing or sp.group(1)
        reasons.append("pattern_stirrup")
        return {
            "semantic_type": "StirrupNote",
            "node_type": "StirrupNote",
            "engineering_meaning": "STIRRUP_SPACING",
            "quantity": qty,
            "diameter_mm": dia,
            "spacing_mm": spacing,
            "grade": grade or "Y",
            "placement": "STIRRUP",
            "reasons": reasons,
            "raw_text": raw,
        }

    # Longitudinal bar callout 2-Y16 / 2Y20
    m = _BAR_RE.search(upper)
    if m and "FACE" not in upper:
        qty = qty or int(m.group("qty"))
        dia = dia or float(m.group("dia"))
        grade = grade or (m.group("grade") or "Y")
        placement = None
        if eso and eso.get("placement"):
            placement = eso.get("placement")
        elif r1_role:
            if "TOP" in str(r1_role).upper():
                placement = "TOP"
            elif "BOTTOM" in str(r1_role).upper():
                placement = "BOTTOM"
        reasons.append("pattern_bar_callout")
        return {
            "semantic_type": "BarCallout",
            "node_type": "SemanticFact",
            "engineering_meaning": "LONGITUDINAL_BAR",
            "quantity": qty,
            "diameter_mm": dia,
            "spacing_mm": spacing,
            "grade": grade,
            "placement": placement,
            "reasons": reasons,
            "raw_text": raw,
        }

    # Numeric dimension-like
    if re.fullmatch(r"\d+(\.\d+)?", upper.strip()):
        reasons.append("numeric_dimension_text")
        return {
            "semantic_type": "DimensionNote",
            "node_type": "Dimension",
            "engineering_meaning": "DIMENSION_VALUE",
            "quantity": None,
            "diameter_mm": None,
            "spacing_mm": None,
            "grade": None,
            "placement": None,
            "reasons": reasons,
            "raw_text": raw,
        }

    reasons.append("unclassified")
    return {
        "semantic_type": "Unknown",
        "node_type": "SemanticFact",
        "engineering_meaning": "UNKNOWN",
        "quantity": qty,
        "diameter_mm": dia,
        "spacing_mm": spacing,
        "grade": grade,
        "placement": None,
        "reasons": reasons,
        "raw_text": raw,
    }
