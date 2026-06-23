"""Collect reinforcement text annotations with coordinates."""

import re
from typing import Any, List, TypedDict

from ezdxf.document import Drawing

from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN
from src.regions.text_normalizer import normalize_drawing_text

EXCLUDE_TEXT_PATTERNS = [
    re.compile(r"SCALE\s*1\s*:", re.IGNORECASE),
    re.compile(r"FRAMING\s+PLAN", re.IGNORECASE),
    re.compile(r"REINFORCEMENT\s+GFC\s+DETAILS", re.IGNORECASE),
    re.compile(r"GENERAL\s+NOTES", re.IGNORECASE),
    re.compile(r"^NOTE:", re.IGNORECASE),
    re.compile(r"TYPICAL\s+STIRRUP", re.IGNORECASE),
    re.compile(r"SIDE\.FACE\.REINFORCEMENT\s+DETAILS", re.IGNORECASE),
    re.compile(r"^0?\d$"),
]

NUMERIC_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?$")
SIDE_FACE_PATTERN = re.compile(
    r"SIDE\s+FACE\s+REINF|SIDE\s+FACE\s+REINFORCEMENT|S\.?\s*F\.?\s*R",
    re.IGNORECASE,
)


class TextAnnotation(TypedDict):
    text: str
    x: float
    y: float


def simplify_reinforcement_text(text: str) -> str:
    normalized = normalize_drawing_text(text)
    normalized = re.sub(r"\\A\d+;", "", normalized)
    normalized = re.sub(r"\\P", "", normalized)
    return normalized.strip()


def normalize_dimension_text(text: str) -> str:
    stripped = text.strip()
    if not NUMERIC_PATTERN.match(stripped):
        return stripped
    try:
        value = float(stripped)
        rounded = round(value)
        if abs(value - rounded) < 0.1:
            return str(rounded)
    except ValueError:
        pass
    return stripped


def is_decimal_dimension_noise(text: str) -> bool:
    stripped = text.strip()
    if "." not in stripped or not NUMERIC_PATTERN.match(stripped):
        return False
    try:
        return float(stripped) > 100.0
    except ValueError:
        return False


def is_side_face_title_note(text: str) -> bool:
    normalized = normalize_drawing_text(text)
    if not SIDE_FACE_PATTERN.search(normalized):
        return False
    if re.search(r"\d+-Y\d+", normalized, re.IGNORECASE):
        return False
    return True


def is_global_contaminant(text: str) -> bool:
    normalized = normalize_drawing_text(text)
    if not normalized:
        return True

    if BEAM_LABEL_PATTERN.match(normalized):
        return True

    if is_side_face_title_note(normalized):
        return True

    for pattern in EXCLUDE_TEXT_PATTERNS:
        if pattern.search(normalized):
            return True

    return False


def is_contaminant_for_beam(text: str, beam_mark: str) -> bool:
    if is_global_contaminant(text):
        return True

    other_beam = re.compile(r"\bB(\d+)\b", re.IGNORECASE)
    for match in other_beam.finditer(normalize_drawing_text(text)):
        if f"B{match.group(1)}".upper() != beam_mark.upper():
            return True

    return False


def _dimension_text_from_entity(entity: Any) -> str:
    override = getattr(entity.dxf, "text", None)
    if override is not None and str(override).strip():
        return str(override).strip()

    if hasattr(entity.dxf, "actual_measurement"):
        actual = entity.dxf.actual_measurement
        if actual is not None:
            return str(actual).strip()

    if hasattr(entity, "get_measurement"):
        try:
            measurement = entity.get_measurement()
            if measurement is not None:
                return str(measurement).strip()
        except Exception:
            pass

    return ""


def _dimension_position(entity: Any) -> tuple[float, float]:
    if hasattr(entity.dxf, "text_midpoint"):
        point = entity.dxf.text_midpoint
        return float(point.x), float(point.y)
    if hasattr(entity.dxf, "defpoint"):
        point = entity.dxf.defpoint
        return float(point.x), float(point.y)
    return 0.0, 0.0


def _accept_pool_text(raw: str) -> str | None:
    if is_global_contaminant(raw):
        return None

    simplified = simplify_reinforcement_text(raw)
    if not simplified:
        return None

    normalized = normalize_dimension_text(simplified)
    if is_decimal_dimension_noise(normalized):
        return None

    return normalized


def dedupe_annotations(annotations: List[TextAnnotation]) -> List[TextAnnotation]:
    seen: set[tuple[str, float, float]] = set()
    unique: List[TextAnnotation] = []

    for item in annotations:
        key = (
            item["text"].strip().upper(),
            round(item["x"], 1),
            round(item["y"], 1),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique


def collect_annotation_pool(
    entities: List[dict],
    doc: Drawing | None = None,
) -> List[TextAnnotation]:
    """Collect all candidate reinforcement annotations for ownership assignment."""
    pool: List[TextAnnotation] = []

    for entity in entities:
        if entity.get("entity_type") not in {"TEXT", "MTEXT"}:
            continue

        try:
            x = float(entity.get("x", 0))
            y = float(entity.get("y", 0))
        except (TypeError, ValueError):
            continue

        raw = str(entity.get("clean_text", ""))
        accepted = _accept_pool_text(raw)
        if accepted is None:
            continue

        pool.append(
            TextAnnotation(text=accepted, x=round(x, 6), y=round(y, 6))
        )

    if doc is not None:
        msp = doc.modelspace()
        for entity in msp.query("DIMENSION"):
            x, y = _dimension_position(entity)
            raw = _dimension_text_from_entity(entity)
            if not raw:
                continue
            accepted = _accept_pool_text(raw)
            if accepted is None:
                continue
            pool.append(
                TextAnnotation(text=accepted, x=round(x, 6), y=round(y, 6))
            )

    return dedupe_annotations(pool)
