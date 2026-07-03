"""Load, validate, cache, and expose estimator methodology rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from loguru import logger

DEFAULT_CONFIG = Path("config/estimator_rules.yaml")

_REQUIRED_SPACER_KEYS = ("diameter_mm", "spacing_mm")
_REQUIRED_STEEL_KEYS = ("unit_weight_formula",)
_REQUIRED_ROUNDING_KEYS = ("precision",)


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse a minimal nested YAML subset (indent-based, no external deps)."""
    if not path.exists():
        raise FileNotFoundError(f"Estimator rules config not found: {path}")

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        if ":" not in content:
            continue
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
            continue

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        else:
            try:
                value = int(value) if "." not in value else float(value)
            except ValueError:
                pass
        parent[key] = value

    return root


class EstimatorRuleLoader:
    """Load estimator methodology from YAML configuration."""

    _instance: Optional["EstimatorRuleLoader"] = None
    _cached_rules: Optional[dict[str, Any]] = None
    _source_path: Optional[Path] = None

    def __init__(self, config_path: Path | str = DEFAULT_CONFIG) -> None:
        self._config_path = Path(config_path)

    @classmethod
    def get_instance(cls, config_path: Path | str | None = None) -> "EstimatorRuleLoader":
        path = Path(config_path) if config_path else DEFAULT_CONFIG
        if cls._instance is None:
            cls._instance = EstimatorRuleLoader(path)
        elif config_path is not None:
            cls._instance._config_path = path
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._cached_rules = None
        cls._source_path = None

    def load(self, config_path: Path | str | None = None) -> dict[str, Any]:
        path = Path(config_path) if config_path else self._config_path
        rules = _parse_simple_yaml(path)
        self.validate(rules)
        EstimatorRuleLoader._cached_rules = rules
        EstimatorRuleLoader._source_path = path
        logger.info("Estimator rules loaded from {}", path)
        return rules

    @property
    def rules(self) -> dict[str, Any]:
        if EstimatorRuleLoader._cached_rules is None:
            return self.load()
        return EstimatorRuleLoader._cached_rules

    def validate(self, rules: dict[str, Any]) -> None:
        spacer = rules.get("spacer", {})
        steel = rules.get("steel", {})
        rounding = rules.get("rounding", {})

        missing: list[str] = []
        for key in _REQUIRED_SPACER_KEYS:
            if key not in spacer:
                missing.append(f"spacer.{key}")
        for key in _REQUIRED_STEEL_KEYS:
            if key not in steel:
                missing.append(f"steel.{key}")
        for key in _REQUIRED_ROUNDING_KEYS:
            if key not in rounding:
                missing.append(f"rounding.{key}")

        if missing:
            raise ValueError(
                "Estimator rules config is incomplete. Missing: "
                + ", ".join(missing)
            )

        if spacer["diameter_mm"] <= 0 or spacer["spacing_mm"] <= 0:
            raise ValueError("Spacer diameter and spacing must be positive.")

        formula = str(steel["unit_weight_formula"]).strip()
        if not formula:
            raise ValueError("Steel unit weight formula must not be empty.")

    def to_knowledge_model(self) -> dict[str, Any]:
        rules = self.rules
        spacer = rules["spacer"]
        steel = rules["steel"]
        rounding = rules["rounding"]
        return {
            "spacer": {
                "diameter_mm": spacer["diameter_mm"],
                "spacing_mm": spacer["spacing_mm"],
            },
            "steel": {
                "unit_weight_formula": steel["unit_weight_formula"],
            },
            "rounding": {
                "precision": rounding["precision"],
            },
            "source": str(self._source_path or self._config_path),
        }

    def get_estimator_spacer(self) -> dict[str, Any]:
        spacer = self.rules["spacer"]
        return {
            "diameter_mm": spacer["diameter_mm"],
            "spacing_mm": spacer["spacing_mm"],
        }

    def get_unit_weight_formula(self) -> str:
        return str(self.rules["steel"]["unit_weight_formula"])

    def get_rounding_precision(self) -> int:
        return int(self.rules["rounding"]["precision"])

    def get_estimator_defaults(self) -> dict[str, Any]:
        spacer = self.get_estimator_spacer()
        return {
            "default_spacer_diameter_mm": spacer["diameter_mm"],
            "default_spacer_spacing_mm": spacer["spacing_mm"],
            "unit_weight_formula": self.get_unit_weight_formula(),
            "rounding_precision": self.get_rounding_precision(),
        }

    def export_json(self, path: Path) -> None:
        path.write_text(
            json.dumps(self.to_knowledge_model(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
