"""
Lap Rule Parser.

Extracts lap splice rules from GN DXF:
  - "LENGTH OF LAPS FOR LAPPED SPLICES SHALL BE AS PER TABLE-1"
  - "NO SPLICES SHALL HAVE LAP LENGTH LESS THAN 300mm"
  - "WHERE DETAILS ... NOT SHOWN ON DRAWINGS, LAP SPLICES SHALL..."
"""
from __future__ import annotations
import re
from typing import List, Tuple

from .general_notes_text_extractor import GeneralNotesTextExtractor
from .engineering_context_model import LapRule

_TABLE_REF_PAT = re.compile(r"TABLE[-\s]*1|lap.*table", re.I)
_MIN_LAP_PAT   = re.compile(r"(?:lap|splice).*?less\s+than\s+(\d+)\s*mm", re.I | re.DOTALL)
_LAPPED_SPLICE = re.compile(r"lapped?\s+splice", re.I)
_LAP_MM_PAT    = re.compile(r"\b(\d{3,4})\s*mm\b")


class LapRuleParser:
    def __init__(self, extractor: GeneralNotesTextExtractor):
        self._ext = extractor

    def parse(self) -> Tuple[List[LapRule], List[str]]:
        warnings: List[str] = []
        rules: List[LapRule] = []
        seen_types: set = set()

        for item in self._ext.extract():
            text = item.text

            # Table reference
            if _TABLE_REF_PAT.search(text) and "TABLE_REF" not in seen_types:
                seen_types.add("TABLE_REF")
                rules.append(LapRule(
                    rule_type="TABLE_REF",
                    table_ref="TABLE-1",
                    source=f"GN_DXF layer={item.layer}",
                    note=text[:120],
                ))

            # Minimum lap 300mm
            m = _MIN_LAP_PAT.search(text)
            if m and "MIN_LAP" not in seen_types:
                val = int(m.group(1))
                if val < 100:   # not a plausible lap length
                    continue
                seen_types.add("MIN_LAP")
                rules.append(LapRule(
                    rule_type="MINIMUM_LAP",
                    value_mm=val,
                    source=f"GN_DXF layer={item.layer}",
                    note=text[:120],
                ))

            # General lapped splice clauses
            if _LAPPED_SPLICE.search(text):
                mm_vals = _LAP_MM_PAT.findall(text)
                for val_str in mm_vals:
                    val = int(val_str)
                    key = f"LAP_MM_{val}"
                    if key not in seen_types and 200 <= val <= 2000:
                        seen_types.add(key)
                        rules.append(LapRule(
                            rule_type="LAP_LENGTH_SPECIFIC",
                            value_mm=val,
                            source=f"GN_DXF layer={item.layer}",
                            note=text[:120],
                        ))

        if not rules:
            warnings.append("LapRuleParser: No lap rules found in GN DXF.")
            rules = [
                LapRule("MINIMUM_LAP", 300, "", "FALLBACK_IS456", "IS 456 minimum lap = 300mm"),
            ]

        return rules, warnings
