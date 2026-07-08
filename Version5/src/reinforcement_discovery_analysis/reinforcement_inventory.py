"""Build the master reinforcement discovery inventory."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.reinforcement_discovery_analysis.callout_classifier import CalloutClassifier
from src.reinforcement_discovery_analysis.discovery_collector import DiscoveryCollector


ROLE_TO_CATEGORY = {
    "TOP_MAIN": "Top Main",
    "BOTTOM_MAIN": "Bottom Main",
    "TOP_EXTRA": "Top Extra",
    "BOTTOM_EXTRA": "Bottom Extra",
    "STIRRUP": "Stirrups",
    "SIDE_BAR": "Side Face Bars",
    "SPACER_BAR": "Spacer Bars",
    "SFR": "Chair Bars",
    "UNKNOWN": "Other",
}


class ReinforcementInventoryBuilder:
    """Construct the master reinforcement annotation inventory."""

    def __init__(self) -> None:
        self._classifier = CalloutClassifier()

    def build(self, snapshot: dict[str, Any]) -> List[dict[str, Any]]:
        inventory: List[dict[str, Any]] = []
        indexes = dict(snapshot.get("indexes") or {})
        indexes["_calculated_bar_ids"] = set(snapshot.get("calculated_bar_ids") or [])
        text_objects = snapshot.get("text_objects") or []
        sequence = 1

        for text_object in text_objects:
            text = str(text_object.get("text") or "").strip()
            classification = self._classifier.classify_text(text)
            if not classification.is_reinforcement:
                continue

            geometry_id = str(text_object.get("geometry_id") or "")
            ownership = text_object.get("ownership") or {}
            owner_id = str(ownership.get("owner_id") or "")
            beam_association = DiscoveryCollector.beam_mark_from_owner(owner_id)
            association_confidence = float(ownership.get("ownership_confidence") or 0.0)
            association_source = str(ownership.get("ownership_source") or "")

            matched_bar = self._match_bar(
                text_object,
                classification,
                beam_association,
                indexes,
            )
            trace = self._build_trace(matched_bar, indexes, beam_association, classification)

            entry = {
                "discovery_id": f"CALL::{sequence:06d}",
                "geometry_id": geometry_id,
                "original_text": text,
                "coordinates": self._coordinates(text_object.get("bbox")),
                "layer": text_object.get("layer"),
                "block": text_object.get("block_name") or text_object.get("block"),
                "region": owner_id,
                "beam_association": beam_association,
                "section": None,
                "leader": text_object.get("leader"),
                "text_source": text_object.get("entity_type") or "TEXT",
                "callout_confidence": classification.confidence,
                "classification": classification.classification,
                "role": classification.role,
                "category": ROLE_TO_CATEGORY.get(classification.role, "Other"),
                "diameter_mm": classification.diameter_mm,
                "quantity": classification.quantity,
                "spacing_mm": classification.spacing_mm,
                "classified": classification.classification not in {"UNKNOWN", "EMPTY"},
                "ambiguous": classification.ambiguous,
                "multiple_interpretations": classification.multiple_interpretations,
                "unknown": classification.unknown,
                "interpretations": classification.interpretations,
                "association_confidence": association_confidence,
                "association_source": association_source,
                "associated": beam_association is not None and classification.classification not in {"UNKNOWN", "EMPTY"},
                "engineering_object_id": text_object.get("engineering_object_id")
                or trace.get("engineering_object_id"),
                "engineering_status": text_object.get("engineering_status"),
                "normalized_bar_id": trace.get("normalized_bar_id"),
                "calculation_state": trace.get("calculation_state"),
                "bbs_row_id": trace.get("bbs_row_id"),
                "excel_row_number": trace.get("excel_row_number"),
                "failure_stage": trace.get("failure_stage"),
                "failure_reason": trace.get("failure_reason") or classification.failure_reason,
                "current_status": trace.get("current_status"),
                "pipeline_trace": trace.get("pipeline_trace"),
            }
            inventory.append(entry)
            sequence += 1
        return inventory

    def _match_bar(
        self,
        text_object: dict[str, Any],
        classification,
        beam_association: Optional[str],
        indexes: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        geometry_id = str(text_object.get("geometry_id") or "")
        bars_by_geometry = indexes.get("bars_by_geometry") or {}
        if geometry_id in bars_by_geometry:
            return bars_by_geometry[geometry_id]

        engineering_object_id = str(text_object.get("engineering_object_id") or "")
        bars_by_object = indexes.get("bars_by_engineering_object") or {}
        if engineering_object_id and engineering_object_id in bars_by_object:
            return bars_by_object[engineering_object_id]

        if beam_association and classification.diameter_mm is not None:
            callout_variants = self._callout_variants(
                text_object.get("text"),
                classification.quantity,
                classification.diameter_mm,
            )
            bars_by_callout_key = indexes.get("bars_by_callout_key") or {}
            for callout in callout_variants:
                for role in {classification.role, "TOP_MAIN", "STIRRUP", "SIDE_BAR"}:
                    key = f"{beam_association}|{callout}|{classification.diameter_mm}|{role}"
                    if key in bars_by_callout_key:
                        return bars_by_callout_key[key]
        return None

    @staticmethod
    def _callout_variants(text: Any, quantity: Optional[float], diameter_mm: Optional[float]) -> List[str]:
        raw = str(text or "").strip().replace("-", "").replace(" ", "")
        variants = {raw, raw.upper(), raw.lower()}
        if quantity is not None and diameter_mm is not None:
            qty = int(quantity) if quantity == int(quantity) else quantity
            dia = int(diameter_mm) if diameter_mm == int(diameter_mm) else diameter_mm
            variants.add(f"{qty}Y{dia}")
            variants.add(f"{qty}Y{int(diameter_mm)}")
        return [item for item in variants if item]

    def _build_trace(
        self,
        bar: Optional[dict[str, Any]],
        indexes: dict[str, Any],
        beam_association: Optional[str],
        classification,
    ) -> dict[str, Any]:
        pipeline_trace = {
            "text_detected": True,
            "classified": classification.classification not in {"UNKNOWN", "EMPTY"},
            "associated": beam_association is not None
            and classification.classification not in {"UNKNOWN", "EMPTY"},
            "engineering_object_created": False,
            "normalized": False,
            "ready": False,
            "calculated": False,
            "written_to_bbs": False,
            "written_to_excel": False,
        }
        if not pipeline_trace["classified"]:
            return {
                "current_status": "DISCOVERY_FAILED",
                "failure_stage": "classification",
                "failure_reason": classification.failure_reason or "Unsupported notation",
                "pipeline_trace": pipeline_trace,
            }
        if not pipeline_trace["associated"]:
            pipeline_trace["associated"] = False
            return {
                "current_status": "ASSOCIATION_FAILED",
                "failure_stage": "association",
                "failure_reason": "Unknown beam",
                "pipeline_trace": pipeline_trace,
            }

        if bar is None:
            return {
                "current_status": "NORMALIZATION_FAILED",
                "failure_stage": "normalization",
                "failure_reason": "Engineering bar not created",
                "pipeline_trace": pipeline_trace,
            }

        bar_id = str(bar.get("bar_id"))
        traceability = bar.get("traceability") or {}
        pipeline_trace["engineering_object_created"] = bool(traceability.get("engineering_object_id"))
        pipeline_trace["normalized"] = str(bar.get("status", "")).upper() == "NORMALIZED"

        readiness = bar.get("calculation_readiness") or {}
        calculation_state = str(readiness.get("calculation_state") or "UNKNOWN").upper()
        pipeline_trace["ready"] = calculation_state == "READY"
        calculated_bar_ids = set(indexes.get("_calculated_bar_ids") or [])
        pipeline_trace["calculated"] = bar_id in calculated_bar_ids

        bbs_by_bar = indexes.get("bbs_by_bar") or {}
        bbs_record = bbs_by_bar.get(bar_id)
        pipeline_trace["written_to_bbs"] = bbs_record is not None

        schedule_row_by_bar = indexes.get("schedule_row_by_bar") or {}
        schedule_row = schedule_row_by_bar.get(bar_id)
        excel_row_number = None
        excel_row_by_bar = indexes.get("excel_row_by_bar") or {}
        if schedule_row and beam_association:
            fab_mark = schedule_row.get("fabrication_mark")
            role = schedule_row.get("role") or bar.get("role")
            diameter = schedule_row.get("diameter_mm") or bar.get("diameter_mm")
            candidate_keys = [
                f"{beam_association}|{role}|{diameter}|{fab_mark or ''}",
                f"{beam_association}|{role}|{diameter}|",
                f"{beam_association}|{role}|{int(diameter) if diameter == int(diameter) else diameter}|",
            ]
            excel_row = None
            for key in candidate_keys:
                excel_row = excel_row_by_bar.get(key)
                if excel_row is not None:
                    break
            if excel_row is None:
                for key, row in excel_row_by_bar.items():
                    if not key.startswith(f"{beam_association}|{role}|"):
                        continue
                    key_diameter = key.split("|")[2]
                    try:
                        if float(key_diameter) == float(diameter):
                            excel_row = row
                            break
                    except (TypeError, ValueError):
                        continue
            if excel_row is not None:
                pipeline_trace["written_to_excel"] = True
                excel_row_number = getattr(excel_row, "row_number", None)

        current_status = self._resolve_status(pipeline_trace, calculation_state)
        failure_stage = None
        failure_reason = None
        if current_status.endswith("FAILED") or current_status in {
            "DISCOVERY_FAILED",
            "ASSOCIATION_FAILED",
            "NORMALIZATION_FAILED",
            "CALCULATION_DEFERRED",
            "EXPORT_SKIPPED",
        }:
            failure_stage, failure_reason = self._failure_details(current_status, readiness, pipeline_trace)

        return {
            "normalized_bar_id": bar_id,
            "engineering_object_id": traceability.get("engineering_object_id"),
            "calculation_state": calculation_state,
            "bbs_row_id": (bbs_record or {}).get("bbs_id") if bbs_record else None,
            "excel_row_number": excel_row_number,
            "current_status": current_status,
            "failure_stage": failure_stage,
            "failure_reason": failure_reason,
            "pipeline_trace": pipeline_trace,
        }

    @staticmethod
    def _resolve_status(pipeline_trace: dict[str, bool], calculation_state: str) -> str:
        if pipeline_trace.get("written_to_excel"):
            return "WRITTEN_TO_EXCEL"
        if pipeline_trace.get("written_to_bbs"):
            return "WRITTEN_TO_BBS"
        if pipeline_trace.get("calculated"):
            return "CALCULATED"
        if calculation_state == "READY":
            return "READY"
        if calculation_state == "DEFERRED":
            return "CALCULATION_DEFERRED"
        if calculation_state == "BLOCKED":
            return "DISCOVERY_FAILED"
        if pipeline_trace.get("normalized"):
            return "NORMALIZED"
        if pipeline_trace.get("engineering_object_created"):
            return "ENGINEERING_OBJECT_CREATED"
        if pipeline_trace.get("associated"):
            return "ASSOCIATION_FAILED" if not pipeline_trace.get("normalized") else "NORMALIZED"
        if pipeline_trace.get("classified"):
            return "ASSOCIATION_FAILED"
        if pipeline_trace.get("text_detected"):
            return "DISCOVERY_FAILED"
        return "NOT_DETECTED"

    @staticmethod
    def _failure_details(
        current_status: str,
        readiness: dict[str, Any],
        pipeline_trace: dict[str, bool],
    ) -> tuple[Optional[str], Optional[str]]:
        if current_status == "CALCULATION_DEFERRED":
            return "calculation", readiness.get("defer_reason") or "Calculation deferred"
        if current_status == "EXPORT_SKIPPED":
            return "export", "Export skipped"
        if current_status == "NORMALIZATION_FAILED":
            return "normalization", "Engineering bar not created"
        if current_status == "ASSOCIATION_FAILED":
            return "association", "Unknown beam"
        if current_status == "DISCOVERY_FAILED":
            return "classification", "Unsupported notation"
        if pipeline_trace.get("normalized") and not pipeline_trace.get("calculated"):
            return "calculation", "Calculation incomplete"
        return None, None

    @staticmethod
    def _coordinates(bbox: Any) -> Optional[dict[str, float]]:
        if not isinstance(bbox, dict):
            return None
        min_x = bbox.get("min_x")
        min_y = bbox.get("min_y")
        if min_x is None or min_y is None:
            return None
        return {"x": float(min_x), "y": float(min_y)}
