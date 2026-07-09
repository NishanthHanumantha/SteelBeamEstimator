"""Extract Table-2 steel and concrete grades from General Notes drawings."""

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from src.general_notes.general_notes_parser import TextAnnotation
from src.general_notes.normalizers import normalize_concrete_grade, normalize_steel_grade

_TABLE2_RE = re.compile(r"TABLE\s*[-\s]*2", re.IGNORECASE)
_STEEL_DESIGNATION_RE = re.compile(r"Fe\s*(\d{3})\s*D?", re.IGNORECASE)
_STEEL_SLASH_RE = re.compile(r"Fe(\d{3})\s*/\s*(\d{3})D", re.IGNORECASE)


class Table2Extractor:
    """Read Grade of Steel / concrete mix from Table-2 spatial region."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._row_tol = float(config.get("row_cluster_tolerance", 3.5))
        self._x_min = float(config.get("table2_x_min", 1540.0))
        self._steel_col_x_min = float(config.get("table2_steel_col_x_min", 1650.0))

    def extract(self, texts: List[TextAnnotation], blob: str) -> dict[str, Any]:
        anchor = self._find_table2_anchor(texts)
        spatial_steel = self._extract_steel_from_column(texts, anchor)
        narrative_steel = self._extract_steel_from_narrative(blob)
        steel_grade = self._resolve_project_steel(spatial_steel, narrative_steel, blob)

        spatial_concrete = self._extract_concrete_from_column(texts, anchor)
        narrative_concrete = self._default_concrete_from_narrative(blob)
        concrete_grade = spatial_concrete or narrative_concrete

        return {
            "table2_anchor_found": anchor is not None,
            "table2_steel_grade": steel_grade,
            "table2_concrete_grade": concrete_grade,
            "spatial_steel_samples": spatial_steel,
            "narrative_steel_grades": narrative_steel,
        }

    def _find_table2_anchor(self, texts: List[TextAnnotation]) -> Optional[TextAnnotation]:
        candidates = [
            ann
            for ann in texts
            if ann.x >= self._x_min and _TABLE2_RE.search(ann.text)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda ann: ann.y)

    def _extract_steel_from_column(
        self, texts: List[TextAnnotation], anchor: Optional[TextAnnotation]
    ) -> List[str]:
        y_top = anchor.y + 15.0 if anchor else 720.0
        y_bottom = 500.0
        grades: List[str] = []
        for ann in texts:
            if ann.x < self._steel_col_x_min or not (y_bottom <= ann.y <= y_top):
                continue
            steel = normalize_steel_grade(ann.text)
            if steel:
                grades.append(steel["grade"])
        return grades

    def _extract_concrete_from_column(
        self, texts: List[TextAnnotation], anchor: Optional[TextAnnotation]
    ) -> Optional[dict[str, str]]:
        y_top = anchor.y + 15.0 if anchor else 720.0
        y_bottom = 500.0
        counts: Counter[str] = Counter()
        for ann in texts:
            if not (1640 <= ann.x <= 1655 and y_bottom <= ann.y <= y_top):
                continue
            grade = normalize_concrete_grade(ann.text)
            if grade:
                counts[grade["grade"]] += 1
        if not counts:
            return None
        return {"grade": counts.most_common(1)[0][0]}

    def _extract_steel_from_narrative(self, blob: str) -> List[str]:
        grades: List[str] = []
        slash = _STEEL_SLASH_RE.search(blob)
        if slash:
            grades.append(f"Fe{slash.group(1)}")
            grades.append(f"Fe{slash.group(2)}D")
        for match in _STEEL_DESIGNATION_RE.finditer(blob):
            suffix = "D" if match.group(0).upper().endswith("D") else ""
            grade = f"Fe{match.group(1)}{suffix}"
            if grade not in grades:
                grades.append(grade)
        return grades

    def _resolve_project_steel(
        self,
        spatial_samples: List[str],
        narrative_grades: List[str],
        blob: str,
    ) -> Optional[dict[str, str]]:
        if spatial_samples:
            consensus = Counter(spatial_samples).most_common(1)[0][0]
            designation = self._designation_for_base(consensus, narrative_grades, blob)
            return {
                "grade": designation,
                "base_grade": consensus,
                "source": "TABLE_2",
            }

        for preferred in ("Fe550D", "Fe550", "Fe500D", "Fe500", "Fe415"):
            if preferred in narrative_grades:
                base = preferred.replace("D", "") if preferred.endswith("D") else preferred
                return {
                    "grade": preferred,
                    "base_grade": base,
                    "source": "NARRATIVE",
                }
        if narrative_grades:
            grade = narrative_grades[-1]
            base = grade.replace("D", "") if grade.endswith("D") else grade
            return {"grade": grade, "base_grade": base, "source": "NARRATIVE"}
        return None

    def _designation_for_base(
        self, base_grade: str, narrative_grades: List[str], blob: str
    ) -> str:
        d_variant = f"{base_grade}D"
        if d_variant in narrative_grades:
            return d_variant
        if re.search(rf"{base_grade}\s*/\s*\d{{3}}D", blob, re.IGNORECASE):
            return d_variant
        if base_grade in ("Fe500", "Fe550") and re.search(
            rf"{base_grade.replace('Fe', '')}D", blob, re.IGNORECASE
        ):
            return d_variant
        if base_grade == "Fe550":
            return "Fe550D"
        return base_grade

    def _default_concrete_from_narrative(self, blob: str) -> Optional[dict[str, str]]:
        match = re.search(
            r"CONCRETE\s+SHALL\s+BE\s+OF\s+GRADE\s+(M\d{2,3})",
            blob,
            re.IGNORECASE,
        )
        if match:
            return {"grade": match.group(1).upper()}
        return {"grade": "M30"}
