"""STEP 4 — Detect engineering abbreviations / symbols (dynamic discovery)."""
from __future__ import annotations

import re
from typing import Dict, List, Set

from .notation_models import NotationGroup

# Known engineering symbol families (pattern -> symbol family label)
_SYMBOL_FAMILIES = [
    (re.compile(r"^S\.F\.R\.$", re.I), "S.F.R."),
    (re.compile(r"^O\.E\.F\.$", re.I), "O.E.F."),
    (re.compile(r"^T\.O\.F\.$", re.I), "T.O.F."),
    (re.compile(r"^B\.O\.F\.$", re.I), "B.O.F."),
    (re.compile(r"^N\.F\.$", re.I), "N.F."),
    (re.compile(r"^F\.F\.$", re.I), "F.F."),
    (re.compile(r"^CONT$", re.I), "CONT"),
    (re.compile(r"^TYP\.$", re.I), "TYP."),
    (re.compile(r"^U-BAR$", re.I), "U-BAR"),
    (re.compile(r"^Ld", re.I), "Ld"),
    (re.compile(r"^Lap$", re.I), "Lap"),
    (re.compile(r"^Crank$", re.I), "Crank"),
    (re.compile(r"^Hook$", re.I), "Hook"),
    (re.compile(r"^Bend$", re.I), "Bend"),
    (re.compile(r"^Anchor$", re.I), "Anchor"),
    (re.compile(r"^Dev", re.I), "DEV"),
    (re.compile(r"^Spacer$", re.I), "Spacer"),
    (re.compile(r"^FACE$", re.I), "FACE"),
    (re.compile(r"FACE$", re.I), "FACE_PHRASE"),
    (re.compile(r"^TOP$", re.I), "TOP"),
    (re.compile(r"^BOT$", re.I), "BOT"),
    (re.compile(r"^MID$", re.I), "MID"),
    (re.compile(r"^T&B$", re.I), "T&B"),
    (re.compile(r"^\([A-Za-z][^)]*\)$"), "PAREN_MODIFIER"),
    (re.compile(r"^\(\d+[xX~]\d+\)$"), "BEAM_SECTION"),
    (re.compile(r"^\d+(?:/\d+){2,}$"), "ZONE_SPACING"),
    (re.compile(r"^\d+L-Y\d+", re.I), "MULTI_LEG_BAR"),
    (re.compile(r"Y\d+@", re.I), "STIRRUP_CALL"),
    (re.compile(r"^\d+-?Y\d+", re.I), "BAR_CALL"),
    (re.compile(r"^Y\d+$", re.I), "GRADE_DIA"),
]


class EngineeringSymbolDetector:

    def detect(self, groups: List[NotationGroup]) -> Dict[str, Dict]:
        """Return map: normalized_notation -> {is_symbol, family, ...}."""
        result = {}
        families_found: Set[str] = set()
        for g in groups:
            family = None
            for rx, label in _SYMBOL_FAMILIES:
                if rx.search(g.normalized_notation):
                    family = label
                    break
            is_symbol = family is not None and family not in (
                "BAR_CALL", "STIRRUP_CALL", "GRADE_DIA", "MULTI_LEG_BAR", "BEAM_SECTION"
            )
            # Also treat pure abbreviations as symbols
            if family in (
                "S.F.R.", "O.E.F.", "T.O.F.", "B.O.F.", "N.F.", "F.F.",
                "CONT", "TYP.", "U-BAR", "Ld", "Lap", "Crank", "Hook",
                "Bend", "Anchor", "DEV", "Spacer", "FACE", "FACE_PHRASE",
                "TOP", "BOT", "MID", "T&B", "PAREN_MODIFIER", "ZONE_SPACING",
            ):
                is_symbol = True
            if family:
                families_found.add(family)
            result[g.normalized_notation] = {
                "is_engineering_symbol": is_symbol,
                "symbol_family": family or "NONE",
                "frequency": g.frequency,
            }
        return {
            "by_notation": result,
            "families_discovered": sorted(families_found),
            "symbol_count": sum(
                1 for v in result.values() if v["is_engineering_symbol"]
            ),
        }
