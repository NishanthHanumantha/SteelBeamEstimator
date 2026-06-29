"""Automatic floor detection from drawing content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ezdxf import recover
from loguru import logger

from src.framing.engineering_ids import floor_id, floor_slug_from_name
from src.utils.text_cleaner import TextCleaner


_TITLE_BLOCK_HINTS = ("title", "titile", "tb-", "border")

DRAWING_TYPE_SUFFIXES: List[re.Pattern[str]] = [
    re.compile(r"\s+BEAM\s+REINFORCEMENT\b.*$", re.IGNORECASE),
    re.compile(r"\s+FRAMING\s+PLAN\b.*$", re.IGNORECASE),
    re.compile(r"\s+GENERAL\s+NOTES\b.*$", re.IGNORECASE),
    re.compile(r"\s+GFC\s+DETAILS\b.*$", re.IGNORECASE),
    re.compile(r"\s+STRUCTURAL\s+DETAILS\b.*$", re.IGNORECASE),
    re.compile(r"\s+DETAILS\b.*$", re.IGNORECASE),
]

DRAWING_TYPE_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"GENERAL\s+NOTES", re.IGNORECASE), "GENERAL_NOTES"),
    (re.compile(r"FRAMING\s+PLAN", re.IGNORECASE), "FRAMING_PLAN"),
    (re.compile(r"REINFORCEMENT", re.IGNORECASE), "BEAM_REINFORCEMENT"),
]

DETAIL_TITLE_EXCLUSIONS: List[re.Pattern[str]] = [
    re.compile(r"SIDE\.FACE", re.IGNORECASE),
    re.compile(r"CURVED\s+BEAMS", re.IGNORECASE),
    re.compile(r"DETAILS\s+FOR", re.IGNORECASE),
]

KNOWN_FLOOR_PHRASES: List[str] = [
    "GROUND FLOOR",
    "FIRST FLOOR",
    "SECOND FLOOR",
    "THIRD FLOOR",
    "FOURTH FLOOR",
    "FIFTH FLOOR",
    "TYPICAL FLOOR",
    "TERRACE",
    "ROOF",
    "BASEMENT",
    "PODIUM",
    "MEZZANINE",
    "STILT FLOOR",
    "SERVICE FLOOR",
]

PRIORITY_TITLE_BLOCK = "TITLE_BLOCK"
PRIORITY_DRAWING_TITLE = "DRAWING_TITLE"
PRIORITY_MTEXT_HEADER = "MTEXT_HEADER"
PRIORITY_LAYOUT_NAME = "LAYOUT_NAME"
PRIORITY_FILENAME = "FILENAME"

_REVISION_RE = re.compile(r"\bR(\d+)\b", re.IGNORECASE)
_SHEET_RE = re.compile(r"(SH[-/]?\d+[\w&-]*)", re.IGNORECASE)


@dataclass
class FloorDetectionResult:
    floor_name: Optional[str]
    floor_slug: Optional[str]
    floor_id: Optional[str]
    drawing_title: str
    drawing_type: str
    revision: str
    sheet_number: str
    detection_source: str
    confidence: float
    candidates: List[dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "floor_name": self.floor_name,
            "floor_slug": self.floor_slug,
            "floor_id": self.floor_id,
            "drawing_title": self.drawing_title,
            "drawing_type": self.drawing_type,
            "revision": self.revision,
            "sheet_number": self.sheet_number,
            "detection_source": self.detection_source,
            "confidence": self.confidence,
            "candidates": self.candidates,
            "metadata": self.metadata,
        }


class FloorDetector:
    """Detect floor name and drawing metadata from DXF content."""

    def __init__(self, config: dict[str, Any]) -> None:
        di = config.get("drawing_identity", {})
        patterns = di.get("title_block_block_patterns", [])
        if isinstance(patterns, str):
            patterns = [part.strip() for part in patterns.split(",") if part.strip()]
        if not patterns:
            patterns = ["Sobha_Titile block-A1", "*title*", "*titile*"]
        self._block_patterns = patterns
        self._cleaner = TextCleaner()

    def detect_from_dxf(
        self,
        path: Path,
        expected_type: Optional[str] = None,
    ) -> FloorDetectionResult:
        path = Path(path).resolve()
        try:
            doc, _ = recover.readfile(str(path))
        except Exception as exc:
            logger.warning("Floor detection failed for {}: {}", path, exc)
            return self._fallback_from_filename(path, expected_type)

        title_block = self._extract_title_block(doc)
        drawing_title_candidates = self._collect_title_candidates(doc, expected_type)
        layout_names = [layout.name for layout in doc.layouts if layout.name != "Model"]

        best_title, title_source, title_confidence = self._select_drawing_title(
            title_block,
            drawing_title_candidates,
            layout_names,
            path,
            expected_type,
        )
        drawing_type = self._detect_drawing_type(best_title, expected_type)
        floor_name, floor_confidence = self._extract_floor_name(best_title, title_block, layout_names)

        revision = self._extract_revision(title_block, path)
        sheet_number = self._extract_sheet_number(title_block, layout_names, path)

        floor_slug = floor_slug_from_name(floor_name) if floor_name else None
        fid = floor_id(floor_slug) if floor_slug else None

        detection_source = title_source
        confidence = min(0.99, title_confidence * floor_confidence)

        return FloorDetectionResult(
            floor_name=floor_name,
            floor_slug=floor_slug,
            floor_id=fid,
            drawing_title=best_title,
            drawing_type=drawing_type,
            revision=revision,
            sheet_number=sheet_number,
            detection_source=detection_source,
            confidence=confidence,
            candidates=drawing_title_candidates[:10],
            metadata={
                "source_file": str(path),
                "layout_names": layout_names,
                "title_block_block": title_block.get("block_name"),
                "title_block_layout": title_block.get("layout_name"),
            },
        )

    def _extract_title_block(self, doc: Any) -> dict[str, Any]:
        best: Optional[dict[str, Any]] = None
        for layout in doc.layouts:
            if layout.name == "Model":
                continue
            for entity in layout:
                if entity.dxftype() != "INSERT":
                    continue
                block_name = entity.dxf.name
                if not self._is_title_block_name(block_name):
                    continue
                attribs: dict[str, str] = {}
                if entity.has_attrib:
                    for attrib in entity.attribs:
                        tag = str(attrib.dxf.tag).strip().upper()
                        text = self._cleaner.clean(str(attrib.dxf.text))
                        if text:
                            attribs[tag] = text
                candidate = {
                    "block_name": block_name,
                    "layout_name": layout.name,
                    "attributes": attribs,
                    "title": attribs.get("TITLE", ""),
                }
                if attribs.get("TITLE"):
                    return candidate
                if best is None:
                    best = candidate
        return best or {}

    def _collect_title_candidates(
        self,
        doc: Any,
        expected_type: Optional[str] = None,
    ) -> List[dict[str, Any]]:
        candidates: List[dict[str, Any]] = []
        for layout in doc.layouts:
            space = doc.layouts.get(layout.name)
            for entity in space:
                dxftype = entity.dxftype()
                if dxftype not in ("TEXT", "MTEXT", "ATTRIB"):
                    continue
                raw = entity.plain_text() if dxftype == "MTEXT" else str(entity.dxf.text)
                clean = self._cleaner.clean(raw)
                if not clean or len(clean) < 8:
                    continue
                upper = clean.upper()
                score = len(clean)
                if expected_type == "FRAMING_PLAN" and "FRAMING PLAN" in upper:
                    score += 500
                if expected_type == "BEAM_REINFORCEMENT" and "BEAM REINFORCEMENT" in upper:
                    score += 500
                if expected_type == "FRAMING_PLAN" and "FRAMING" in upper:
                    score += 200
                if expected_type == "BEAM_REINFORCEMENT" and "REINFORCEMENT" in upper:
                    score += 200
                if any(token in upper for token in ("FRAMING", "REINFORCEMENT", "GENERAL NOTES", "FLOOR", "LVL")):
                    score += 50
                if self._is_detail_title(clean):
                    score -= 400
                candidates.append(
                    {
                        "text": clean,
                        "layout": layout.name,
                        "entity_type": dxftype,
                        "score": score,
                    }
                )
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates

    def _select_drawing_title(
        self,
        title_block: dict[str, Any],
        candidates: List[dict[str, Any]],
        layout_names: List[str],
        path: Path,
        expected_type: Optional[str],
    ) -> Tuple[str, str, float]:
        tb_title = title_block.get("title", "").strip()
        if tb_title and self._looks_like_drawing_title(tb_title, expected_type):
            return tb_title, PRIORITY_TITLE_BLOCK, 0.98

        for candidate in candidates:
            text = candidate.get("text", "")
            if self._is_detail_title(text) and expected_type == "BEAM_REINFORCEMENT":
                continue
            if self._looks_like_drawing_title(text, expected_type):
                return text, PRIORITY_MTEXT_HEADER, 0.92

        for layout_name in layout_names:
            if layout_name == "Model":
                continue
            clean = self._cleaner.clean(layout_name)
            if self._looks_like_drawing_title(clean, expected_type):
                return clean, PRIORITY_LAYOUT_NAME, 0.75

        if candidates:
            return candidates[0]["text"], PRIORITY_MTEXT_HEADER, 0.60

        stem = self._cleaner.clean(path.stem.replace("_", " "))
        return stem, PRIORITY_FILENAME, 0.35

    def _is_detail_title(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in DETAIL_TITLE_EXCLUSIONS)

    def _looks_like_drawing_title(self, text: str, expected_type: Optional[str]) -> bool:
        upper = text.upper()
        if expected_type == "FRAMING_PLAN":
            return "FRAMING" in upper
        if expected_type == "BEAM_REINFORCEMENT":
            return "REINFORCEMENT" in upper and not self._is_detail_title(text)
        if expected_type == "GENERAL_NOTES":
            return "GENERAL" in upper and "NOTE" in upper
        return any(
            token in upper
            for token in ("FRAMING", "REINFORCEMENT", "GENERAL NOTES", "FLOOR", "LVL", "TERRACE", "ROOF")
        )

    def _detect_drawing_type(self, title: str, expected_type: Optional[str]) -> str:
        if expected_type:
            return expected_type
        upper = title.upper()
        for pattern, dtype in DRAWING_TYPE_PATTERNS:
            if pattern.search(upper):
                return dtype
        return "FRAMING_PLAN"

    def _extract_floor_name(
        self,
        title: str,
        title_block: dict[str, Any],
        layout_names: List[str],
    ) -> Tuple[Optional[str], float]:
        for phrase in KNOWN_FLOOR_PHRASES:
            if phrase in title.upper():
                return phrase, 0.95

        floor_name = self._strip_drawing_suffix(title)
        if floor_name and len(floor_name) >= 3:
            return floor_name.strip(), 0.90

        tb_floor = title_block.get("attributes", {}).get("FLOOR")
        if tb_floor:
            return tb_floor.strip(), 0.85

        for layout_name in layout_names:
            for phrase in KNOWN_FLOOR_PHRASES:
                if phrase in layout_name.upper():
                    return phrase, 0.70

        return None, 0.0

    def _strip_drawing_suffix(self, title: str) -> str:
        result = title.strip()
        for pattern in DRAWING_TYPE_SUFFIXES:
            result = pattern.sub("", result).strip()
        return result

    def _extract_revision(self, title_block: dict[str, Any], path: Path) -> str:
        attribs = title_block.get("attributes", {})
        raw = attribs.get("REVISION", "").strip()
        if raw:
            if raw.upper().startswith("R"):
                return raw.upper()
            return f"R{raw}"
        match = _REVISION_RE.search(path.name)
        if match:
            return f"R{match.group(1)}"
        return "UNKNOWN"

    def _extract_sheet_number(
        self,
        title_block: dict[str, Any],
        layout_names: List[str],
        path: Path,
    ) -> str:
        attribs = title_block.get("attributes", {})
        for key in ("DRAWINGNO.", "DRAWING NO", "SHEET", "SHEETNO"):
            raw = attribs.get(key.replace(" ", ""), attribs.get(key, ""))
            if raw:
                match = _SHEET_RE.search(raw)
                if match:
                    return match.group(1).replace("/", "-")
                return raw.strip()
        for layout_name in layout_names:
            match = _SHEET_RE.search(layout_name)
            if match:
                return match.group(1).replace("/", "-")
        match = _SHEET_RE.search(path.name)
        if match:
            return match.group(1).replace("/", "-")
        return "UNKNOWN"

    def _is_title_block_name(self, name: str) -> bool:
        lower = name.lower()
        if any(hint in lower for hint in _TITLE_BLOCK_HINTS):
            return True
        for pattern in self._block_patterns:
            if pattern.startswith("*") and pattern.endswith("*"):
                if pattern[1:-1].lower() in lower:
                    return True
            elif pattern.lower() in lower:
                return True
        return False

    def _fallback_from_filename(
        self,
        path: Path,
        expected_type: Optional[str],
    ) -> FloorDetectionResult:
        stem = self._cleaner.clean(path.stem.replace("_", " "))
        drawing_type = self._detect_drawing_type(stem, expected_type)
        floor_name, floor_conf = self._extract_floor_name(stem, {}, [])
        floor_slug = floor_slug_from_name(floor_name) if floor_name else None
        return FloorDetectionResult(
            floor_name=floor_name,
            floor_slug=floor_slug,
            floor_id=floor_id(floor_slug) if floor_slug else None,
            drawing_title=stem,
            drawing_type=drawing_type,
            revision="UNKNOWN",
            sheet_number="UNKNOWN",
            detection_source=PRIORITY_FILENAME,
            confidence=0.30 * floor_conf,
            metadata={"source_file": str(path)},
        )
