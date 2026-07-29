"""STEP 9 — MTEXT recovery statistics."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .mtext_models import RecoveryRecord, ValidationRecord

_RE_BAR = re.compile(r"(\d+)\s*[-\u2013]?\s*([YyRrTt])\s*(\d+)", re.I)
_RE_STIRRUP = re.compile(
    r"(?:(\d+)\s*[Ll][-\u2013]\s*)?([YyRrTt])\s*(\d+)\s*@\s*(\d+(?:[/]\d+)*)", re.I
)


def _would_regex_match(text: str) -> bool:
    return bool(_RE_BAR.search(text) or _RE_STIRRUP.search(text))


class MtextStatistics:

    def compute(
        self,
        records: List[RecoveryRecord],
        validations: List[ValidationRecord],
    ) -> Dict[str, Any]:
        total = len(records)
        recovered = sum(1 for r in records if r.new_status == "RECOVERED")
        unchanged = sum(1 for r in records if r.new_status == "UNCHANGED")
        still_lost = sum(1 for r in records if r.new_status == "STILL_LOST")
        formatting_only = sum(1 for r in records if r.old_status == "FORMAT_ONLY")
        previously_lost = sum(1 for r in records if r.old_status == "LOST")

        fmt_tokens_removed = sum(r.formatting_tokens_removed for r in records)
        chars_recovered = sum(r.characters_recovered for r in records)

        old_regex_pass = sum(1 for r in records if r.regex_would_match_old)
        new_regex_pass = sum(1 for r in records if r.regex_would_match_new)

        eng_preserved = sum(1 for v in validations if v.is_valid_engineering)

        return {
            "total_mtext": total,
            "previously_lost": previously_lost,
            "recovered": recovered,
            "unchanged": unchanged,
            "still_lost": still_lost,
            "formatting_only": formatting_only,
            "formatting_tokens_removed": fmt_tokens_removed,
            "characters_recovered": chars_recovered,
            "regex_match_before": old_regex_pass,
            "regex_match_after": new_regex_pass,
            "engineering_preserved": eng_preserved,
            "recovery_pct": round(100.0 * recovered / previously_lost, 2)
            if previously_lost else 100.0,
            "backward_compat_pct": round(
                100.0 * unchanged / (total - previously_lost), 2
            ) if (total - previously_lost) else 100.0,
        }
