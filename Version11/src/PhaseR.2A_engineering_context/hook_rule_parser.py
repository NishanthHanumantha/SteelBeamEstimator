"""
Hook and Bend Rule Parser.

Extracts standard hook / bend rules from GN DXF text.
GN DXF contains:
  - "STANDARD 90 BEND"  with "4xdb"
  - Hook lengths: "4xdb", "5xdb"
  - "135 degree hook both ends" (stirrups)
"""
from __future__ import annotations
import re
from typing import List, Tuple

from .general_notes_text_extractor import GeneralNotesTextExtractor
from .engineering_context_model import HookBendRule

_HOOK_90_PAT  = re.compile(r"STANDARD\s+90\s+(?:DEGREE\s+)?(?:HOOK|BEND)", re.I)
_HOOK_135_PAT = re.compile(r"135\s*(?:DEGREE|DEG)", re.I)
_XDB_PAT      = re.compile(r"(\d+)\s*[xX]\s*db", re.I)
_ND_PAT       = re.compile(r"(\d+)\s*[dD]\b")


class HookRuleParser:
    def __init__(self, extractor: GeneralNotesTextExtractor):
        self._ext = extractor

    def parse(self) -> Tuple[List[HookBendRule], List[str]]:
        warnings: List[str] = []
        rules: List[HookBendRule] = []
        seen: set = set()

        for item in self._ext.extract():
            text = item.text

            # 90-degree standard bend
            if _HOOK_90_PAT.search(text):
                xdb_matches = _XDB_PAT.findall(text)
                for xdb in xdb_matches:
                    val = int(xdb)
                    key = ("90", val)
                    if key not in seen and 2 <= val <= 20:
                        seen.add(key)
                        rules.append(HookBendRule(
                            rule_type="STANDARD_90_BEND",
                            angle_deg=90,
                            multiplier_xd=val,
                            source=f"GN_DXF layer={item.layer}",
                            note=f"From: {text[:80]}",
                        ))

            # 135-degree hook (stirrups)
            if _HOOK_135_PAT.search(text):
                xdb_matches = _XDB_PAT.findall(text)
                nd_matches = _ND_PAT.findall(text)
                multipliers = [int(x) for x in xdb_matches] + [int(x) for x in nd_matches]
                for val in multipliers:
                    key = ("135", val)
                    if key not in seen and 2 <= val <= 20:
                        seen.add(key)
                        rules.append(HookBendRule(
                            rule_type="STANDARD_135_BEND",
                            angle_deg=135,
                            multiplier_xd=val,
                            source=f"GN_DXF layer={item.layer}",
                            note=f"From: {text[:80]}",
                        ))

        # Also collect standalone xdb mentions near hook/bend section
        for item in self._ext.extract():
            text = item.text
            xdb_matches = _XDB_PAT.findall(text)
            for xdb in xdb_matches:
                val = int(xdb)
                key = ("any", val)
                if key not in seen and 2 <= val <= 15:
                    seen.add(key)
                    angle = 90 if val <= 4 else 135
                    rules.append(HookBendRule(
                        rule_type=f"HOOK_{val}XD",
                        angle_deg=angle,
                        multiplier_xd=val,
                        source=f"GN_DXF layer={item.layer}",
                        note=f"xdb reference: {text[:60]}",
                    ))

        if not rules:
            warnings.append("HookRuleParser: No hook/bend rules found in GN DXF.")
            # IS 456 defaults
            rules = [
                HookBendRule("STANDARD_90_BEND", 90, 4, "FALLBACK_IS456:2000", "4d for 90° bend"),
                HookBendRule("STANDARD_135_BEND", 135, 10, "FALLBACK_IS456:2000", "10d for 135° stirrup bend"),
            ]

        return rules, warnings
