"""Load read-only inputs for engineering object creation audit."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.estimator_validation.comparison_utils import load_json_if_exists
from src.reinforcement_discovery_analysis.discovery_collector import _list as discovery_list

PHASE = "Phase QA.COVERAGE.4"
MODEL_VERSION = "5.24.0"
ENGINE_VERSION = "1.0.0"
OUTPUT_DIR_REL = Path("data/output/engineering_object_audit")
DISCOVERY_INVENTORY_REL = Path(
    "data/output/reinforcement_discovery_analysis/reinforcement_inventory.json"
)
DISCOVERY_MATRIX_REL = Path(
    "data/output/reinforcement_discovery_analysis/reinforcement_traceability_matrix.json"
)

REJECTION_CODES: tuple[str, ...] = (
    "UNKNOWN",
    "NOT_REINFORCEMENT",
    "UNSUPPORTED_NOTATION",
    "AMBIGUOUS_CALLOUT",
    "BEAM_NOT_ASSOCIATED",
    "MULTIPLE_BEAM_CANDIDATES",
    "MISSING_GEOMETRY",
    "MISSING_SECTION",
    "MISSING_POSITION",
    "MISSING_BAR_ROLE",
    "MISSING_BAR_TYPE",
    "MISSING_SPECIFICATION",
    "MISSING_DIAMETER",
    "MISSING_QUANTITY",
    "INVALID_SPACING",
    "INVALID_HOOK",
    "INVALID_DEVELOPMENT_LENGTH",
    "INVALID_COVER",
    "UNSUPPORTED_CONFIGURATION",
    "DUPLICATE_SUPPRESSED",
    "ENGINEERING_RULE_CONFLICT",
    "NORMALIZATION_FAILED",
    "UNKNOWN_ENGINEERING_STATE",
)

READINESS_COMPONENTS: tuple[str, ...] = (
    "geometry",
    "beam",
    "specification",
    "section",
    "position",
    "role",
)


def default_paths(project_root: Path | None = None) -> dict[str, Path]:
    root = project_root or Path.cwd()
    phase_i = root / Path("data/output/phase_i")
    phase_g = root / Path("data/output/phase_g")
    return {
        "output_dir": root / OUTPUT_DIR_REL,
        "reinforcement_inventory": root / DISCOVERY_INVENTORY_REL,
        "traceability_matrix": root / DISCOVERY_MATRIX_REL,
        "reinforcement_text": phase_g / "g_2_reinforcement_drawing/reinforcement_text.json",
        "engineering_properties": phase_g / "g_5_3_1_property_parser/engineering_properties.json",
        "resolved_properties": phase_g / "g_5_3_2_property_resolver/resolved_engineering_properties.json",
        "reinforcement_objects": phase_i / "i_2_reinforcement_engine/reinforcement_objects.json",
        "calculation_context": phase_i / "i_1_calculation_context/calculation_contexts.json",
        "beam_schedule": phase_i / "i_15_beam_schedule/beam_schedule_results.json",
    }


def round_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0 if numerator <= 0 else 100.0
    return round(min((numerator / denominator) * 100.0, 100.0), 2)


class AuditCollector:
    """Collect reinforcement inventory and engineering pipeline snapshots."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)
        self.load_status: Dict[str, bool] = {}

    def collect(self) -> dict[str, Any]:
        payloads: Dict[str, Any] = {}
        for key, path in self.paths.items():
            if key == "output_dir":
                continue
            payloads[key] = load_json_if_exists(path)
            self.load_status[key] = payloads[key] is not None

        inventory_payload = payloads.get("reinforcement_inventory") or {}
        inventory = inventory_payload.get("inventory") or []
        matrix_payload = payloads.get("traceability_matrix") or {}
        matrix_records = matrix_payload.get("records") or []

        reinforcement_objects = payloads.get("reinforcement_objects") or {}
        bars = reinforcement_objects.get("bars") or []
        contexts = discovery_list(payloads.get("calculation_context"), "contexts")
        engineering_properties = payloads.get("engineering_properties") or {}
        reinforcement_text = payloads.get("reinforcement_text") or {}
        text_objects = reinforcement_text.get("text_objects") or []

        indexes = self._build_indexes(
            inventory,
            bars,
            contexts,
            engineering_properties,
            text_objects,
        )
        return {
            "paths": {key: str(path) for key, path in self.paths.items()},
            "load_status": dict(self.load_status),
            "inventory": inventory,
            "traceability_matrix": matrix_records,
            "bars": bars,
            "contexts": contexts,
            "engineering_properties": engineering_properties,
            "text_objects": text_objects,
            "indexes": indexes,
        }

    @staticmethod
    def _build_indexes(
        inventory: List[dict[str, Any]],
        bars: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        engineering_properties: dict[str, Any],
        text_objects: List[dict[str, Any]],
    ) -> dict[str, Any]:
        contexts_by_beam = {
            str(item.get("beam_id")): item for item in contexts if item.get("beam_id")
        }
        text_by_geometry = {
            str(item.get("geometry_id")): item
            for item in text_objects
            if item.get("geometry_id")
        }

        bars_by_id = {str(item.get("bar_id")): item for item in bars}
        bars_by_geometry: Dict[str, str] = {}
        bars_by_signature: Dict[str, str] = {}
        engineering_objects_by_id: Dict[str, dict[str, Any]] = {}

        for bar in bars:
            trace = bar.get("traceability") or {}
            spec_trace = trace.get("specification_traceability") or {}
            engineering_object_id = str(trace.get("engineering_object_id") or "")
            if engineering_object_id:
                engineering_objects_by_id[engineering_object_id] = {
                    "bar_id": bar.get("bar_id"),
                    "beam_id": bar.get("beam_id"),
                    "role": bar.get("role"),
                    "diameter_mm": bar.get("diameter_mm"),
                    "callout": trace.get("callout"),
                }
            for chain in spec_trace.get("property_chains") or []:
                geometry_id = str(chain.get("drawing_entity_id") or "")
                if geometry_id.startswith("TXT::"):
                    bars_by_geometry[geometry_id] = str(bar.get("bar_id"))
            callout = str(trace.get("callout") or "")
            signature = AuditCollector._bar_signature(
                str(bar.get("beam_id") or ""),
                callout,
                bar.get("diameter_mm"),
                str(bar.get("role") or ""),
            )
            if signature:
                bars_by_signature[signature] = str(bar.get("bar_id"))

        properties_by_geometry: Dict[str, List[dict[str, Any]]] = {}
        for prop in engineering_properties.get("properties") or engineering_properties.get("results") or []:
            source_entity = str(prop.get("source_entity_id") or "")
            if source_entity:
                properties_by_geometry.setdefault(source_entity, []).append(prop)

        claimants_by_bar: Dict[str, List[str]] = {}
        claimants_by_signature: Dict[str, List[str]] = {}
        for item in inventory:
            discovery_id = str(item.get("discovery_id"))
            signature = AuditCollector._inventory_signature(item)
            if signature:
                claimants_by_signature.setdefault(signature, []).append(discovery_id)
            bar_id = item.get("normalized_bar_id")
            if not bar_id:
                continue
            claimants_by_bar.setdefault(str(bar_id), []).append(discovery_id)

        return {
            "contexts_by_beam": contexts_by_beam,
            "text_by_geometry": text_by_geometry,
            "bars_by_id": bars_by_id,
            "bars_by_geometry": bars_by_geometry,
            "bars_by_signature": bars_by_signature,
            "engineering_objects_by_id": engineering_objects_by_id,
            "properties_by_geometry": properties_by_geometry,
            "claimants_by_bar": claimants_by_bar,
            "claimants_by_signature": claimants_by_signature,
        }

    @staticmethod
    def _bar_signature(beam_id: str, callout: str, diameter_mm: Any, role: str) -> str:
        if not beam_id or not callout:
            return ""
        return f"{beam_id}|{callout}|{diameter_mm}|{role}"

    @staticmethod
    def _inventory_signature(item: dict[str, Any]) -> str:
        beam = str(item.get("beam_association") or "")
        text = str(item.get("original_text") or "").replace("-", "").replace(" ", "")
        qty = item.get("quantity")
        dia = item.get("diameter_mm")
        role = str(item.get("role") or "")
        callout = text.upper()
        if qty is not None and dia is not None:
            qty_int = int(qty) if float(qty) == int(qty) else qty
            dia_int = int(dia) if float(dia) == int(dia) else dia
            callout = f"{qty_int}Y{dia_int}"
        return AuditCollector._bar_signature(beam, callout, dia, role)

    @staticmethod
    def matching_bar_id(item: dict[str, Any], indexes: dict[str, Any]) -> Optional[str]:
        geometry_id = str(item.get("geometry_id") or "")
        bars_by_geometry = indexes.get("bars_by_geometry") or {}
        if geometry_id in bars_by_geometry:
            return bars_by_geometry[geometry_id]

        signature = AuditCollector._inventory_signature(item)
        bars_by_signature = indexes.get("bars_by_signature") or {}
        if signature in bars_by_signature:
            return bars_by_signature[signature]

        for role in {item.get("role"), "TOP_MAIN", "STIRRUP", "SIDE_BAR"}:
            if not role:
                continue
            alt = AuditCollector._bar_signature(
                str(item.get("beam_association") or ""),
                str(item.get("original_text") or "").replace("-", "").replace(" ", "").upper(),
                item.get("diameter_mm"),
                str(role),
            )
            if alt in bars_by_signature:
                return bars_by_signature[alt]
        return None
