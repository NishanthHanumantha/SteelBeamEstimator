"""STEP 3 — Parse AutoCAD MTEXT formatting commands."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .mtext_models import MtextEntity

# AutoCAD MTEXT format command catalogue
_FORMAT_CATALOGUE = {
    r"\\A\d;": "ALIGNMENT",
    r"\\H[^;]+;": "HEIGHT",
    r"\\W[^;]+;": "WIDTH_FACTOR",
    r"\\Q[^;]+;": "OBLIQUE_ANGLE",
    r"\\T[^;]+;": "TRACKING",
    r"\\f[^;]+;": "FONT",
    r"\\F[^;]+;": "FONT_ALT",
    r"\\C[^;]+;": "COLOR",
    r"\\p[^;]+;": "PARAGRAPH_INDENT",
    r"\\L": "UNDERLINE_START",
    r"\\l": "UNDERLINE_END",
    r"\\O": "OVERSTRIKE_START",
    r"\\o": "OVERSTRIKE_END",
    r"\\K": "STRIKETHROUGH_START",
    r"\\k": "STRIKETHROUGH_END",
    r"\\P": "PARAGRAPH_BREAK",
    r"\\\\": "ESCAPED_BACKSLASH",
}

_BRACE_RX = re.compile(r"\{([^{}]*)\}")


def _classify_cmd(cmd: str) -> str:
    for pattern, label in _FORMAT_CATALOGUE.items():
        if re.match(pattern, cmd, re.I):
            return label
    return "UNKNOWN_FORMAT"


def parse_mtext_formatting(entity: MtextEntity) -> Dict[str, Any]:
    """Return a per-entity formatting structure report."""
    raw = entity.raw_text
    brace_blocks = []
    for m in _BRACE_RX.finditer(raw):
        content = m.group(1)
        cmds = re.findall(r"\\[A-Za-z][^;{}]*;|\\[LlOoKkP\\]", content)
        brace_blocks.append({
            "span": [m.start(), m.end()],
            "raw_block": m.group(0)[:80],
            "inner_content": content[:80],
            "format_commands": [
                {"cmd": c, "type": _classify_cmd(c)} for c in cmds
            ],
            "text_after_strip": re.sub(
                r"\\[A-Za-z][^;{}]*;|\\[LlOoKkP\\]", "", content
            ).strip(),
        })

    top_cmds = re.findall(
        r"\\[A-Za-z][^;]*;|\\[LlOoKkP]|\\\\", raw
    )

    return {
        "entity_id": entity.entity_id,
        "raw_text": raw[:120],
        "brace_blocks": brace_blocks,
        "top_level_format_commands": [
            {"cmd": c, "type": _classify_cmd(c)} for c in top_cmds
        ],
        "total_format_commands": len(top_cmds) + sum(
            len(b["format_commands"]) for b in brace_blocks
        ),
        "has_nested_formatting": bool(brace_blocks),
    }


class MtextFormatterParser:

    def parse_all(self, entities: List[MtextEntity]) -> List[Dict[str, Any]]:
        return [parse_mtext_formatting(e) for e in entities]
