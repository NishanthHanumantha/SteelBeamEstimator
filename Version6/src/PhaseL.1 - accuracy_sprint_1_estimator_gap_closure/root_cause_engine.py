"""Assign deterministic root cause to every engineering gap."""

from __future__ import annotations

from typing import Any, Dict, List

PHASE_ORIGIN_ORDER = [
    "Phase A", "Phase B", "Phase C", "Phase D", "Phase E",
    "Phase F", "Phase G", "Phase H", "Phase I",
    "Phase J", "Phase K.1", "Phase K.1.1", "Phase K.2", "Phase K.2.1",
    "Phase I.3", "Phase I.4", "Phase I.6", "Phase I.10",
    "Phase I.11", "Phase I.15", "Phase I.16", "Phase I.17",
]

ROOT_CAUSE_MAP: Dict[str, Dict[str, str]] = {
    "PARSER_GAP": {
        "what": "Drawing annotation not detected or parsed",
        "why": "DXF parser failed to extract or tokenise the text object",
        "where": "DXF extraction layer",
        "pipeline_phase": "Phase A–D (DXF parsing)",
    },
    "GEOMETRY_GAP": {
        "what": "Beam span or section dimensions inaccurate",
        "why": "Framing geometry or beam boundary detection produced wrong dimensions",
        "where": "Phase F Framing Geometry",
        "pipeline_phase": "Phase F",
    },
    "SPECIFICATION_GAP": {
        "what": "Concrete grade, steel grade or cover not correctly captured",
        "why": "General note parsing missed specification value or applied wrong default",
        "where": "Phase E General Notes",
        "pipeline_phase": "Phase E",
    },
    "RECOVERY_GAP": {
        "what": "Engineering object exists but recovery failed to include it",
        "why": "Recovery heuristic did not match object to beam context",
        "where": "Phase J Recovery Engine",
        "pipeline_phase": "Phase J.1–J.2",
    },
    "INTENT_GAP": {
        "what": "Reinforcement present in drawing but intent not reconstructed",
        "why": "Engineering intent rule for this reinforcement type not implemented",
        "where": "Phase K.1 Engineering Intent Reconstruction",
        "pipeline_phase": "Phase K.1",
    },
    "DECISION_GAP": {
        "what": "Intent reconstructed but not resolved to an executable decision",
        "why": "Decision resolution rule missing or priority conflict not resolved",
        "where": "Phase K.1.1 Engineering Decision Resolution",
        "pipeline_phase": "Phase K.1.1",
    },
    "RULE_GAP": {
        "what": "Engineering category not implemented in pipeline",
        "why": "No engineering rule exists for this reinforcement type in current model",
        "where": "Phase K.1 Engineering Intent / Phase I calculation engines",
        "pipeline_phase": "Phase K.1, Phase I.3–I.6",
    },
    "CALCULATION_GAP": {
        "what": "Engineering decision exists but calculation not performed or not complete",
        "why": "Phase I pipeline not fully executed in Version6, or DEFERRED/BLOCKED status",
        "where": "Phase I.1–I.17 Calculation Pipeline",
        "pipeline_phase": "Phase I",
    },
    "REPORTING_GAP": {
        "what": "Calculation completed but not included in beam schedule or report",
        "why": "Schedule builder or report aggregation excluded result",
        "where": "Phase I.15 Beam Schedule / Phase I.16 Engineering Report",
        "pipeline_phase": "Phase I.15–I.16",
    },
    "EXCEL_PRESENTATION_GAP": {
        "what": "Engineering result correct but Excel format differs from estimator",
        "why": "Template column mapping, row ordering or number format mismatch",
        "where": "Phase I.17 Excel Export",
        "pipeline_phase": "Phase I.17",
    },
    "UNKNOWN": {
        "what": "Cause could not be deterministically identified",
        "why": "Insufficient evidence in available pipeline outputs",
        "where": "Unknown",
        "pipeline_phase": "Unknown",
    },
}


class RootCauseEngine:
    """Enrich gaps with deterministic root cause evidence."""

    def analyze(
        self,
        gaps: List[Dict[str, Any]],
        snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        enriched = []
        for gap in gaps:
            category = str(gap.get("gap_category") or "UNKNOWN")
            template = ROOT_CAUSE_MAP.get(category, ROOT_CAUSE_MAP["UNKNOWN"])
            enriched_gap = dict(gap)
            enriched_gap["root_cause"] = {
                "category": category,
                "what_differs": template["what"],
                "why_it_differs": template["why"],
                "where_introduced": template["where"],
                "pipeline_phase_origin": gap.get("phase_origin") or template["pipeline_phase"],
                "affected_engineering_objects": self._affected_objects(gap, snapshot),
                "affected_beams": gap.get("affected_beams") or [],
                "affected_roles": gap.get("affected_roles") or [],
                "affected_diameters": gap.get("affected_diameters") or [],
                "future_phase_resolution": gap.get("future_phase") or "Phase L.2",
                "evidence": gap.get("evidence") or "See gap description",
                "deterministic": True,
            }
            enriched.append(enriched_gap)
        return enriched

    @staticmethod
    def _affected_objects(gap: Dict[str, Any], snapshot: Dict[str, Any]) -> List[str]:
        affected_beams = gap.get("affected_beams") or []
        decisions_by_beam = snapshot.get("decisions_by_beam") or {}
        objects: List[str] = []
        for beam in affected_beams[:5]:
            for d in (decisions_by_beam.get(beam) or []):
                oid = d.get("engineering_object_id")
                if oid and oid not in objects:
                    objects.append(str(oid))
        return objects[:20]
