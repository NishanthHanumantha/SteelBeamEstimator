"""Build dependency graph for every reinforcement role."""

from __future__ import annotations

from typing import Any, Dict, List

DEPENDENCY_GRAPH: Dict[str, List[Dict[str, Any]]] = {
    "TOP_MAIN": [
        {"dependency": "DRAWING_DETECTION", "satisfied": True, "phase": "B/C/D"},
        {"dependency": "GEOMETRY_CREATION", "satisfied": True, "phase": "F"},
        {"dependency": "ENGINEERING_OBJECT_CREATION (TOP_REINFORCEMENT)", "satisfied": True, "phase": "G.5.1"},
        {"dependency": "SPECIFICATION_NORMALIZATION (TOP_MAIN role)", "satisfied": True, "phase": "I.2"},
        {"dependency": "CALCULATION_CONTEXT (steel grade, concrete grade, span)", "satisfied": True, "phase": "I.1"},
        {"dependency": "DEVELOPMENT_LENGTH (Ld lookup)", "satisfied": "PARTIAL", "phase": "I.3"},
        {"dependency": "HOOK_LENGTH (hook multiplier)", "satisfied": "PARTIAL", "phase": "I.4"},
        {"dependency": "CUT_LENGTH (clear span + 2*Ld + 2*hook)", "satisfied": "PARTIAL", "phase": "I.6"},
        {"dependency": "STEEL_WEIGHT (density * volume)", "satisfied": "PARTIAL", "phase": "I.11"},
        {"dependency": "BEAM_SCHEDULE_ASSEMBLY", "satisfied": "PARTIAL", "phase": "I.15"},
    ],
    "BOTTOM_MAIN": [
        {"dependency": "DRAWING_DETECTION", "satisfied": True, "phase": "B/C/D"},
        {"dependency": "GEOMETRY_CREATION", "satisfied": True, "phase": "F"},
        {"dependency": "ENGINEERING_OBJECT_CREATION (BOTTOM_REINFORCEMENT)", "satisfied": False, "phase": "G.5.1",
         "missing": "Phase G engineering_object_builder never produces BOTTOM_REINFORCEMENT type"},
        {"dependency": "SPECIFICATION_NORMALIZATION (BOTTOM_MAIN role)", "satisfied": False, "phase": "I.2",
         "missing": "No BOTTOM_REINFORCEMENT objects to normalize"},
        {"dependency": "CALCULATION_CONTEXT", "satisfied": False, "phase": "I.1"},
        {"dependency": "DEVELOPMENT_LENGTH", "satisfied": False, "phase": "I.3"},
        {"dependency": "CUT_LENGTH rule (MAIN_TENSION_CUT_LENGTH)", "satisfied": False, "phase": "I.6",
         "note": "Rule exists in CutLengthRuleResolver but unreachable"},
        {"dependency": "STEEL_WEIGHT", "satisfied": False, "phase": "I.11"},
        {"dependency": "BEAM_SCHEDULE_ASSEMBLY", "satisfied": False, "phase": "I.15"},
    ],
    "TOP_EXTRA": [
        {"dependency": "DRAWING_DETECTION", "satisfied": True, "phase": "B/C/D"},
        {"dependency": "GEOMETRY_CREATION", "satisfied": True, "phase": "F"},
        {"dependency": "ENGINEERING_OBJECT_CREATION (EXTRA_TOP)", "satisfied": False, "phase": "G.5.1",
         "missing": "Phase G does not create EXTRA_TOP engineering objects"},
        {"dependency": "SPECIFICATION_NORMALIZATION (EXTRA_TOP role)", "satisfied": False, "phase": "I.2"},
        {"dependency": "CUT_LENGTH rule (MAIN_TENSION branch)", "satisfied": False, "phase": "I.6",
         "note": "Rule exists but unreachable — EXTRA_TOP excluded from K.1 MAIN_BAR_TYPES"},
        {"dependency": "STEEL_WEIGHT", "satisfied": False, "phase": "I.11"},
        {"dependency": "BEAM_SCHEDULE_ASSEMBLY", "satisfied": False, "phase": "I.15"},
    ],
    "STIRRUP": [
        {"dependency": "DRAWING_DETECTION", "satisfied": True, "phase": "B/C/D"},
        {"dependency": "GEOMETRY_CREATION", "satisfied": True, "phase": "F"},
        {"dependency": "ENGINEERING_OBJECT_CREATION (STIRRUP)", "satisfied": True, "phase": "G.5.1"},
        {"dependency": "SPECIFICATION_NORMALIZATION (STIRRUP role)", "satisfied": True, "phase": "I.2"},
        {"dependency": "CALCULATION_CONTEXT (beam section: width, depth, cover)", "satisfied": "PARTIAL", "phase": "I.1",
         "missing": "Beam section dimensions (width/depth) not consistently populated in context"},
        {"dependency": "CUT_LENGTH TRANSVERSE rule (section perimeter)", "satisfied": "PARTIAL", "phase": "I.6",
         "missing": "Section perimeter = 2*(width-2*cover)+2*(depth-2*cover) DEFERRED — beam dimensions missing"},
        {"dependency": "STEEL_WEIGHT", "satisfied": "DEFERRED", "phase": "I.11",
         "missing": "DEFERRED because cut_length_mm not computed"},
        {"dependency": "BEAM_SCHEDULE_ASSEMBLY", "satisfied": False, "phase": "I.15",
         "missing": "Cannot schedule bars with DEFERRED steel weight"},
    ],
    "SIDE_FACE": [
        {"dependency": "DRAWING_DETECTION", "satisfied": True, "phase": "B/C/D"},
        {"dependency": "ENGINEERING_OBJECT_CREATION (SIDE_FACE_REINFORCEMENT)", "satisfied": True, "phase": "G.5.1"},
        {"dependency": "SPECIFICATION_NORMALIZATION (SIDE_BAR role)", "satisfied": True, "phase": "I.2"},
        {"dependency": "CALCULATION_CONTEXT", "satisfied": True, "phase": "I.1"},
        {"dependency": "CUT_LENGTH rule (MAIN_TENSION_CUT_LENGTH for SIDE_BAR)", "satisfied": True, "phase": "I.6"},
        {"dependency": "STEEL_WEIGHT (CALCULATED)", "satisfied": True, "phase": "I.11"},
        {"dependency": "BEAM_SCHEDULE_ASSEMBLY inclusion for SIDE_BAR", "satisfied": False, "phase": "I.15",
         "missing": "BeamScheduleBuilder does not include SIDE_BAR role in schedule rows"},
    ],
    "SPACER_BAR": [
        {"dependency": "SPEC_DRIVEN_CREATION (from Phase H general notes)", "satisfied": False, "phase": "H",
         "missing": "No engineering object instantiation for spacer bars from spec"},
        {"dependency": "ENGINEERING_OBJECT_CREATION (SPACER type)", "satisfied": False, "phase": "G",
         "missing": "No spacer bar engineering objects"},
        {"dependency": "SPECIFICATION_NORMALIZATION (SPACER role)", "satisfied": False, "phase": "I.2"},
        {"dependency": "CUT_LENGTH TRANSVERSE rule (SPACER in TRANSVERSE_ROLES)", "satisfied": False, "phase": "I.6",
         "note": "Rule available but unreachable — no bars of SPACER role produced"},
    ],
    "CHAIR_BAR": [
        {"dependency": "DRAWING_DETECTION", "satisfied": False, "phase": "B/C/D",
         "missing": "No parser detection for chair bars"},
        {"dependency": "ENGINEERING_OBJECT_CREATION", "satisfied": False, "phase": "G"},
        {"dependency": "CUT_LENGTH rule", "satisfied": False, "phase": "I.6",
         "missing": "No chair bar rule implemented"},
    ],
}


class DependencyMapper:
    """Build and report dependency graph for every engineering role."""

    def build(
        self,
        status_classifications: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        dependency_entries: List[Dict[str, Any]] = []
        for sc in status_classifications:
            role = str(sc.get("role") or "")
            deps = DEPENDENCY_GRAPH.get(role, [
                {"dependency": f"Pipeline trace for {role}", "satisfied": "UNKNOWN", "phase": "Unknown"}
            ])
            satisfied = sum(1 for d in deps if d.get("satisfied") is True)
            missing = [d for d in deps if d.get("satisfied") is False]
            dependency_entries.append({
                "role": role,
                "implementation_status": sc.get("implementation_status"),
                "total_dependencies": len(deps),
                "satisfied_dependencies": satisfied,
                "missing_dependencies": len(missing),
                "first_missing_dependency": missing[0].get("dependency") if missing else None,
                "first_missing_phase": missing[0].get("phase") if missing else None,
                "dependencies": deps,
            })
        return {
            "role_count": len(dependency_entries),
            "entries": dependency_entries,
        }
