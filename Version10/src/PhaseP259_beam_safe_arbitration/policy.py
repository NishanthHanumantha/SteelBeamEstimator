"""Load P2.5.9 arbitration YAML without PyYAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

_RULES_PATH = Path(__file__).with_name("beam_safe_arbitration.yaml")


def load_arbitration_config(path: Path | None = None) -> Dict[str, Any]:
    src = Path(path or _RULES_PATH)
    text = src.read_text(encoding="utf-8")
    root: Dict[str, Any] = {}
    stack: list = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, _, rest = raw.strip().partition(":")
        val = rest.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        elif val.lower() == "true":
            parent[key] = True
        elif val.lower() == "false":
            parent[key] = False
        else:
            parent[key] = val
    return root


__all__ = ["load_arbitration_config"]
