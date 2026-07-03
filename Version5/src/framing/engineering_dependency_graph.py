"""Engineering computation dependency framework (metadata only)."""

from __future__ import annotations

from typing import Any, Dict, List

# Future Phase G computation dependencies — no quantities computed in F.6
COMPUTATION_REGISTRY: Dict[str, dict[str, Any]] = {
    "concrete_volume": {
        "description": "Beam concrete volume",
        "depends_on": [
            "beam_section",
            "engineering_length_model",
            "project_engineering_rules",
        ],
        "status": "NOT_STARTED",
    },
    "bottom_steel": {
        "description": "Bottom longitudinal reinforcement",
        "depends_on": [
            "reinforcement",
            "development_length",
            "beam_section",
            "engineering_length_model",
            "estimator_rules",
        ],
        "status": "NOT_STARTED",
    },
    "top_steel": {
        "description": "Top longitudinal reinforcement",
        "depends_on": [
            "reinforcement",
            "development_length",
            "beam_section",
            "engineering_length_model",
            "estimator_rules",
        ],
        "status": "NOT_STARTED",
    },
    "stirrups": {
        "description": "Shear reinforcement",
        "depends_on": [
            "reinforcement",
            "beam_section",
            "engineering_length_model",
            "project_engineering_rules",
            "estimator_rules",
        ],
        "status": "NOT_STARTED",
    },
    "development_length": {
        "description": "Bar development length",
        "depends_on": [
            "project_engineering_rules",
            "beam_section",
        ],
        "status": "NOT_STARTED",
    },
    "beam_quantities": {
        "description": "Aggregated beam quantities",
        "depends_on": [
            "concrete_volume",
            "bottom_steel",
            "top_steel",
            "stirrups",
            "estimator_rules",
        ],
        "status": "NOT_STARTED",
    },
    "boq_line_items": {
        "description": "Bill of quantities line items",
        "depends_on": [
            "beam_quantities",
            "estimator_rules",
            "project_defaults",
        ],
        "status": "NOT_STARTED",
    },
}


class EngineeringDependencyGraph:
    """Track computation dependencies for Phase G."""

    def build(self) -> dict[str, Any]:
        nodes = [
            {"id": key, "type": "COMPUTATION", **meta}
            for key, meta in COMPUTATION_REGISTRY.items()
        ]
        edges: List[dict[str, Any]] = []
        for comp_id, meta in COMPUTATION_REGISTRY.items():
            for dep in meta.get("depends_on", []):
                edges.append(
                    {
                        "from": comp_id,
                        "to": dep,
                        "relationship": "DEPENDS_ON",
                    }
                )
        return {
            "phase": "Phase F.6",
            "description": "Engineering computation dependency framework",
            "computation_count": len(nodes),
            "edge_count": len(edges),
            "computations": nodes,
            "edges": edges,
        }

    def build_registry(self) -> dict[str, Any]:
        beam_root_deps = [
            "beam_section",
            "engineering_length_model",
            "engineering_coordinate_system",
            "support_model",
            "project_engineering_rules",
            "estimator_rules",
        ]
        entries: List[dict[str, Any]] = [
            {
                "computation": "beam_engineering",
                "depends_on": beam_root_deps,
                "status": "NOT_STARTED",
            }
        ]
        for comp_id, meta in COMPUTATION_REGISTRY.items():
            entries.append(
                {
                    "computation": comp_id,
                    "depends_on": list(meta.get("depends_on", [])),
                    "status": meta.get("status", "NOT_COMPUTED"),
                }
            )
        return {
            "phase": "Phase F.6",
            "entries": entries,
        }
