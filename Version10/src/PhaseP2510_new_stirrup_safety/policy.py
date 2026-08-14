"""Load P2.5.10 insertion-safety YAML without PyYAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

_RULES_PATH = Path(__file__).with_name("insertion_safety.yaml")


def load_insertion_config(path: Path | None = None) -> Dict[str, Any]:
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
            try:
                parent[key] = int(val)
            except ValueError:
                parent[key] = val
    return root


__all__ = ["load_insertion_config"]
