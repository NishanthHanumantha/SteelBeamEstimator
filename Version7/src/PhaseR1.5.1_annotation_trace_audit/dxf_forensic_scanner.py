"""READ-ONLY DXF forensic text scanner."""
from __future__ import annotations
import math
import pathlib
import re
from typing import Any, Dict, List, Optional

_Y10_PATTERNS = [
    re.compile(r"Y\s*10\b", re.I),
    re.compile(r"2L[-\s]*Y\s*10", re.I),
    re.compile(r"L[-\s]*Y\s*10", re.I),
    re.compile(r"Y\s*10\s*@", re.I),
]

_STIRRUP_PATTERNS = [
    re.compile(r"Y\d+\s*@", re.I),
    re.compile(r"\d+L[-\s]*Y\d+\s*@", re.I),
    re.compile(r"R\d+\s*@", re.I),
]

_SPACER_HINTS = re.compile(r"SPACER|S\.P\.|SP\.", re.I)


class DxfForensicScanner:
    """Read-only scan of DXF text entities not captured by R.1 discovery."""

    def __init__(self, dxf_path: pathlib.Path, beam_registry: Dict[str, Any]):
        self._dxf = dxf_path
        self._registry = beam_registry

    def scan_y10(self) -> List[Dict[str, Any]]:
        return self._scan_patterns(_Y10_PATTERNS, label="Y10")

    def scan_stirrup_like(self) -> List[Dict[str, Any]]:
        return self._scan_patterns(_STIRRUP_PATTERNS, label="STIRRUP_LIKE")

    def scan_all_reinforcement_text(self) -> List[Dict[str, Any]]:
        if not self._dxf.exists():
            return []
        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._dxf))
        except Exception as exc:
            return [{"error": str(exc)}]

        results = []
        for entity in doc.modelspace():
            if entity.dxftype() not in ("TEXT", "MTEXT"):
                continue
            raw = self._raw_text(entity)
            if not raw or len(raw) < 2:
                continue
            cleaned_r1 = self._strip_like_r1(raw)
            results.append({
                "entity_type": entity.dxftype(),
                "raw_text": raw[:200],
                "r1_clean_text": cleaned_r1,
                "x": round(float(entity.dxf.insert.x), 2),
                "y": round(float(entity.dxf.insert.y), 2),
                "nearest_beam_id": self._nearest_beam(
                    float(entity.dxf.insert.x), float(entity.dxf.insert.y)
                ),
            })
        return results

    def _scan_patterns(
        self, patterns: List[re.Pattern], label: str
    ) -> List[Dict[str, Any]]:
        if not self._dxf.exists():
            return []
        try:
            import ezdxf
            doc = ezdxf.readfile(str(self._dxf))
        except Exception:
            return []

        found = []
        for entity in doc.modelspace():
            if entity.dxftype() not in ("TEXT", "MTEXT"):
                continue
            raw = self._raw_text(entity)
            if not any(p.search(raw) for p in patterns):
                continue
            cleaned_r1 = self._strip_like_r1(raw)
            found.append({
                "forensic_id": f"DXF_{label}_{len(found):04d}",
                "label": label,
                "entity_type": entity.dxftype(),
                "raw_text": raw[:200],
                "r1_clean_text": cleaned_r1,
                "r1_would_match": self._would_r1_match(cleaned_r1),
                "x": round(float(entity.dxf.insert.x), 2),
                "y": round(float(entity.dxf.insert.y), 2),
                "nearest_beam_id": self._nearest_beam(
                    float(entity.dxf.insert.x), float(entity.dxf.insert.y)
                ),
                "first_loss_module": self._first_loss_module(raw, cleaned_r1),
                "root_cause": self._root_cause_for_missed(raw, cleaned_r1),
            })
        return found

    @staticmethod
    def _raw_text(entity) -> str:
        if entity.dxftype() == "TEXT":
            return entity.dxf.text or ""
        try:
            return entity.plain_mtext()
        except Exception:
            return getattr(entity.dxf, "text", "") or ""

    @staticmethod
    def _strip_like_r1(raw: str) -> str:
        """Replicate R.1 annotation_discovery MTEXT stripping (read-only)."""
        _MTEXT_CODE = re.compile(
            r"\\[A-Za-z][^;]*;|\\\\|\\P|\\p[^;]+;|\{[^{}]*\}"
        )
        cleaned = _MTEXT_CODE.sub("", raw)
        cleaned = re.sub(r"%%[A-Za-z]", "", cleaned)
        return cleaned.strip()

    @staticmethod
    def _would_r1_match(cleaned: str) -> bool:
        if not cleaned:
            return False
        _RE_BAR = re.compile(
            r"(\d+)\s*[-–]?\s*([YyRrTt])\s*(\d+)", re.I
        )
        _RE_STIRRUP = re.compile(
            r"(?:(\d+)\s*[Ll][-–]\s*)?([YyRrTt])\s*(\d+)\s*@\s*(\d+(?:[/]\d+)*)",
            re.I,
        )
        return bool(_RE_BAR.search(cleaned) or _RE_STIRRUP.search(cleaned))

    def _nearest_beam(self, x: float, y: float) -> str:
        best_id = ""
        best_dist = float("inf")
        beams = self._registry.get("beams", {})
        for bid, beam in beams.items():
            cx = beam.get("centroid_x") or beam.get("detail_centroid_x")
            cy = beam.get("centroid_y") or beam.get("detail_centroid_y")
            if cx is None or cy is None:
                continue
            d = math.hypot(float(cx) - x, float(cy) - y)
            if d < best_dist:
                best_dist = d
                best_id = bid
        return best_id

    @staticmethod
    def _first_loss_module(raw: str, cleaned: str) -> str:
        if not cleaned:
            return "annotation_discovery._strip_mtext"
        if not DxfForensicScanner._would_r1_match(cleaned):
            return "annotation_discovery._parse_record"
        return "beam_detail_segmenter.discover"

    @staticmethod
    def _root_cause_for_missed(raw: str, cleaned: str) -> str:
        if not cleaned and "{" in raw:
            return "REGEX_NOT_MATCHED"
        if not cleaned:
            return "CLASSIFIER_FILTERED"
        if not DxfForensicScanner._would_r1_match(cleaned):
            return "REGEX_NOT_MATCHED"
        return "UNKNOWN"
