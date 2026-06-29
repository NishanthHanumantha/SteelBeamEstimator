"""BeamEngineeringContext — single computation API for Phase G."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BeamEngineeringContext:
    """Assembled engineering context consumed exclusively by Phase G."""

    context_id: str
    beam_id: str
    beam_mark: str
    beam_section: dict[str, Any]
    engineering_length_model: dict[str, Any]
    engineering_coordinate_system: dict[str, Any]
    support_model: dict[str, Any]
    knowledge_graph_node: dict[str, Any]
    station_api: dict[str, Any]
    relationships: List[dict[str, Any]]
    project_id: str = ""
    floor_id: str = ""
    rule_reference: dict[str, Any] = field(default_factory=dict)
    estimator_rules_reference: dict[str, Any] = field(default_factory=dict)
    project_defaults_reference: dict[str, Any] = field(default_factory=dict)
    services: str = "ENGINEERING_SERVICES"
    metadata: dict[str, Any] = field(default_factory=dict)
    legacy_ids: dict[str, str] = field(default_factory=dict)
    status: str = "READY"
    # Legacy embedded copies — deprecated; retained for backward compatibility reads only
    project_engineering_rules: Optional[dict[str, Any]] = None
    estimator_rules: Optional[dict[str, Any]] = None
    project_defaults: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "context_id": self.context_id,
            "beam_id": self.beam_id,
            "beam_mark": self.beam_mark,
            "status": self.status,
            "project_id": self.project_id,
            "floor_id": self.floor_id,
            "legacy_ids": dict(self.legacy_ids),
            "beam_section": self.beam_section,
            "engineering_length_model": self.engineering_length_model,
            "engineering_coordinate_system": self.engineering_coordinate_system,
            "support_model": self.support_model,
            "knowledge_graph_node": self.knowledge_graph_node,
            "rule_reference": self.rule_reference,
            "estimator_rules_reference": self.estimator_rules_reference,
            "project_defaults_reference": self.project_defaults_reference,
            "services": self.services,
            "station_api": self.station_api,
            "relationships": self.relationships,
            "metadata": self.metadata,
        }
        return payload
