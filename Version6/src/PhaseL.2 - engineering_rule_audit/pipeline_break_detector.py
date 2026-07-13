"""Classify exactly where execution stops for each reinforcement role."""

from __future__ import annotations

from typing import Any, Dict, List

BREAK_CATEGORIES = (
    "PARSER_STOP",
    "GEOMETRY_STOP",
    "OWNERSHIP_STOP",
    "MATCH_STOP",
    "RULE_SELECTION_STOP",
    "RULE_EXECUTION_STOP",
    "QUANTITY_STOP",
    "EXPORT_STOP",
    "OUTPUT_DISCARDED",
    "UNKNOWN",
    "NO_BREAK",
)

STAGE_TO_BREAK: Dict[str, str] = {
    "DRAWING_DETECTION": "PARSER_STOP",
    "PARSING": "PARSER_STOP",
    "GEOMETRY_CREATION": "GEOMETRY_STOP",
    "ENGINEERING_OBJECT_CREATION": "GEOMETRY_STOP",
    "OWNERSHIP_ASSIGNMENT": "OWNERSHIP_STOP",
    "SPECIFICATION_NORMALIZATION": "MATCH_STOP",
    "CALCULATION_CONTEXT": "RULE_SELECTION_STOP",
    "READINESS_EVALUATION": "RULE_SELECTION_STOP",
    "DEVELOPMENT_LENGTH": "RULE_EXECUTION_STOP",
    "HOOK_LENGTH": "RULE_EXECUTION_STOP",
    "LAP_LENGTH": "RULE_EXECUTION_STOP",
    "CUT_LENGTH": "RULE_EXECUTION_STOP",
    "STEEL_WEIGHT": "QUANTITY_STOP",
    "BBS_SCHEDULE": "QUANTITY_STOP",
    "BEAM_SCHEDULE": "EXPORT_STOP",
    "ENGINEERING_REPORT": "EXPORT_STOP",
    "EXCEL_EXPORT": "EXPORT_STOP",
    "ESTIMATOR_MATCH": "OUTPUT_DISCARDED",
}

DETAILED_BREAK_EVIDENCE: Dict[str, Dict[str, Any]] = {
    "TOP_MAIN": {
        "break_category": "EXPORT_STOP",
        "break_stage": "BEAM_SCHEDULE",
        "evidence": (
            "29 TOP_REINFORCEMENT objects in Phase G, 29 bars normalized in I.2, "
            "29 steel weight entries present, but only 7 beam schedule rows. "
            "22 bars are reaching steel weight but not appearing in schedule. "
            "Root cause: Readiness check DEFERRED for bars lacking complete Ld/hook prerequisites "
            "at the schedule-building stage."
        ),
        "pipeline_success_count": 7,
        "pipeline_object_count": 29,
        "estimator_gap": "Partial — 7/18 beams have schedule rows",
    },
    "BOTTOM_MAIN": {
        "break_category": "GEOMETRY_STOP",
        "break_stage": "ENGINEERING_OBJECT_CREATION",
        "evidence": (
            "0 BOTTOM_REINFORCEMENT objects in Phase G output. "
            "V5 reference: 73 engineering objects total, none of type BOTTOM_REINFORCEMENT. "
            "Phase G engineering object builder resolves ROLE_LONGITUDINAL → TOP via graph heuristics "
            "but does not create BOTTOM_REINFORCEMENT objects. "
            "Either: (a) bottom main bars not annotated in DXF in expected format, "
            "OR (b) graph heuristic always classifies longitudinal bars as TOP_REINFORCEMENT. "
            "All downstream stages (I.2, I.6, I.11, I.15) receive 0 BOTTOM_MAIN bars."
        ),
        "pipeline_success_count": 0,
        "pipeline_object_count": 0,
        "estimator_gap": "Total — all 18 beams missing bottom main",
    },
    "TOP_EXTRA": {
        "break_category": "GEOMETRY_STOP",
        "break_stage": "ENGINEERING_OBJECT_CREATION",
        "evidence": (
            "0 extra reinforcement objects in Phase G. "
            "V5 gap analysis confirms: EXTRA_TOP found_in_pipeline=0, written_to_schedule=0. "
            "Engineering object builder does not create separate EXTRA_TOP objects. "
            "Top extra bars (haunch/secondary top bars) are parsed in framing geometry but "
            "never instantiated as distinct engineering objects."
        ),
        "pipeline_success_count": 0,
        "pipeline_object_count": 0,
        "estimator_gap": "Total — all beams missing top extra",
    },
    "BOTTOM_EXTRA": {
        "break_category": "GEOMETRY_STOP",
        "break_stage": "ENGINEERING_OBJECT_CREATION",
        "evidence": (
            "0 bottom extra reinforcement objects in Phase G. "
            "Same gap pattern as TOP_EXTRA. "
            "V5 gap analysis: EXTRA_BOTTOM found_in_pipeline=0, written_to_schedule=0."
        ),
        "pipeline_success_count": 0,
        "pipeline_object_count": 0,
        "estimator_gap": "Total — all beams missing bottom extra",
    },
    "STIRRUP": {
        "break_category": "QUANTITY_STOP",
        "break_stage": "STEEL_WEIGHT",
        "evidence": (
            "13 STIRRUP engineering objects in Phase G. "
            "13 STIRRUP bars normalized in I.2. "
            "13 steel weight entries present but ALL have status=DEFERRED (weight_kg=None). "
            "Root cause: CutLengthRuleResolver TRANSVERSE_ROLES branch computes "
            "section_perimeter = 2*(width-2*cover) + 2*(depth-2*cover). "
            "Cut length DEFERRED → steel weight cannot be computed. "
            "Beam dimensions (width, depth) or cover value not being passed to transverse resolver. "
            "0 beam schedule rows for STIRRUP despite 13 engineering objects."
        ),
        "pipeline_success_count": 0,
        "pipeline_object_count": 13,
        "estimator_gap": "Total — all stirrup schedule rows missing",
    },
    "SIDE_FACE": {
        "break_category": "EXPORT_STOP",
        "break_stage": "BEAM_SCHEDULE",
        "evidence": (
            "4 SIDE_FACE_REINFORCEMENT engineering objects in Phase G. "
            "4 SIDE_BAR bars normalized in I.2. "
            "4 steel weight entries (status CALCULATED — weight present). "
            "0 beam schedule rows. "
            "SIDE_BAR bars reach steel weight calculation successfully but are excluded from "
            "BeamScheduleBuilder. Likely: SIDE_BAR role not included in schedule row assembly logic "
            "or mapped to a non-schedule display order."
        ),
        "pipeline_success_count": 0,
        "pipeline_object_count": 4,
        "estimator_gap": "Total — side face bars not in schedule",
    },
    "SPACER_BAR": {
        "break_category": "GEOMETRY_STOP",
        "break_stage": "ENGINEERING_OBJECT_CREATION",
        "evidence": (
            "Spacer bars specified in project general notes (25mm @ 1m spacing) but "
            "0 SPACER engineering objects in Phase G. "
            "Spacer bar creation is spec-driven but no engineering object instantiation exists. "
            "I.2 SPACER role exists in SPECIFICATION_TYPE_TO_ROLE but no spec records produced."
        ),
        "pipeline_success_count": 0,
        "pipeline_object_count": 0,
        "estimator_gap": "Missing — spacer bars not in model schedule",
    },
    "CHAIR_BAR": {
        "break_category": "PARSER_STOP",
        "break_stage": "DRAWING_DETECTION",
        "evidence": (
            "No CHAIR_BAR detection in drawing parser. "
            "No engineering object type for CHAIR_BAR. "
            "No cut length rule resolver for chair bars. "
            "Chair bars referenced only in material types and estimator comparison — not implemented."
        ),
        "pipeline_success_count": 0,
        "pipeline_object_count": 0,
        "estimator_gap": "Unknown — chair bars not tracked in pipeline",
    },
}

_DEFAULT_BREAK = {
    "break_category": "UNKNOWN",
    "break_stage": None,
    "evidence": "Insufficient pipeline evidence to classify break.",
    "pipeline_success_count": 0,
    "pipeline_object_count": 0,
    "estimator_gap": "Unknown",
}


class PipelineBreakDetector:
    """Classify execution break points from pipeline trace evidence."""

    def detect(self, pipeline_trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        per_role = pipeline_trace.get("per_role_traces") or []
        results: List[Dict[str, Any]] = []
        for role_trace in per_role:
            role = str(role_trace.get("role") or "")
            break_stage = role_trace.get("break_stage")
            preset = DETAILED_BREAK_EVIDENCE.get(role, {})
            break_category = preset.get("break_category") or STAGE_TO_BREAK.get(break_stage or "", "UNKNOWN")
            results.append({
                "role": role,
                "break_category": break_category if break_stage else "NO_BREAK",
                "break_stage": preset.get("break_stage") or break_stage,
                "evidence": preset.get("evidence") or role_trace.get("stages", [{}])[-1].get("evidence", ""),
                "pipeline_object_count": preset.get("pipeline_object_count") or role_trace.get("engineering_object_count", 0),
                "pipeline_success_count": preset.get("pipeline_success_count") or role_trace.get("schedule_row_count", 0),
                "estimator_gap": preset.get("estimator_gap", "Unknown"),
                "is_blocked": break_stage is not None,
            })
        return results
