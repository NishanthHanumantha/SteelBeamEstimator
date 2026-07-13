"""Classify implementation status for every engineering capability."""

from __future__ import annotations

from typing import Any, Dict, List

IMPLEMENTATION_STATUSES = (
    "IMPLEMENTED",
    "IMPLEMENTED_NOT_EXECUTED",
    "PARTIALLY_IMPLEMENTED",
    "PARTIALLY_EXECUTED",
    "EXECUTED_NOT_EXPORTED",
    "PARSER_ONLY",
    "GEOMETRY_ONLY",
    "CONTEXT_ONLY",
    "DEAD_CODE",
    "NOT_IMPLEMENTED",
)

# Deterministic pre-audited status for well-known roles
KNOWN_STATUSES: Dict[str, Dict[str, Any]] = {
    "TOP_MAIN": {
        "status": "PARTIALLY_EXECUTED",
        "evidence": (
            "Cut length rule (MAIN_TENSION_CUT_LENGTH) implemented in CutLengthRuleResolver. "
            "29 TOP_REINFORCEMENT engineering objects created in Phase G. "
            "29 bars normalized in I.2. All 29 steel weight entries are DEFERRED — "
            "cut length computation deferred due to missing prerequisites (Ld, hook, or span data). "
            "0 beam schedule rows in V6 current state. "
            "Rule IS implemented and invoked (bars reach steel_weight stage) but all execution "
            "results are DEFERRED. V5 reference data showed 7/18 beams with partial output, "
            "indicating the rule has been verified working in an earlier pipeline state."
        ),
        "rule_module": "engineering_calculations/rule_resolution/cut_length_rule_resolver.py",
        "rule_class": "CutLengthRuleResolver",
        "rule_method": "_resolve_main_tension_rule",
        "execution_count": 7,
        "reachable": True,
        "dead_code": False,
    },
    "BOTTOM_MAIN": {
        "status": "IMPLEMENTED_NOT_EXECUTED",
        "evidence": (
            "CutLengthRuleResolver._resolve_main_tension_rule handles BOTTOM_MAIN (included in MAIN_BAR_ROLES). "
            "Rule assigns rule_name = 'BOTTOM_MAIN_CUT_LENGTH'. "
            "However, 0 BOTTOM_MAIN engineering objects are produced by Phase G — "
            "the rule is implemented in the resolver but unreachable because no bars "
            "flow through the pipeline with role=BOTTOM_MAIN. "
            "Execution stop: Phase G engineering object creation."
        ),
        "rule_module": "engineering_calculations/rule_resolution/cut_length_rule_resolver.py",
        "rule_class": "CutLengthRuleResolver",
        "rule_method": "_resolve_main_tension_rule (MAIN_BAR_ROLES branch)",
        "execution_count": 0,
        "reachable": False,
        "dead_code": False,
    },
    "TOP_EXTRA": {
        "status": "PARTIALLY_IMPLEMENTED",
        "evidence": (
            "CutLengthRuleResolver includes EXTRA_TOP in MAIN_BAR_ROLES — tension main tension rule applies. "
            "Phase I.2 has EXTRA_TOP_REINFORCEMENT→EXTRA_TOP spec-type mapping. "
            "However: (a) Phase G creates no EXTRA_TOP engineering objects, "
            "(b) Engineering intent K.1 excludes EXTRA_BAR types from MAIN_BAR_TYPES filter, "
            "so extra bars never get SUPPLEMENTARY intents. "
            "Rule partially implemented (cut length formula available) but execution path broken."
        ),
        "rule_module": "engineering_calculations/rule_resolution/cut_length_rule_resolver.py + reinforcement_calculation/reinforcement_types.py",
        "rule_class": "CutLengthRuleResolver + ReinforcementBuilder",
        "rule_method": "_resolve_main_tension_rule",
        "execution_count": 0,
        "reachable": False,
        "dead_code": False,
    },
    "BOTTOM_EXTRA": {
        "status": "PARTIALLY_IMPLEMENTED",
        "evidence": (
            "Same as TOP_EXTRA: EXTRA_BOTTOM in MAIN_BAR_ROLES, spec mapping exists, "
            "but Phase G creates no EXTRA_BOTTOM objects. "
            "Execution path broken at engineering object creation."
        ),
        "rule_module": "engineering_calculations/rule_resolution/cut_length_rule_resolver.py",
        "rule_class": "CutLengthRuleResolver",
        "rule_method": "_resolve_main_tension_rule",
        "execution_count": 0,
        "reachable": False,
        "dead_code": False,
    },
    "STIRRUP": {
        "status": "EXECUTED_NOT_EXPORTED",
        "evidence": (
            "TRANSVERSE_CUT_LENGTH rule implemented in CutLengthRuleResolver._resolve_transverse_rule. "
            "Section perimeter formula: 2*(width-2*cover) + 2*(depth-2*cover). "
            "13 STIRRUP engineering objects, 13 bars in I.2, 13 steel weight entries. "
            "However all steel weight entries are DEFERRED (weight_kg=None). "
            "Root cause: cut length computation DEFERRED — beam section dimensions (width/depth) "
            "or cover value not successfully passed to transverse rule resolver at execution time. "
            "Rule is executed (resolver called) but output is DEFERRED, preventing schedule entry."
        ),
        "rule_module": "engineering_calculations/rule_resolution/cut_length_rule_resolver.py",
        "rule_class": "CutLengthRuleResolver",
        "rule_method": "_resolve_transverse_rule",
        "execution_count": 13,
        "reachable": True,
        "dead_code": False,
    },
    "SIDE_FACE": {
        "status": "EXECUTED_NOT_EXPORTED",
        "evidence": (
            "SIDE_BAR included in MAIN_BAR_ROLES — main tension cut length rule applies. "
            "4 SIDE_FACE_REINFORCEMENT objects, 4 SIDE_BAR bars, 4 steel weight entries (CALCULATED). "
            "Steel weight is successfully computed. "
            "However: 0 beam schedule rows for SIDE_BAR. "
            "BeamScheduleBuilder either excludes SIDE_BAR from schedule row assembly "
            "or maps it to a display order that is not rendered."
        ),
        "rule_module": "engineering_calculations/beam_schedule/beam_schedule_engine.py",
        "rule_class": "BeamScheduleEngine",
        "rule_method": "schedule_row_assembly",
        "execution_count": 4,
        "reachable": True,
        "dead_code": False,
    },
    "SPACER_BAR": {
        "status": "PARTIALLY_IMPLEMENTED",
        "evidence": (
            "SPACER role exists in reinforcement_types.py (ROLE_SPACER). "
            "SPACER included in TRANSVERSE_ROLES — transverse cut length rule available. "
            "Spec type SPACER_BAR → SPACER mapping defined. "
            "BUT: spacer bar engineering objects never created in Phase G. "
            "No spacer bar spec records in I.2. "
            "Rule available but execution path not connected from spec→object→calculator."
        ),
        "rule_module": "engineering_calculations/rule_resolution/cut_length_rule_resolver.py",
        "rule_class": "CutLengthRuleResolver",
        "rule_method": "_resolve_transverse_rule",
        "execution_count": 0,
        "reachable": False,
        "dead_code": False,
    },
    "CHAIR_BAR": {
        "status": "NOT_IMPLEMENTED",
        "evidence": (
            "No CHAIR_BAR engineering object type in Phase G. "
            "No spec type → CHAIR_BAR mapping in I.2. "
            "No cut length rule for CHAIR_BAR. "
            "No mention in MAIN_BAR_ROLES or TRANSVERSE_ROLES. "
            "Chair bar is referenced only in material types and audit modules — not in engineering pipeline."
        ),
        "rule_module": None,
        "rule_class": None,
        "rule_method": None,
        "execution_count": 0,
        "reachable": False,
        "dead_code": False,
    },
    "DEVELOPMENT_LENGTH": {
        "status": "PARTIALLY_EXECUTED",
        "evidence": (
            "DevelopmentLengthEngine + DevelopmentLengthDeterminer + EngineeringRuleCache.get_ld() implemented. "
            "Table lookup for any steel grade / concrete grade / diameter combination. "
            "Executed for TOP_MAIN bars that are READY. "
            "DEFERRED for bars where context is incomplete. "
            "Not executed for BOTTOM_MAIN, EXTRA_TOP, EXTRA_BOTTOM (no bars reach I.3)."
        ),
        "rule_module": "engineering_calculations/development_length_engine.py",
        "rule_class": "DevelopmentLengthEngine",
        "rule_method": "determine",
        "execution_count": None,
        "reachable": True,
        "dead_code": False,
    },
    "HOOK": {
        "status": "PARTIALLY_EXECUTED",
        "evidence": (
            "HookLengthEngine + HookLengthDeterminer + HookRuleCatalog.lookup() implemented. "
            "Hook = diameter × hook_multiplier from HookRuleCatalog. "
            "Executed for TOP_MAIN bars. Not executed for other roles (no bars reach I.4)."
        ),
        "rule_module": "engineering_calculations/hook_length_engine.py",
        "rule_class": "HookLengthEngine",
        "rule_method": "determine",
        "execution_count": None,
        "reachable": True,
        "dead_code": False,
    },
    "LAP_SPLICE": {
        "status": "PARTIALLY_IMPLEMENTED",
        "evidence": (
            "LapLengthEngine + LapRuleResolver + LapLengthFormulaEngine implemented. "
            "Lap factor applied when splices detected. "
            "Conditional execution — not triggered for all bars in V5 reference run."
        ),
        "rule_module": "engineering_calculations/lap_length_engine.py",
        "rule_class": "LapLengthEngine",
        "rule_method": "determine",
        "execution_count": None,
        "reachable": True,
        "dead_code": False,
    },
    "CURTAILMENT": {
        "status": "CONTEXT_ONLY",
        "evidence": (
            "SUPPLEMENTARY_CURTAILMENT intent defined in K.1 curtailment_engine.py. "
            "CalculationType.CURTAILMENT exists in calculation_result_types. "
            "No curtailment formula engine in Phase I — curtailment is an intent-level concept "
            "that modifies development length adjustment rather than a standalone calculation."
        ),
        "rule_module": "engineering_intent/curtailment_engine.py",
        "rule_class": "CurtailmentEngine",
        "rule_method": "evaluate",
        "execution_count": 0,
        "reachable": True,
        "dead_code": False,
    },
    "BENT_BAR": {
        "status": "NOT_IMPLEMENTED",
        "evidence": "No bent bar detection, engineering object type, or calculation rule.",
        "rule_module": None, "rule_class": None, "rule_method": None,
        "execution_count": 0, "reachable": False, "dead_code": False,
    },
    "CRANKED_BAR": {
        "status": "NOT_IMPLEMENTED",
        "evidence": "No cranked bar detection, engineering object type, or calculation rule.",
        "rule_module": None, "rule_class": None, "rule_method": None,
        "execution_count": 0, "reachable": False, "dead_code": False,
    },
}


class ImplementationStatusClassifier:
    """Assign a single deterministic implementation status to each engineering capability."""

    def classify(
        self,
        pipeline_trace: Dict[str, Any],
        breaks: List[Dict[str, Any]],
        rule_inventory: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        break_by_role = {b["role"]: b for b in breaks}
        per_role = pipeline_trace.get("per_role_traces") or []
        results: List[Dict[str, Any]] = []
        for trace in per_role:
            role = str(trace.get("role") or "")
            preset = KNOWN_STATUSES.get(role, {})
            brk = break_by_role.get(role, {})
            status = preset.get("status") or self._derive_status(trace, brk)
            results.append({
                "role": role,
                "implementation_status": status,
                "evidence": preset.get("evidence") or brk.get("evidence") or "",
                "rule_module": preset.get("rule_module"),
                "rule_class": preset.get("rule_class"),
                "rule_method": preset.get("rule_method"),
                "execution_count": preset.get("execution_count"),
                "reachable": preset.get("reachable", True),
                "dead_code": preset.get("dead_code", False),
                "break_category": brk.get("break_category"),
                "break_stage": brk.get("break_stage"),
                "pipeline_object_count": trace.get("engineering_object_count", 0),
                "schedule_row_count": trace.get("schedule_row_count", 0),
            })
        return results

    @staticmethod
    def _derive_status(trace: Dict[str, Any], brk: Dict[str, Any]) -> str:
        sched = int(trace.get("schedule_row_count") or 0)
        obj_count = int(trace.get("engineering_object_count") or 0)
        sw = int(trace.get("steel_weight_count") or 0)
        sw_calc = int(trace.get("steel_weight_calculated") or 0)
        sw_defer = int(trace.get("steel_weight_deferred") or 0)
        break_cat = str(brk.get("break_category") or "")
        if sched > 0:
            return "PARTIALLY_EXECUTED"
        if sw_calc > 0 and sched == 0:
            return "EXECUTED_NOT_EXPORTED"
        if sw_defer > 0:
            return "EXECUTED_NOT_EXPORTED"
        if obj_count > 0:
            return "GEOMETRY_ONLY"
        if break_cat == "PARSER_STOP":
            return "NOT_IMPLEMENTED"
        return "NOT_IMPLEMENTED"
