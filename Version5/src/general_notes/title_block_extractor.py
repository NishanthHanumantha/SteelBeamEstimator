"""Extract project metadata from DXF title blocks (paper space first)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ezdxf import recover
from loguru import logger

from src.general_notes.metadata_validator import (
    is_valid_company_name,
    is_valid_project_name,
    normalize_project_name,
)

_DRAWING_CODE_RE = re.compile(r"(SE[-/]?\d+[\w-]*)", re.IGNORECASE)
_REVISION_RE = re.compile(r"\bR(\d+)\b", re.IGNORECASE)
_TITLE_BLOCK_HINTS = ("title", "titile", "tb-", "border")


@dataclass
class MetadataField:
    value: Optional[str]
    confidence: float
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class TitleBlockData:
    attributes: dict[str, str] = field(default_factory=dict)
    block_name: Optional[str] = None
    layout_name: Optional[str] = None
    company_hint: Optional[str] = None
    source: str = "TITLE_BLOCK"


def _wrap(
    value: Optional[str],
    confidence: float,
    source: str,
) -> dict[str, Any]:
    return MetadataField(value=value, confidence=confidence, source=source).to_dict()


def _is_title_block_name(name: str, patterns: list[str]) -> bool:
    lower = name.lower()
    if any(hint in lower for hint in _TITLE_BLOCK_HINTS):
        return True
    for pattern in patterns:
        if pattern.startswith("*") and pattern.endswith("*"):
            if pattern[1:-1].lower() in lower:
                return True
        elif pattern.lower() in lower:
            return True
    return False


def _company_from_block(block_name: str, static_text: str) -> Optional[str]:
    if "sobha" in block_name.lower() or "sobha" in static_text.lower():
        return "Sobha"
    match = re.search(r"@([a-z0-9-]+)\.com", static_text, re.IGNORECASE)
    if match:
        domain = match.group(1).split(".")[0]
        return domain.replace("-", " ").title()
    return None


class TitleBlockExtractor:
    """Title-block-first metadata extraction from General Notes DXF."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        patterns = config.get("title_block_block_patterns", [])
        if isinstance(patterns, str):
            patterns = [part.strip() for part in patterns.split(",") if part.strip()]
        if not patterns:
            patterns = ["Sobha_Titile block-A1", "*title*", "*titile*"]
        self._block_patterns = patterns

    def extract_from_dxf(self, path: Path) -> Optional[TitleBlockData]:
        try:
            doc, _ = recover.readfile(str(path))
        except Exception as exc:
            logger.warning("Title block read failed for {}: {}", path, exc)
            return None

        best: Optional[TitleBlockData] = None
        for layout in doc.layouts:
            if layout.name == "Model":
                continue
            for entity in layout:
                if entity.dxftype() != "INSERT":
                    continue
                block_name = entity.dxf.name
                if not _is_title_block_name(block_name, self._block_patterns):
                    continue
                attribs: dict[str, str] = {}
                if entity.has_attrib:
                    for attrib in entity.attribs:
                        tag = str(attrib.dxf.tag).strip().upper()
                        text = str(attrib.dxf.text).strip()
                        if text:
                            attribs[tag] = text

                static_text = self._block_static_text(doc, block_name)
                company_hint = _company_from_block(block_name, static_text)
                candidate = TitleBlockData(
                    attributes=attribs,
                    block_name=block_name,
                    layout_name=layout.name,
                    company_hint=company_hint,
                    source="TITLE_BLOCK",
                )
                if attribs.get("PROJECTNAME"):
                    return candidate
                if best is None:
                    best = candidate
        return best

    def _block_static_text(self, doc: Any, block_name: str) -> str:
        if block_name not in doc.blocks:
            return ""
        parts: list[str] = []
        for entity in doc.blocks[block_name]:
            if entity.dxftype() == "MTEXT":
                parts.append(entity.plain_text())
            elif entity.dxftype() == "TEXT":
                parts.append(entity.dxf.text)
        return "\n".join(parts)

    def build_project_information(
        self,
        document: Any,
        title_block: Optional[TitleBlockData] = None,
    ) -> dict[str, Any]:
        if title_block is None and document.source_format == "DXF":
            title_block = self.extract_from_dxf(document.source_path)

        drawing_number = self._drawing_number(document, title_block)
        revision = self._revision(document, title_block)
        project_name = self._project_name(document, title_block)
        company = self._company(title_block)
        consultant = self._consultant(title_block, company)
        drawing_date = self._field_from_title_block(
            title_block, ("DATE",), fallback_labels=("DATE", "DRAWING DATE")
        )
        drawing_scale = self._field_from_title_block(
            title_block, ("SCALE",), fallback_labels=("SCALE", "DRAWING SCALE")
        )
        drawing_title = self._field_from_title_block(
            title_block, ("TITLE",), fallback_labels=("TITLE",)
        )

        sheet_numbers = [s.sheet_id for s in document.sheets]
        layout_names = document.layouts
        sheet_names = layout_names or sheet_numbers

        project_code = None
        project_code_source = "KEYWORD_FALLBACK"
        project_code_confidence = 0.0
        if title_block and title_block.attributes.get("PROJECTCODE"):
            project_code = title_block.attributes["PROJECTCODE"]
            project_code_source = "TITLE_BLOCK"
            project_code_confidence = 0.98

        return {
            "project_name": project_name,
            "project_code": _wrap(project_code, project_code_confidence, project_code_source),
            "revision": _wrap(revision, 0.98 if title_block and title_block.attributes.get("REVISION") else 0.85, "TITLE_BLOCK" if title_block and title_block.attributes.get("REVISION") else "LAYOUT"),
            "drawing_number": _wrap(drawing_number, 0.98 if title_block and title_block.attributes.get("DRAWINGNO.") else 0.85, "TITLE_BLOCK" if title_block and title_block.attributes.get("DRAWINGNO.") else "LAYOUT"),
            "drawing_date": drawing_date,
            "consultant": consultant,
            "company": company,
            "drawing_scale": drawing_scale,
            "drawing_title": drawing_title,
            "sheet_numbers": sheet_numbers,
            "sheet_names": sheet_names,
            "layout_names": layout_names,
            "source_file": str(document.source_path),
            "source_format": document.source_format,
            "title_block_block": title_block.block_name if title_block else None,
            "title_block_layout": title_block.layout_name if title_block else None,
        }

    def _drawing_number(
        self, document: Any, title_block: Optional[TitleBlockData]
    ) -> Optional[str]:
        if title_block:
            raw = title_block.attributes.get("DRAWINGNO.")
            if raw:
                match = _DRAWING_CODE_RE.search(raw.replace("/", "-"))
                if match:
                    return match.group(1).replace("/", "-")
                return raw.strip()

        path_match = re.search(r"(SE-\d+)", document.source_path.name, re.IGNORECASE)
        if path_match:
            return path_match.group(1)

        for layout in document.layouts:
            layout_match = re.search(r"GN-(\d+)", layout, re.IGNORECASE)
            if layout_match:
                return f"SE-{layout_match.group(1)}"

        blob = document.all_text_joined()
        for match in _DRAWING_CODE_RE.finditer(blob):
            return match.group(1).replace("/", "-")
        return None

    def _revision(
        self, document: Any, title_block: Optional[TitleBlockData]
    ) -> Optional[str]:
        if title_block and title_block.attributes.get("REVISION"):
            rev = title_block.attributes["REVISION"].strip()
            if rev.upper().startswith("R"):
                return rev.upper()
            return f"R{rev}"

        rev_match = _REVISION_RE.search(document.source_path.name)
        if rev_match:
            return f"R{rev_match.group(1)}"
        return None

    def _project_name(
        self, document: Any, title_block: Optional[TitleBlockData]
    ) -> dict[str, Any]:
        if title_block and title_block.attributes.get("PROJECTNAME"):
            raw = title_block.attributes["PROJECTNAME"]
            if is_valid_project_name(raw):
                normalized = normalize_project_name(raw, title_block.company_hint)
                return _wrap(normalized, 0.98, "TITLE_BLOCK")

        for layout in document.layouts:
            if "GALERA" in layout.upper() or "CLUB" in layout.upper():
                name = normalize_project_name("GALERA CLUB HOUSE", "Sobha")
                return _wrap(name, 0.85, "LAYOUT")

        header_name = self._header_project_name(document)
        if header_name and is_valid_project_name(header_name):
            return _wrap(header_name, 0.70, "HEADER")

        fallback = self._keyword_project_name(document)
        if fallback and is_valid_project_name(fallback):
            return _wrap(fallback, 0.40, "KEYWORD_FALLBACK")

        return _wrap(None, 0.0, "KEYWORD_FALLBACK")

    def _company(self, title_block: Optional[TitleBlockData]) -> dict[str, Any]:
        if title_block and title_block.company_hint:
            if is_valid_company_name(title_block.company_hint):
                return _wrap(title_block.company_hint, 0.98, "TITLE_BLOCK")
        return _wrap(None, 0.0, "KEYWORD_FALLBACK")

    def _consultant(
        self, title_block: Optional[TitleBlockData], company: dict[str, Any]
    ) -> dict[str, Any]:
        if title_block:
            hod = title_block.attributes.get("HOD")
            if hod and is_valid_company_name(hod):
                return _wrap(hod, 0.90, "TITLE_BLOCK")
            designed = title_block.attributes.get("DESINED")
            if designed and is_valid_company_name(designed):
                return _wrap(designed, 0.85, "TITLE_BLOCK")
        if company.get("value"):
            return _wrap(company["value"], 0.80, "TITLE_BLOCK")
        return _wrap(None, 0.0, "KEYWORD_FALLBACK")

    def _field_from_title_block(
        self,
        title_block: Optional[TitleBlockData],
        tags: tuple[str, ...],
        fallback_labels: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if title_block:
            for tag in tags:
                value = title_block.attributes.get(tag)
                if value:
                    return _wrap(value, 0.98, "TITLE_BLOCK")
        return _wrap(None, 0.0, "KEYWORD_FALLBACK")

    def _header_project_name(self, document: Any) -> Optional[str]:
        if document.source_format != "DXF":
            return None
        try:
            doc, _ = recover.readfile(str(document.source_path))
            value = doc.header.get("$PROJECTNAME", "")
            if value and str(value).strip():
                return str(value).strip()
        except Exception:
            return None
        return None

    def _keyword_project_name(self, document: Any) -> Optional[str]:
        blob = document.all_text_joined()
        for line in blob.splitlines():
            upper = line.upper()
            if "PROJECT NAME" in upper and ":" in line:
                candidate = line.split(":", 1)[1].strip()
                if is_valid_project_name(candidate):
                    return candidate
        return None
