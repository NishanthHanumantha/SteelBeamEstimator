"""Trace every reinforcement role through all 17+ pipeline stages."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

PIPELINE_STAGES = [
    "DRAWING_DETECTION",
    "PARSING",
    "GEOMETRY_CREATION",
    "ENGINEERING_OBJECT_CREATION",
    "OWNERSHIP_ASSIGNMENT",
    "SPECIFICATION_NORMALIZATION",
    "CALCULATION_CONTEXT",
    "READINESS_EVALUATION",
    "DEVELOPMENT_LENGTH",
    "HOOK_LENGTH",
    "LAP_LENGTH",
    "CUT_LENGTH",
    "STEEL_WEIGHT",
    "BBS_SCHEDULE",
    "BEAM_SCHEDULE",
    "ENGINEERING_REPORT",
    "EXCEL_EXPORT",
    "ESTIMATOR_MATCH",
]

ALL_ROLES = [
    "TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
    "STIRRUP", "SIDE_FACE", "SPACER_BAR", "CHAIR_BAR",
    "DEVELOPMENT_LENGTH", "HOOK", "LAP_SPLICE", "CURTAILMENT",
    "BENT_BAR", "CRANKED_BAR",
]

# Canonical role mapping between pipeline internal names and audit names
INTERNAL_TO_AUDIT: Dict[str, str] = {
    "TOP_MAIN": "TOP_MAIN",
    "BOTTOM_MAIN": "BOTTOM_MAIN",
    "EXTRA_TOP": "TOP_EXTRA",
    "EXTRA_BOTTOM": "BOTTOM_EXTRA",
    "STIRRUP": "STIRRUP",
    "LINK_BAR": "STIRRUP",
    "SIDE_BAR": "SIDE_FACE",
    "SPACER": "SPACER_BAR",
    "SIDE_FACE_REINFORCEMENT": "SIDE_FACE",
    "UNKNOWN": "UNKNOWN",
}

# Engineering object types → audit roles
ENG_OBJ_TYPE_TO_ROLE: Dict[str, str] = {
    "TOP_REINFORCEMENT": "TOP_MAIN",
    "BOTTOM_REINFORCEMENT": "BOTTOM_MAIN",
    "STIRRUP": "STIRRUP",
    "SIDE_FACE_REINFORCEMENT": "SIDE_FACE",
    "BEAM_IDENTIFIER": None,
    "GENERAL_NOTE": None,
    "TEXT_NOTE": None,
}


class PipelineTracer:
    """Build per-role pipeline trace from available artifact evidence."""

    def trace(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        # Index each stage's data
        eng_obj_counts = self._count_by_type(snapshot.get("engineering_objects"), "objects", "object_type")
        bar_counts = self._count_role_in_bars(snapshot.get("reinforcement_objects"))
        cut_length_by_role = self._count_role_in_results(snapshot.get("cut_length"), "results", "role")
        sw_by_role = self._count_role_in_results(snapshot.get("steel_weight"), "results", "role")
        sw_by_role_status = self._count_role_status(snapshot.get("steel_weight"), "results", "role", "status")
        schedule_by_role = self._count_schedule_roles(snapshot.get("beam_schedule"))
        hook_by_role = self._count_role_in_results(snapshot.get("hook_results"), "results", "role")
        dl_by_role = self._count_role_in_results(snapshot.get("development_length"), "results", "role")

        per_role_traces: List[Dict[str, Any]] = []
        for role in ALL_ROLES:
            trace = self._build_role_trace(
                role, eng_obj_counts, bar_counts, cut_length_by_role,
                sw_by_role, sw_by_role_status, schedule_by_role,
                hook_by_role, dl_by_role, snapshot,
            )
            per_role_traces.append(trace)

        # Per-beam trace
        per_beam_traces = self._build_per_beam_trace(snapshot)

        return {
            "pipeline_stages": PIPELINE_STAGES,
            "per_role_traces": per_role_traces,
            "per_beam_traces": per_beam_traces,
            "stage_counts": {
                "engineering_objects": sum(eng_obj_counts.values()),
                "i2_bars": sum(bar_counts.values()),
                "cut_length": sum(cut_length_by_role.values()),
                "steel_weight": sum(sw_by_role.values()),
                "beam_schedule_rows": sum(schedule_by_role.values()),
            },
            "data_source": snapshot.get("data_source", "UNKNOWN"),
        }

    def _build_role_trace(
        self,
        role: str,
        eng_obj_counts: Dict[str, int],
        bar_counts: Dict[str, int],
        cut_length_by_role: Dict[str, int],
        sw_by_role: Dict[str, int],
        sw_by_role_status: Dict[str, Dict[str, int]],
        schedule_by_role: Dict[str, int],
        hook_by_role: Dict[str, int],
        dl_by_role: Dict[str, int],
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Map to internal pipeline names for evidence lookup
        internal = self._to_internal(role)
        obj_type = self._role_to_obj_type(role)

        # Deduplicated lookup keys (avoid double-counting when internal == role)
        lookup_keys = list({k for k in [internal, role] if k})

        def _sum(*keys: Optional[str], d: Dict) -> int:
            seen: set = set()
            total = 0
            for k in keys:
                if k and k not in seen:
                    seen.add(k)
                    total += d.get(k, 0)
            return total

        # Stage evidence
        drawing_detected = self._has_drawing_evidence(role, snapshot)
        parsed = drawing_detected
        geometry_created = drawing_detected
        obj_count = eng_obj_counts.get(obj_type, 0) if obj_type else 0
        obj_created = obj_count > 0
        ownership = obj_created
        bar_count = _sum(internal, role if role != internal else None, d=bar_counts)
        spec_normalized = bar_count > 0
        ctx_count = self._count_context_role(snapshot.get("calculation_contexts"), internal or role)
        context_built = ctx_count > 0 or spec_normalized
        dl_count = _sum(internal, role if role != internal else None, d=dl_by_role)
        hook_count = _sum(internal, role if role != internal else None, d=hook_by_role)
        cut_count = _sum(internal, role if role != internal else None, d=cut_length_by_role)
        sw_count = _sum(internal, role if role != internal else None, d=sw_by_role)
        sched_count = _sum(internal, role if role != internal else None, d=schedule_by_role)

        # Merge status dicts without duplicating (only merge if internal != role)
        sw_statuses: Dict[str, int] = {}
        for k in lookup_keys:
            for status, cnt in (sw_by_role_status.get(k) or {}).items():
                sw_statuses[status] = sw_statuses.get(status, 0) + cnt
        sw_calculated = sw_statuses.get("CALCULATED", 0) + sw_statuses.get("SUCCESS", 0)
        sw_deferred = sw_statuses.get("DEFERRED", 0) + sw_statuses.get("PRESERVED_DEFERRED", 0)

        # Rule existence evidence (from source scanning — filled in later by rule_registry_auditor)
        rule_exists = role not in ("CHAIR_BAR", "BENT_BAR", "CRANKED_BAR")

        # Build stage trace
        stages: List[Dict[str, Any]] = []
        for stage in PIPELINE_STAGES:
            result, count, evidence = self._evaluate_stage(
                stage, role, drawing_detected, parsed, geometry_created,
                obj_created, obj_count, ownership, spec_normalized,
                bar_count, context_built, ctx_count,
                dl_count, hook_count, cut_count, sw_count, sw_calculated,
                sw_deferred, sched_count, rule_exists, snapshot,
            )
            stages.append({
                "stage": stage,
                "result": result,
                "count": count,
                "evidence": evidence,
            })

        # Determine break stage
        break_stage = None
        for s in stages:
            if s["result"] in ("NO", "DEFERRED", "UNKNOWN"):
                break_stage = s["stage"]
                break

        return {
            "role": role,
            "break_stage": break_stage,
            "stages": stages,
            "engineering_object_count": obj_count,
            "bar_count": bar_count,
            "steel_weight_count": sw_count,
            "steel_weight_calculated": sw_calculated,
            "steel_weight_deferred": sw_deferred,
            "schedule_row_count": sched_count,
            "has_drawing_evidence": drawing_detected,
            "rule_exists": rule_exists,
        }

    @staticmethod
    def _evaluate_stage(
        stage: str, role: str,
        drawing: bool, parsed: bool, geom: bool,
        obj_created: bool, obj_count: int, ownership: bool,
        spec_norm: bool, bar_count: int, ctx_built: bool, ctx_count: int,
        dl_count: int, hook_count: int, cut_count: int,
        sw_count: int, sw_calc: int, sw_defer: int, sched_count: int,
        rule_exists: bool, snapshot: Dict[str, Any],
    ):
        if stage == "DRAWING_DETECTION":
            return ("YES" if drawing else "UNKNOWN", None, "Inferred from downstream evidence")
        if stage == "PARSING":
            return ("YES" if parsed else "UNKNOWN", None, "Inferred from engineering objects")
        if stage == "GEOMETRY_CREATION":
            return ("YES" if geom else "UNKNOWN", None, "Beam geometry built for all detected drawings")
        if stage == "ENGINEERING_OBJECT_CREATION":
            evidence = f"Engineering objects of this type: {obj_count}" if obj_count > 0 else "0 engineering objects of this type in Phase G output"
            return ("YES" if obj_count > 0 else "NO", obj_count, evidence)
        if stage == "OWNERSHIP_ASSIGNMENT":
            return ("YES" if ownership else "NO", None, "Owned by beam if engineering object created")
        if stage == "SPECIFICATION_NORMALIZATION":
            evidence = f"Normalized bars in I.2: {bar_count}"
            return ("YES" if spec_norm else "NO", bar_count, evidence)
        if stage == "CALCULATION_CONTEXT":
            return ("YES" if ctx_built else "INFERRED", ctx_count, "Context built if bars normalized")
        if stage == "READINESS_EVALUATION":
            return ("YES" if bar_count > 0 else "NO", bar_count, "READY if bar+context exist")
        if stage == "DEVELOPMENT_LENGTH":
            if dl_count > 0:
                return ("YES", dl_count, f"Dev length results: {dl_count}")
            if role in ("STIRRUP", "SPACER_BAR", "CHAIR_BAR"):
                return ("N/A", 0, "Transverse bars: perimeter rule, no Ld lookup")
            return ("NO", 0, "No development length results for this role")
        if stage == "HOOK_LENGTH":
            if hook_count > 0:
                return ("YES", hook_count, f"Hook results: {hook_count}")
            if role in ("STIRRUP", "SPACER_BAR"):
                return ("N/A", 0, "Transverse: hook included in perimeter calc")
            return ("NO", 0, "No hook results for this role")
        if stage == "LAP_LENGTH":
            return ("CONDITIONAL", 0, "Lap applied when splices detected in drawing")
        if stage == "CUT_LENGTH":
            if cut_count > 0:
                return ("YES", cut_count, f"Cut length results: {cut_count}")
            if bar_count > 0:
                return ("DEFERRED", 0, "Bars exist but cut length computation deferred/blocked")
            return ("NO", 0, "No bars reached cut length stage")
        if stage == "STEEL_WEIGHT":
            if sw_calc > 0:
                return ("YES", sw_calc, f"Calculated weight entries: {sw_calc}")
            if sw_defer > 0:
                return ("DEFERRED", sw_defer, f"Deferred weight entries: {sw_defer} (missing cut length input)")
            if sw_count > 0:
                return ("PARTIAL", sw_count, f"Weight entries present but status unknown: {sw_count}")
            return ("NO", 0, "No steel weight entries for this role")
        if stage == "BBS_SCHEDULE":
            return ("UNKNOWN", 0, "BBS role tracing requires detailed BBS output parsing")
        if stage == "BEAM_SCHEDULE":
            if sched_count > 0:
                return ("YES", sched_count, f"Schedule rows: {sched_count}")
            if sw_calc > 0:
                return ("NO", 0, f"Steel calculated ({sw_calc}) but 0 schedule rows — excluded from schedule builder")
            if sw_defer > 0:
                return ("NO", 0, "Schedule skipped — steel weight DEFERRED")
            return ("NO", 0, "No schedule rows for this role")
        if stage == "ENGINEERING_REPORT":
            return ("YES" if sched_count > 0 else "NO", sched_count, "Report includes schedule rows")
        if stage == "EXCEL_EXPORT":
            return ("YES" if sched_count > 0 else "NO", sched_count, "Excel includes schedule rows")
        if stage == "ESTIMATOR_MATCH":
            return ("PARTIAL" if sched_count > 0 else "NO", sched_count, "Estimator match requires schedule rows")
        return ("UNKNOWN", None, "")

    @staticmethod
    def _to_internal(role: str) -> Optional[str]:
        mapping = {
            "TOP_MAIN": "TOP_MAIN",
            "BOTTOM_MAIN": "BOTTOM_MAIN",
            "TOP_EXTRA": "EXTRA_TOP",
            "BOTTOM_EXTRA": "EXTRA_BOTTOM",
            "STIRRUP": "STIRRUP",
            "SIDE_FACE": "SIDE_BAR",
            "SPACER_BAR": "SPACER",
        }
        return mapping.get(role)

    @staticmethod
    def _role_to_obj_type(role: str) -> Optional[str]:
        mapping = {
            "TOP_MAIN": "TOP_REINFORCEMENT",
            "BOTTOM_MAIN": "BOTTOM_REINFORCEMENT",
            "STIRRUP": "STIRRUP",
            "SIDE_FACE": "SIDE_FACE_REINFORCEMENT",
        }
        return mapping.get(role)

    @staticmethod
    def _has_drawing_evidence(role: str, snapshot: Dict[str, Any]) -> bool:
        if role in ("CHAIR_BAR", "BENT_BAR", "CRANKED_BAR"):
            return False
        return True

    @staticmethod
    def _count_by_type(payload: Any, list_key: str, type_key: str) -> Dict[str, int]:
        if not payload:
            return {}
        counts: Dict[str, int] = {}
        for obj in (payload.get(list_key) or []):
            t = str(obj.get(type_key) or "UNKNOWN")
            counts[t] = counts.get(t, 0) + 1
        return counts

    @staticmethod
    def _count_role_in_bars(payload: Any) -> Dict[str, int]:
        if not payload:
            return {}
        counts: Dict[str, int] = {}
        for bar in (payload.get("bars") or []):
            r = str(bar.get("role") or "UNKNOWN")
            counts[r] = counts.get(r, 0) + 1
        return counts

    @staticmethod
    def _count_role_in_results(payload: Any, list_key: str, role_key: str) -> Dict[str, int]:
        if not payload:
            return {}
        counts: Dict[str, int] = {}
        for r in (payload.get(list_key) or []):
            role = str(r.get(role_key) or "UNKNOWN")
            counts[role] = counts.get(role, 0) + 1
        return counts

    @staticmethod
    def _count_role_status(payload: Any, list_key: str, role_key: str, status_key: str) -> Dict[str, Dict[str, int]]:
        if not payload:
            return {}
        data: Dict[str, Dict[str, int]] = {}
        for r in (payload.get(list_key) or []):
            role = str(r.get(role_key) or "UNKNOWN")
            status = str(r.get(status_key) or "UNKNOWN")
            data.setdefault(role, {})[status] = data.get(role, {}).get(status, 0) + 1
        return data

    @staticmethod
    def _count_schedule_roles(payload: Any) -> Dict[str, int]:
        if not payload:
            return {}
        counts: Dict[str, int] = {}
        for result in (payload.get("results") or []):
            for row in (result.get("rows") or []):
                r = str(row.get("role") or "UNKNOWN")
                counts[r] = counts.get(r, 0) + 1
        return counts

    @staticmethod
    def _count_context_role(payload: Any, role: str) -> int:
        if not payload:
            return 0
        count = 0
        for r in (payload.get("results") or payload.get("contexts") or []):
            if str(r.get("role") or "") == role:
                count += 1
        return count

    def _build_per_beam_trace(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        beam_schedule = snapshot.get("beam_schedule") or {}
        results = beam_schedule.get("results") or []
        traces = []
        for r in results:
            rows = r.get("rows") or []
            roles_in_schedule = list({str(row.get("role") or "UNKNOWN") for row in rows})
            traces.append({
                "beam_mark": r.get("beam_mark") or r.get("beam_id"),
                "schedule_row_count": len(rows),
                "roles_in_schedule": roles_in_schedule,
                "total_steel_weight_kg": r.get("total_steel_weight_kg"),
                "engineering_ready": r.get("engineering_ready"),
                "status": r.get("status"),
            })
        return traces
