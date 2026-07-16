"""STEP 5 — Assign semantic category. Discovery classification only — no interpretation."""
from __future__ import annotations

import re
from typing import Dict, List

from .notation_models import NotationGroup

# Category rules (first match wins). Categories document vocabulary, not meanings applied.
_RULES = [
    (re.compile(r"^S\.F\.R\.$", re.I), "REINFORCEMENT_ROLE"),
    (re.compile(r"^U-BAR$", re.I), "REINFORCEMENT_ROLE"),
    (re.compile(r"^Spacer$", re.I), "REINFORCEMENT_ROLE"),
    (re.compile(r"^O\.E\.F\.$", re.I), "MODIFIER"),
    (re.compile(r"^T\.O\.F\.$", re.I), "MODIFIER"),
    (re.compile(r"^B\.O\.F\.$", re.I), "MODIFIER"),
    # Parenthetical engineering modifiers e.g. (O.E.F) — not beam sizes
    (re.compile(r"^\([A-Za-z][^)]*\)$"), "MODIFIER"),
    # Beam section sizes e.g. (200X750) are geometry, not modifiers
    (re.compile(r"^\(\d+[xX~]\d+\)$"), "GEOMETRY"),
    (re.compile(r"\d+[xX~]\d+", re.I), "GEOMETRY"),
    (re.compile(r"FACE$", re.I), "POSITION"),
    (re.compile(r"^N\.F\.$|^F\.F\.$", re.I), "POSITION"),
    (re.compile(r"^TOP$|^BOT$|^MID$|^T&B$", re.I), "POSITION"),
    (re.compile(r"^Ld|^Lap$|^Dev|^Hook$|^Bend$|^Anchor$|^Crank$", re.I), "DEVELOPMENT"),
    (re.compile(r"@\d|\d+(?:/\d+){2,}", re.I), "SPACING"),
    (re.compile(r"^\d+L-|^[YyRrTt]\d+$|^\d+-?[YyRrTt]\d+", re.I), "QUANTITY"),
    (re.compile(r"^CONT$|^TYP\.$", re.I), "DRAWING"),
    (re.compile(r"SECTION|SCALE|TITLE|GROUND\s+FLOOR", re.I), "TITLE"),
    (re.compile(r"RETAINING|WALL|NOTES?|SEE\s+DETAIL", re.I), "GENERAL_NOTE"),
    (re.compile(r"^\([^)]+\)$"), "MODIFIER"),
]


class SemanticCategoryClassifier:

    def classify_all(
        self, groups: List[NotationGroup]
    ) -> Dict[str, str]:
        result = {}
        for g in groups:
            result[g.normalized_notation] = self._classify(g.normalized_notation)
        return result

    def _classify(self, notation: str) -> str:
        for rx, cat in _RULES:
            if rx.search(notation):
                return cat
        return "UNKNOWN"

    def category_distribution(
        self, categories: Dict[str, str], groups: List[NotationGroup]
    ) -> Dict[str, Dict]:
        freq_by_cat: Dict[str, int] = {}
        unique_by_cat: Dict[str, int] = {}
        group_map = {g.normalized_notation: g for g in groups}
        for notation, cat in categories.items():
            unique_by_cat[cat] = unique_by_cat.get(cat, 0) + 1
            freq_by_cat[cat] = freq_by_cat.get(cat, 0) + group_map[notation].frequency
        return {
            "unique_counts": unique_by_cat,
            "occurrence_counts": freq_by_cat,
        }
