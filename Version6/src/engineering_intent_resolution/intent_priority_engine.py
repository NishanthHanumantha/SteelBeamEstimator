"""Load configurable intent priority and resolution rules from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple


class IntentPriorityEngine:
    """Deterministic priority lookup from engineering_intent_priority.yaml."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.priorities: Dict[str, int] = {
            str(key): int(value)
            for key, value in (self.config.get("priorities") or {}).items()
        }
        self.merge_groups: List[dict[str, Any]] = list(self.config.get("merge_groups") or [])
        self.mutual_exclusions: List[Tuple[str, str]] = [
            (str(pair[0]), str(pair[1]))
            for pair in (self.config.get("mutual_exclusions") or [])
            if isinstance(pair, list) and len(pair) == 2
        ]
        self.override_rules: List[dict[str, str]] = [
            {"dominant": str(rule.get("dominant")), "suppresses": str(rule.get("suppresses"))}
            for rule in (self.config.get("override_rules") or [])
        ]
        self.complement_rules: List[dict[str, str]] = [
            {"source": str(rule.get("source")), "complements": str(rule.get("complements"))}
            for rule in (self.config.get("complement_rules") or [])
        ]
        self.require_rules: List[dict[str, str]] = [
            {"source": str(rule.get("source")), "requires": str(rule.get("requires"))}
            for rule in (self.config.get("require_rules") or [])
        ]
        self.equivalent_pairs: List[Tuple[str, str]] = [
            (str(pair[0]), str(pair[1]))
            for pair in (self.config.get("equivalent_pairs") or [])
            if isinstance(pair, list) and len(pair) == 2
        ]

    def priority(self, intent_type: str) -> int:
        return int(self.priorities.get(str(intent_type), self.priorities.get("UNKNOWN", 0)))

    def sort_intents(self, intents: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return sorted(
            intents,
            key=lambda item: (
                -self.priority(str(item.get("intent_type") or "")),
                str(item.get("intent_id") or ""),
                str(item.get("intent_key") or ""),
            ),
        )

    def rules_export(self) -> dict[str, Any]:
        return {
            "model_version": self.config.get("model_version"),
            "phase": self.config.get("phase"),
            "config_path": str(self.config_path),
            "priorities": dict(sorted(self.priorities.items(), key=lambda item: (-item[1], item[0]))),
            "merge_groups": self.merge_groups,
            "mutual_exclusions": [list(pair) for pair in self.mutual_exclusions],
            "override_rules": self.override_rules,
            "complement_rules": self.complement_rules,
            "require_rules": self.require_rules,
            "equivalent_pairs": [list(pair) for pair in self.equivalent_pairs],
        }

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Priority config missing: {path}")
        try:
            import yaml  # type: ignore

            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Priority config root must be a mapping.")
            return payload
        except ImportError:
            return IntentPriorityEngine._load_simple_yaml(path)

    @staticmethod
    def _load_simple_yaml(path: Path) -> dict[str, Any]:
        """Minimal fallback parser for the priority config shape."""
        text = path.read_text(encoding="utf-8")
        result: dict[str, Any] = {
            "priorities": {},
            "merge_groups": [],
            "mutual_exclusions": [],
            "override_rules": [],
            "complement_rules": [],
            "require_rules": [],
            "equivalent_pairs": [],
        }
        section = None
        current_group: dict[str, Any] | None = None
        current_rule: dict[str, Any] | None = None
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()
            if indent == 0 and ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in {
                    "priorities",
                    "merge_groups",
                    "mutual_exclusions",
                    "override_rules",
                    "complement_rules",
                    "require_rules",
                    "equivalent_pairs",
                }:
                    section = key
                    current_group = None
                    current_rule = None
                    continue
                result[key] = value
                section = None
                continue
            if section == "priorities" and ":" in stripped:
                key, value = stripped.split(":", 1)
                result["priorities"][key.strip()] = int(value.strip())
            elif section == "merge_groups":
                if stripped.startswith("- name:"):
                    current_group = {
                        "name": stripped.split(":", 1)[1].strip(),
                        "members": [],
                    }
                    result["merge_groups"].append(current_group)
                elif current_group is not None and stripped.startswith("- ") and indent >= 4:
                    if "members" in (raw_line.lower()):
                        continue
                    member = stripped[2:].strip()
                    if ":" not in member:
                        current_group["members"].append(member)
                elif current_group is not None and ":" in stripped:
                    key, value = stripped.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key != "members":
                        current_group[key] = value
            elif section in {"override_rules", "complement_rules", "require_rules"}:
                if stripped.startswith("- "):
                    current_rule = {}
                    result[section].append(current_rule)
                    body = stripped[2:]
                    if ":" in body:
                        key, value = body.split(":", 1)
                        current_rule[key.strip()] = value.strip()
                elif current_rule is not None and ":" in stripped:
                    key, value = stripped.split(":", 1)
                    current_rule[key.strip()] = value.strip()
            elif section in {"mutual_exclusions", "equivalent_pairs"}:
                if stripped.startswith("- ["):
                    inner = stripped[3:].rstrip("]")
                    parts = [part.strip() for part in inner.split(",")]
                    if len(parts) == 2:
                        result[section].append(parts)
        return result
