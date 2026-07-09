"""Load duplicate groups and engineering context for legitimacy audit."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.estimator_validation.comparison_utils import load_json_if_exists

PHASE = "Phase QA.COVERAGE.5"
MODEL_VERSION = "5.25.0"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/duplicate_legitimacy_audit")
OBJECT_AUDIT_DIR = Path("data/output/engineering_object_audit")
DISCOVERY_DIR = Path("data/output/reinforcement_discovery_analysis")

COORDINATE_TOLERANCE = 75.0
STATION_TOLERANCE_MM = 250.0


class DuplicateLegitimacy(str, Enum):
    TRUE_GRAPHICAL_REPEAT = "TRUE_GRAPHICAL_REPEAT"
    TRUE_DUPLICATE = "TRUE_DUPLICATE"
    VALID_MERGE = "VALID_MERGE"
    REINFORCEMENT_REGION_VARIANT = "REINFORCEMENT_REGION_VARIANT"
    LEFT_RIGHT_VARIANT = "LEFT_RIGHT_VARIANT"
    TOP_BOTTOM_VARIANT = "TOP_BOTTOM_VARIANT"
    SPAN_VARIANT = "SPAN_VARIANT"
    SUPPORT_VARIANT = "SUPPORT_VARIANT"
    CENTER_VARIANT = "CENTER_VARIANT"
    LEADER_VARIANT = "LEADER_VARIANT"
    POTENTIAL_ENGINEERING_BAR = "POTENTIAL_ENGINEERING_BAR"
    LIKELY_ENGINEERING_BAR = "LIKELY_ENGINEERING_BAR"
    INCORRECT_SUPPRESSION = "INCORRECT_SUPPRESSION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"


LEGITIMATE_CLASSES = frozenset(
    {
        DuplicateLegitimacy.TRUE_GRAPHICAL_REPEAT,
        DuplicateLegitimacy.TRUE_DUPLICATE,
        DuplicateLegitimacy.VALID_MERGE,
        DuplicateLegitimacy.REINFORCEMENT_REGION_VARIANT,
        DuplicateLegitimacy.LEFT_RIGHT_VARIANT,
        DuplicateLegitimacy.TOP_BOTTOM_VARIANT,
        DuplicateLegitimacy.SPAN_VARIANT,
        DuplicateLegitimacy.SUPPORT_VARIANT,
        DuplicateLegitimacy.CENTER_VARIANT,
        DuplicateLegitimacy.LEADER_VARIANT,
    }
)

RISK_CLASSES = frozenset(
    {
        DuplicateLegitimacy.POTENTIAL_ENGINEERING_BAR,
        DuplicateLegitimacy.LIKELY_ENGINEERING_BAR,
        DuplicateLegitimacy.INCORRECT_SUPPRESSION,
    }
)


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_i = root / Path("data/output/phase_i")
    phase_g = root / Path("data/output/phase_g")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "object_creation_audit": root / OBJECT_AUDIT_DIR / "engineering_object_creation_audit.json",
        "decision_matrix": root / OBJECT_AUDIT_DIR / "engineering_object_decision_matrix.json",
        "duplicate_analysis": root / OBJECT_AUDIT_DIR / "duplicate_analysis.json",
        "reinforcement_inventory": root / DISCOVERY_DIR / "reinforcement_inventory.json",
        "traceability_matrix": root / DISCOVERY_DIR / "reinforcement_traceability_matrix.json",
        "reinforcement_text": phase_g / "g_2_reinforcement_drawing/reinforcement_text.json",
        "engineering_properties": phase_g / "g_5_3_1_property_parser/engineering_properties.json",
        "resolved_properties": phase_g / "g_5_3_2_property_resolver/resolved_engineering_properties.json",
        "calculation_context": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "geometry_model": root / Path("data/output/phase_f/beam_geometry_model.json"),
    }


class DuplicateGroupLoader:
    """Load duplicate groups and supporting engineering artifacts."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def load(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        for key, path in self.paths.items():
            if key == "output_dir":
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        duplicate_payload = payloads.get("duplicate_analysis") or {}
        inventory_payload = payloads.get("reinforcement_inventory") or {}
        decision_payload = payloads.get("decision_matrix") or {}
        audit_payload = payloads.get("object_creation_audit") or {}

        inventory = inventory_payload.get("inventory") or []
        inventory_by_id = {str(item.get("discovery_id")): item for item in inventory}
        decision_by_id = {
            str(item.get("discovery_id")): item for item in (decision_payload.get("records") or [])
        }
        audit_by_id = {
            str(item.get("discovery_id")): item
            for item in (audit_payload.get("audits") or [])
        }

        text_objects = (payloads.get("reinforcement_text") or {}).get("text_objects") or []
        text_by_geometry = {
            str(item.get("geometry_id")): item for item in text_objects if item.get("geometry_id")
        }

        contexts = (payloads.get("calculation_context") or {}).get("contexts") or []
        contexts_by_beam = {str(item.get("beam_id")): item for item in contexts if item.get("beam_id")}

        bars = (payloads.get("reinforcement_objects") or {}).get("bars") or []
        bars_by_id = {str(item.get("bar_id")): item for item in bars}

        properties = (payloads.get("engineering_properties") or {}).get("properties") or []
        properties_by_geometry: Dict[str, List[dict[str, Any]]] = {}
        for prop in properties:
            source = str(prop.get("source_entity_id") or "")
            if source:
                properties_by_geometry.setdefault(source, []).append(prop)

        groups = duplicate_payload.get("groups") or []
        enriched_groups = []
        for group in groups:
            members = []
            for member in group.get("members") or []:
                discovery_id = str(member.get("discovery_id"))
                inventory_item = inventory_by_id.get(discovery_id, {})
                geometry_id = str(member.get("geometry_id") or inventory_item.get("geometry_id") or "")
                text_object = text_by_geometry.get(geometry_id, {})
                decision = decision_by_id.get(discovery_id, {})
                audit = audit_by_id.get(discovery_id, {})
                bar_id = member.get("normalized_bar_id") or inventory_item.get("normalized_bar_id")
                bar = bars_by_id.get(str(bar_id)) if bar_id else None
                members.append(
                    {
                        **member,
                        **inventory_item,
                        "decision": decision,
                        "audit": audit,
                        "text_object": text_object,
                        "properties": properties_by_geometry.get(geometry_id, []),
                        "bar": bar,
                        "suppressed": decision.get("primary_rejection_code") == "DUPLICATE_SUPPRESSED",
                        "primary_callout": discovery_id
                        == sorted(
                            str(item.get("discovery_id"))
                            for item in (group.get("members") or [])
                        )[0],
                    }
                )
            beam_id = self._beam_from_signature(group.get("signature", ""), members)
            enriched_groups.append(
                {
                    **group,
                    "group_id": group.get("signature"),
                    "beam_id": beam_id,
                    "context": contexts_by_beam.get(beam_id, {}),
                    "members": members,
                }
            )

        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "duplicate_groups": enriched_groups,
            "inventory_by_id": inventory_by_id,
            "contexts_by_beam": contexts_by_beam,
            "text_by_geometry": text_by_geometry,
            "bars_by_id": bars_by_id,
        }

    @staticmethod
    def _beam_from_signature(signature: str, members: List[dict[str, Any]]) -> str:
        if signature:
            return signature.split("|", 1)[0]
        for member in members:
            beam = member.get("beam_association") or member.get("beam")
            if beam:
                return str(beam)
        return "UNKNOWN"
