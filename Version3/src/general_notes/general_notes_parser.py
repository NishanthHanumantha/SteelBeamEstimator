"""Parse General Notes DXF/PDF into spatial text annotations."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from ezdxf import recover
from loguru import logger

_SECTION_RE = re.compile(r"^\s*(\d+)\.\d+")
_SHEET_LAYOUT_RE = re.compile(r"SH[-_]?(\d+)", re.IGNORECASE)
_DRAWING_CODE_RE = re.compile(r"(SE-\d+[\w-]*)", re.IGNORECASE)
_REVISION_RE = re.compile(r"\bR(\d+)\b", re.IGNORECASE)


@dataclass
class TextAnnotation:
    x: float
    y: float
    text: str
    layer: str
    sheet_id: Optional[str] = None
    source: str = "modelspace"


@dataclass
class GeneralNotesSheet:
    sheet_id: str
    layout_name: Optional[str] = None
    section_numbers: List[int] = field(default_factory=list)


@dataclass
class GeneralNotesDocument:
    source_path: Path
    source_format: str
    texts: List[TextAnnotation]
    layouts: List[str]
    sheets: List[GeneralNotesSheet]
    text_blob: str = ""

    def all_text_joined(self) -> str:
        if self.text_blob:
            return self.text_blob
        return "\n".join(t.text for t in self.texts)


def load_general_notes_config(config_path: Path) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "preferred_input": "DXF",
        "fallback_pdf": True,
        "extract_tables": True,
        "normalize_units": True,
        "cache_rules": True,
        "debug": True,
        "row_cluster_tolerance": 3.5,
        "column_cluster_tolerance": 12.0,
        "ld_table_x_min": 1540.0,
        "ld_table_y_min": 775.0,
        "cover_table_x_min": 1540.0,
        "cover_table_y_min": 500.0,
        "cover_table_y_max": 720.0,
    }
    if not config_path.exists():
        logger.warning("General notes config not found — using defaults: {}", config_path)
        return defaults

    data = dict(defaults)
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.lower() in ("true", "false"):
            data[key] = value.lower() == "true"
        else:
            try:
                if "." in value:
                    data[key] = float(value)
                else:
                    data[key] = int(value)
            except ValueError:
                data[key] = value
    return data


def _clean_dxf_text(text: str) -> str:
    return text.replace("%%U", "").replace("%%D", "°").strip()


def _section_major_number(text: str) -> Optional[int]:
    match = _SECTION_RE.match(text)
    if match:
        return int(match.group(1))
    first_line = text.split("\n", 1)[0]
    match = _SECTION_RE.match(first_line)
    if match:
        return int(match.group(1))
    return None


def _sheet_from_section(section: int) -> str:
    return "SH-01" if section < 9 else "SH-02"


class GeneralNotesParser:
    """Read General Notes drawings and merge sheets into one document model."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def parse(self, input_path: Optional[Path] = None) -> GeneralNotesDocument:
        dxf_path = self._resolve_dxf_path(input_path)
        if dxf_path is not None:
            return self._parse_dxf(dxf_path)

        if self._config.get("fallback_pdf", True):
            pdf_paths = self._discover_pdf_paths(input_path)
            if pdf_paths:
                return self._parse_pdf_bundle(pdf_paths)

        raise FileNotFoundError(
            "No General Notes DXF or PDF input found. "
            "Place files under data/general_notes/ or data/general_notes_pdf/."
        )

    def _resolve_dxf_path(self, input_path: Optional[Path]) -> Optional[Path]:
        if input_path and input_path.exists() and input_path.suffix.lower() == ".dxf":
            return input_path
        if input_path and input_path.is_dir():
            candidates = sorted(input_path.glob("*.dxf"))
            if candidates:
                return candidates[0]
        default_dir = Path("data/general_notes")
        if default_dir.exists():
            candidates = sorted(default_dir.glob("*.dxf"))
            if candidates:
                return candidates[0]
        return None

    def _discover_pdf_paths(self, input_path: Optional[Path]) -> List[Path]:
        if input_path and input_path.suffix.lower() == ".pdf" and input_path.exists():
            return [input_path]
        pdf_dir = Path("data/general_notes_pdf")
        if not pdf_dir.exists():
            return []
        return sorted(pdf_dir.glob("*.pdf"))

    def _parse_dxf(self, path: Path) -> GeneralNotesDocument:
        doc, _ = recover.readfile(str(path))
        layouts = [layout.name for layout in doc.layouts if layout.name != "Model"]
        sheets = self._sheets_from_layouts(layouts)
        texts: List[TextAnnotation] = []
        msp = doc.modelspace()
        for entity in msp:
            if entity.dxftype() not in ("TEXT", "MTEXT"):
                continue
            raw = (
                entity.plain_text()
                if entity.dxftype() == "MTEXT"
                else entity.dxf.text
            )
            text = _clean_dxf_text(raw)
            if not text:
                continue
            x = float(entity.dxf.insert.x)
            y = float(entity.dxf.insert.y)
            layer = entity.dxf.layer
            section = _section_major_number(text)
            sheet_id = _sheet_from_section(section) if section else None
            texts.append(
                TextAnnotation(
                    x=x,
                    y=y,
                    text=text,
                    layer=layer,
                    sheet_id=sheet_id,
                )
            )

        self._assign_sheets_from_layouts(texts, sheets)
        blob = "\n".join(t.text for t in texts)
        return GeneralNotesDocument(
            source_path=path,
            source_format="DXF",
            texts=texts,
            layouts=layouts,
            sheets=sheets,
            text_blob=blob,
        )

    def _sheets_from_layouts(self, layouts: List[str]) -> List[GeneralNotesSheet]:
        sheets: List[GeneralNotesSheet] = []
        for layout in layouts:
            match = _SHEET_LAYOUT_RE.search(layout)
            sheet_num = match.group(1) if match else str(len(sheets) + 1)
            sheets.append(
                GeneralNotesSheet(
                    sheet_id=f"SH-{sheet_num.zfill(2)}",
                    layout_name=layout,
                )
            )
        if not sheets:
            sheets = [
                GeneralNotesSheet(sheet_id="SH-01"),
                GeneralNotesSheet(sheet_id="SH-02"),
            ]
        return sheets

    def _assign_sheets_from_layouts(
        self, texts: List[TextAnnotation], sheets: List[GeneralNotesSheet]
    ) -> None:
        sheet_ids = {s.sheet_id for s in sheets}
        for ann in texts:
            if ann.sheet_id and ann.sheet_id in sheet_ids:
                continue
            if ann.y >= 850:
                ann.sheet_id = "SH-01"
            elif ann.x < 900:
                ann.sheet_id = "SH-01"
            else:
                ann.sheet_id = "SH-02"

    def _parse_pdf_bundle(self, paths: List[Path]) -> GeneralNotesDocument:
        try:
            import pdfplumber  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "PDF fallback requested but pdfplumber is not installed. "
                "Install pdfplumber or provide a DXF."
            )
            raise

        texts: List[TextAnnotation] = []
        sheets: List[GeneralNotesSheet] = []
        for index, path in enumerate(paths, start=1):
            sheet_id = f"SH-{str(index).zfill(2)}"
            sheets.append(GeneralNotesSheet(sheet_id=sheet_id, layout_name=path.name))
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ""
                    y_base = float(page_num) * 1000.0
                    for line_no, line in enumerate(page_text.splitlines()):
                        if line.strip():
                            texts.append(
                                TextAnnotation(
                                    x=100.0,
                                    y=y_base + line_no * 10.0,
                                    text=line.strip(),
                                    layer="PDF",
                                    sheet_id=sheet_id,
                                    source=path.name,
                                )
                            )

        primary = paths[0]
        blob = "\n".join(t.text for t in texts)
        return GeneralNotesDocument(
            source_path=primary,
            source_format="PDF",
            texts=texts,
            layouts=[p.name for p in paths],
            sheets=sheets,
            text_blob=blob,
        )

    def extract_project_information(self, document: GeneralNotesDocument) -> dict[str, Any]:
        blob = document.all_text_joined()
        drawing_number: Optional[str] = None
        for match in _DRAWING_CODE_RE.finditer(blob):
            drawing_number = match.group(1)
            break

        path_match = re.search(r"(SE-\d+)", document.source_path.name, re.IGNORECASE)
        if path_match:
            drawing_number = path_match.group(1)

        for layout in document.layouts:
            layout_match = re.search(r"GN-(\d+)", layout, re.IGNORECASE)
            if layout_match and drawing_number is None:
                drawing_number = f"SE-{layout_match.group(1)}"

        revision: Optional[str] = None
        rev_match = _REVISION_RE.search(document.source_path.name)
        if rev_match:
            revision = f"R{rev_match.group(1)}"

        sheet_numbers = [s.sheet_id for s in document.sheets]
        layout_names = document.layouts
        sheet_names = layout_names or sheet_numbers

        project_name = self._find_label_value(
            blob, ["PROJECT NAME", "PROJECT:", "NAME OF PROJECT"]
        )
        if not project_name:
            project_name = self._infer_project_name(blob, document.source_path.name)

        company = self._find_company(blob)
        consultant = self._find_label_value(
            blob, ["CONSULTANT", "STRUCTURAL ENGINEER", "ENGINEER"]
        ) or company

        project_info: dict[str, Any] = {
            "project_name": project_name,
            "project_code": drawing_number,
            "revision": revision,
            "drawing_number": drawing_number,
            "drawing_date": self._find_label_value(
                blob, ["DATE", "DRAWING DATE", "DATED"]
            ),
            "consultant": consultant,
            "company": company,
            "drawing_scale": self._find_label_value(
                blob, ["SCALE", "DRAWING SCALE", "N.T.S"]
            ),
            "sheet_numbers": sheet_numbers,
            "sheet_names": sheet_names,
            "layout_names": layout_names,
            "drawing_title": "GENERAL NOTES" if "GENERAL NOTES" in blob.upper() else None,
            "source_file": str(document.source_path),
            "source_format": document.source_format,
        }
        return project_info

    def _infer_project_name(self, blob: str, filename: str) -> Optional[str]:
        for line in blob.splitlines():
            upper = line.upper()
            if "PROJECT" in upper and len(line.strip()) < 120:
                if any(skip in upper for skip in ("REFERS", "DRAWING", "COMPLETION", "TEMPORARY")):
                    continue
                cleaned = re.sub(r"^\d+\.\d+\s*", "", line.strip())
                if len(cleaned) > 5 and "PROJECT" in upper:
                    return cleaned[:100]
        return None

    def _find_company(self, blob: str) -> Optional[str]:
        for line in blob.splitlines():
            upper = line.upper()
            if "QST" in upper and "TEAM" in upper:
                return "QST"
            if "COMPANY" in upper and ":" in line:
                return line.split(":", 1)[1].strip()[:80]
        qst = re.search(r"\b(QST)\b", blob, re.IGNORECASE)
        if qst:
            return qst.group(1)
        return None

    def _find_label_value(self, blob: str, labels: List[str]) -> Optional[str]:
        for line in blob.splitlines():
            upper = line.upper()
            for label in labels:
                if label in upper and ":" in line:
                    return line.split(":", 1)[1].strip() or None
        return None
