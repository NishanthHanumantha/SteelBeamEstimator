"""Load the auditable Vision field promotion whitelist."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .config import FORBIDDEN_FIELDS

_RULES_PATH = Path(__file__).with_name("vision_field_promotion_rules.yaml")


def load_promotion_rules(path: Path | None = None) -> Dict[str, Any]:
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


def is_whitelisted(*, semantic_type: str, field: str, rules: Dict[str, Any] | None = None) -> bool:
    rules = rules or load_promotion_rules()
    if field in FORBIDDEN_FIELDS or field == "zone":
        return False
    if field == "reinforcement_role":
        field = "role"
    st = (semantic_type or "").upper()
    bucket = "STIRRUP"
    if "SIDE_FACE" in st:
        bucket = "SIDE_FACE"
    elif st in ("LONGITUDINAL_BAR", "LONGITUDINAL"):
        bucket = "LONGITUDINAL"
    node = rules.get(bucket)
    if isinstance(node, dict):
        return bool(node.get(field, False))
    return False


__all__ = ["is_whitelisted", "load_promotion_rules"]
