"""
Development Length Table Parser — MODEL_VERSION 7.5.4

Parses all "LD FOR FY/FE-NNN" development-length tables from the General Notes DXF.

Since Phase R.2A.2, the text extractor recursively expands INSERT blocks, so tables
embedded in block definitions (e.g. FY-550 inside block A$C15514357) are discovered
alongside top-level modelspace tables.

Behaviour:
1. Dynamic header detection — all "LD FOR FY/FE-NNN" variations.
2. Extended Y-scan so every table's data rows are fully captured.
3. IS 456:2000 Clause 26.2.1 fallback only when a project steel grade has no DXF table.
4. Full table captured when all three headers are present:
      Fe415: 7 diameters x 5 grades = 35 entries  (DXF TABLE 1)
      Fe500: 7 diameters x 5 grades = 35 entries  (DXF TABLE 1)
      Fe550: 7 diameters x 5 grades = 35 entries  (DXF TABLE 1 / nested block)
   Total: 105 entries.

IS 456:2000 Clause 26.2.1 formula (fallback only):
    Ld = (phi x sigma_s) / (4 x tau_bd)
    sigma_s = fy / 1.15
    tau_bd  = IS456 Table 26 basic bond stress x 1.6 for deformed bars
"""
from __future__ import annotations
import math
import re
from typing import Dict, List, Optional, Set, Tuple

from .general_notes_text_extractor import DXFTextItem, GeneralNotesTextExtractor
from .engineering_context_model import DevelopmentLengthEntry

# ── Spatial constants (from DXF probe analysis) ───────────────────────────
_TABLE_X_MIN = 1540.0
_TABLE_X_MAX = 1680.0

# ── Pattern: any "LD FOR FY/FE-NNN" variant ───────────────────────────────
_STEEL_GRADE_PAT = re.compile(
    r"LD\s+FOR\s+(?:FY|FE)[-\s]?(\d{3,4})",
    re.I,
)

# ── Grade column detection ─────────────────────────────────────────────────
_GRADE_PATTERNS = {
    "M20": re.compile(r"M20\s*(?:GRADE)?(?:\s*&?\s*BELOW)?", re.I),
    "M25": re.compile(r"M25\s*(?:GRADE)?", re.I),
    "M30": re.compile(r"M30\s*(?:GRADE)?", re.I),
    "M35": re.compile(r"M35\s*(?:GRADE)?", re.I),
    "M40": re.compile(r"M40(?:\s*(?:GRADE|&\s*ABOVE|&\s*BELOW))?", re.I),
}

_DIAMETER_VALUES: Set[int] = {8, 10, 12, 16, 20, 25, 32, 36, 40}

# ── IS 456:2000 Table 26 — tau_bd for deformed bars (MPa) ─────────────────
_IS456_TAU_BD: Dict[str, float] = {
    "M20": 1.2 * 1.6,   # 1.92
    "M25": 1.4 * 1.6,   # 2.24
    "M30": 1.5 * 1.6,   # 2.40
    "M35": 1.7 * 1.6,   # 2.72
    "M40": 1.9 * 1.6,   # 3.04
}

_Y_CLUSTER_TOL = 3.0   # DXF units to merge items into same row


def _cluster_by_y(
    items: List[DXFTextItem], tol: float = _Y_CLUSTER_TOL
) -> List[List[DXFTextItem]]:
    if not items:
        return []
    sorted_items = sorted(items, key=lambda i: -i.y)
    clusters: List[List[DXFTextItem]] = [[sorted_items[0]]]
    for item in sorted_items[1:]:
        if abs(item.y - clusters[-1][0].y) <= tol:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def _is456_ld_mm(fy: int, diameter_mm: int, concrete_grade: str) -> int:
    """
    Compute development length in mm per IS 456:2000 Clause 26.2.1.
    sigma_s = fy / 1.15 (design tensile stress for main reinforcement)
    tau_bd  = IS456 Table 26, deformed bars
    Ld = (phi * sigma_s) / (4 * tau_bd)
    """
    sigma_s = fy / 1.15
    tau_bd  = _IS456_TAU_BD.get(concrete_grade, _IS456_TAU_BD["M20"])
    ld = (diameter_mm * sigma_s) / (4.0 * tau_bd)
    # Round up to nearest 5 mm (practical site rounding)
    return int(math.ceil(ld / 5.0) * 5)


class DevelopmentLengthParser:
    """
    Parses ALL development-length tables from the General Notes DXF.

    For steel grades found in the DXF (typically Fe415 and Fe500), values are
    read directly from the spatial table.

    For project steel grades NOT found in the DXF (e.g. Fe550 when the drawing
    only has Fe415/Fe500 tables), the IS 456:2000 Clause 26.2.1 formula is used
    and entries are tagged source="IS456_2000_COMPUTED".
    """

    def __init__(
        self,
        extractor: GeneralNotesTextExtractor,
        project_steel_grades: Optional[List[str]] = None,
    ):
        self._ext = extractor
        # Additional steel grades to compute if absent from DXF tables
        self._project_grades = project_steel_grades or []

    def parse(self) -> Tuple[List[DevelopmentLengthEntry], List[str], dict]:
        """
        Returns (entries, warnings, audit_info).
        """
        all_items  = self._ext.extract()
        table_items = self._ext.items_in_x_range(_TABLE_X_MIN, _TABLE_X_MAX, all_items)
        table_items.sort(key=lambda i: -i.y)

        # ── Step 1: locate all table headers ──────────────────────────────
        headers: List[DXFTextItem] = []
        for item in table_items:
            if _STEEL_GRADE_PAT.search(item.text):
                headers.append(item)

        dxf_grades_parsed: Set[str] = set()
        entries: List[DevelopmentLengthEntry] = []
        warnings: List[str] = []
        audit_info: dict = {
            "dxf_table_headers_found": [],
            "tables_parsed_from_dxf":  [],
            "tables_computed_is456":   [],
            "fe550_in_dxf": False,
            "fe550_computed": False,
            "root_cause": "",
        }

        if not headers:
            warnings.append("DevelopmentLengthParser: No 'LD FOR FY/FE-NNN' headers found in GN DXF.")
        else:
            audit_info["dxf_table_headers_found"] = [
                f"{h.text.strip()} @ y={h.y:.1f}" for h in headers
            ]

        # ── Step 2: parse each DXF table ──────────────────────────────────
        for i, header in enumerate(headers):
            m = _STEEL_GRADE_PAT.search(header.text)
            if not m:
                continue
            grade_num   = m.group(1)
            steel_grade = f"Fe{grade_num}"

            # Y bounds: from just above header to just above next header (or far down)
            y_top    = header.y + 5.0
            if i + 1 < len(headers):
                y_bottom = headers[i + 1].y - 1.0
            else:
                # Last table: extend far enough to capture all rows
                # Fe415 dia 8→32 spans ~28 units, give 70 unit safety margin
                y_bottom = header.y - 70.0

            block = [
                item for item in table_items
                if y_bottom <= item.y <= y_top
            ]
            parsed, w = self._parse_table_block(block, steel_grade)
            entries.extend(parsed)
            warnings.extend(w)

            if parsed:
                dxf_grades_parsed.add(steel_grade)
                audit_info["tables_parsed_from_dxf"].append(
                    f"{steel_grade}: {len(parsed)} entries"
                )

        # ── Step 3: check for Fe550 in DXF ────────────────────────────────
        fe550_in_dxf = "Fe550" in dxf_grades_parsed
        audit_info["fe550_in_dxf"] = fe550_in_dxf

        if not fe550_in_dxf:
            audit_info["root_cause"] = (
                "FY-550 development-length table not found in extracted GN DXF text. "
                "IS 456:2000 Clause 26.2.1 formula will be applied as fallback."
            )
        else:
            audit_info["root_cause"] = (
                "All three development-length tables (FY-415, FY-500, FY-550) "
                "extracted from GN DXF including nested INSERT blocks."
            )

        # ── Step 4: compute IS 456 values for any missing project grade ────
        # Always compute Fe550 if it is the project primary grade and not in DXF
        grades_to_compute = list(dxf_grades_parsed)   # start from parsed grades
        for sg in self._project_grades:
            if sg not in dxf_grades_parsed:
                grades_to_compute.append(sg)

        # Also always compute Fe550 as it is the project primary steel
        if "Fe550" not in dxf_grades_parsed and "Fe550" not in grades_to_compute:
            grades_to_compute.append("Fe550")

        # Determine which diameters and grades to compute for
        dxf_diameters = sorted({e.diameter_mm for e in entries})
        dxf_conc_grades = sorted({e.concrete_grade for e in entries})
        if not dxf_diameters:
            dxf_diameters = [8, 10, 12, 16, 20, 25, 32]
        if not dxf_conc_grades:
            dxf_conc_grades = ["M20", "M25", "M30", "M35", "M40"]

        for sg in grades_to_compute:
            if sg in dxf_grades_parsed:
                continue
            fy_m = re.search(r"(\d{3,4})", sg)
            if not fy_m:
                continue
            fy = int(fy_m.group(1))
            computed_entries: List[DevelopmentLengthEntry] = []
            for dia in dxf_diameters:
                for cg in dxf_conc_grades:
                    ld = _is456_ld_mm(fy, dia, cg)
                    computed_entries.append(DevelopmentLengthEntry(
                        steel_grade=sg,
                        diameter_mm=dia,
                        concrete_grade=cg,
                        length_mm=ld,
                        source="IS456_2000_COMPUTED",
                    ))
            entries.extend(computed_entries)
            audit_info["tables_computed_is456"].append(
                f"{sg}: {len(computed_entries)} entries (IS456 Clause 26.2.1, "
                f"fy={fy}MPa, sigma_s={fy/1.15:.1f}MPa)"
            )
            if sg == "Fe550":
                audit_info["fe550_computed"] = True
            warnings.append(
                f"DevelopmentLengthParser: {sg} table not in GN DXF — "
                f"computed {len(computed_entries)} entries using IS456:2000 Clause 26.2.1."
            )

        if not entries:
            warnings.append("DevelopmentLengthParser: No entries at all — check GN DXF structure.")

        return entries, warnings, audit_info

    # ─────────────────────────────────────────────────────────────────────
    def _parse_table_block(
        self,
        block: List[DXFTextItem],
        steel_grade: str,
    ) -> Tuple[List[DevelopmentLengthEntry], List[str]]:
        warnings: List[str] = []

        # Locate grade column header X positions
        grade_x: Dict[str, float] = {}
        for item in block:
            for grade_name, pat in _GRADE_PATTERNS.items():
                if pat.search(item.text) and grade_name not in grade_x:
                    grade_x[grade_name] = item.x

        if not grade_x:
            return [], [f"No grade column headers found for {steel_grade}"]

        col_centres = sorted(grade_x.items(), key=lambda kv: kv[1])

        # Data items: purely numeric integers (1-4 digits; dia=8 is valid single-digit)
        data_items = [
            item for item in block
            if re.fullmatch(r"\d{1,4}", item.text.strip())
        ]

        rows = _cluster_by_y(data_items)
        entries: List[DevelopmentLengthEntry] = []

        for row in rows:
            row_sorted = sorted(row, key=lambda i: i.x)
            if not row_sorted:
                continue

            # Leftmost integer = diameter
            dia_candidate = int(row_sorted[0].text.strip())
            if dia_candidate not in _DIAMETER_VALUES:
                continue

            dia_mm    = dia_candidate
            remaining = row_sorted[1:]

            for val_item in remaining:
                best_grade: Optional[str] = None
                best_dist  = float("inf")
                for grade_name, cx in col_centres:
                    dist = abs(val_item.x - cx)
                    if dist < best_dist:
                        best_dist  = dist
                        best_grade = grade_name

                if best_grade and best_dist < 20.0:
                    try:
                        length_mm = int(val_item.text.strip())
                        entries.append(DevelopmentLengthEntry(
                            steel_grade    = steel_grade,
                            diameter_mm    = dia_mm,
                            concrete_grade = best_grade,
                            length_mm      = length_mm,
                            source         = "GN_DXF_TABLE_1",
                        ))
                    except ValueError:
                        pass

        if not entries:
            warnings.append(
                f"DevelopmentLengthParser: No data rows parsed for {steel_grade}."
            )
        return entries, warnings
