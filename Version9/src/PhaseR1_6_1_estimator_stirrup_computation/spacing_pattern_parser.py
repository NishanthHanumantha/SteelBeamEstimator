"""
Spacing pattern parser: 100 → [100]; 100/200/100 → [100,200,100]
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

import re
from typing import List

MODEL_VERSION = "8.8.1"


class SpacingPatternParser:
    def parse(self, spacing_text: str) -> List[int]:
        text = (spacing_text or "").strip()
        text = re.sub(r"[Cc]\s*/\s*[Cc]", "", text)
        text = text.replace(" ", "")
        if not text:
            return []
        parts = re.split(r"[/\\|,;]+", text)
        values: List[int] = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if not re.fullmatch(r"\d{2,4}", p):
                continue
            values.append(int(p))
        return values

    def to_pattern(self, values: List[int]) -> str:
        return "/".join(str(v) for v in values)
