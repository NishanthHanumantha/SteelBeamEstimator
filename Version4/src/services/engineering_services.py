"""Engineering services facade — project-scoped logic layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.framing.engineering_ids import RULE_ESTIMATOR, RULE_PROJECT, SERVICES_ID
from src.general_notes.engineering_rule_cache import EngineeringRuleCache
from src.services.concrete_service import ConcreteService
from src.services.cover_service import CoverService
from src.services.development_length_service import DevelopmentLengthService
from src.services.station_service import StationService
from src.services.steel_weight_service import SteelWeightService


class EngineeringServices:
    """Container for project-level engineering logic services."""

    def __init__(
        self,
        cache: EngineeringRuleCache,
    ) -> None:
        self._cache = cache
        self.development_length = DevelopmentLengthService(cache)
        self.cover = CoverService(cache)
        self.station = StationService()
        self.steel_weight = SteelWeightService(cache)
        self.concrete = ConcreteService()

    @classmethod
    def initialize(
        cls,
        output_root: Path,
        knowledge_version: str = "1.0",
    ) -> "EngineeringServices":
        rules_path = output_root / "phase_e" / "general_notes_engineering_rules.json"
        cache = EngineeringRuleCache.get_instance(rules_path)
        logger.info("Engineering services initialized — cache={}", rules_path)
        return cls(cache)

    def resolve_rule(self, rule_id: str) -> Optional[dict[str, Any]]:
        if rule_id in (RULE_PROJECT, "RULE::PROJECT"):
            return self._cache.model
        if rule_id in (RULE_ESTIMATOR, "RULE::ESTIMATOR"):
            return dict(self._cache.model.get("estimator_rules", {}))
        return None

    def registry(self) -> dict[str, Any]:
        services = [
            self.development_length.to_registry_entry(),
            self.cover.to_registry_entry(),
            self.station.to_registry_entry(),
            self.steel_weight.to_registry_entry(),
            self.concrete.to_registry_entry(),
        ]
        return {
            "phase": "Phase F.7",
            "service_id": SERVICES_ID,
            "initialized": True,
            "service_count": len(services),
            "knowledge_references": [RULE_PROJECT, RULE_ESTIMATOR],
            "services": services,
        }

    def to_workspace_ref(self) -> dict[str, Any]:
        return {
            "service_id": SERVICES_ID,
            "initialized": True,
            "service_count": 5,
            "knowledge_references": [RULE_PROJECT, RULE_ESTIMATOR],
        }
