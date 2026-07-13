"""Compare estimator ground-truth against current Version6 model outputs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


ROLE_CANONICAL: Dict[str, str] = {
    "top main": "TOP_MAIN", "top": "TOP_MAIN",
    "bottom main": "BOTTOM_MAIN", "bottom": "BOTTOM_MAIN",
    "top extra": "TOP_EXTRA", "top additional": "TOP_EXTRA",
    "bottom extra": "BOTTOM_EXTRA", "bottom additional": "BOTTOM_EXTRA",
    "stirrup": "STIRRUP", "link": "STIRRUP", "shear": "STIRRUP",
    "side face": "SIDE_FACE", "side": "SIDE_FACE", "mid": "SIDE_FACE",
    "spacer": "SPACER_BAR", "chair": "CHAIR_BAR",
    "supplementary": "SUPPLEMENTARY_BAR",
}

DECISION_CATEGORY_TO_ROLE: Dict[str, str] = {
    "SUPPLEMENTARY_DEVELOPMENT_LENGTH": "TOP_MAIN",
    "SUPPLEMENTARY_ANCHORAGE": "TOP_MAIN",
    "SUPPLEMENTARY_HOOK": "TOP_MAIN",
    "SUPPLEMENTARY_CONTINUATION": "TOP_MAIN",
    "SUPPLEMENTARY_SUPPORT_BAR": "TOP_MAIN",
    "SUPPLEMENTARY_TERMINATION": "TOP_MAIN",
    "SUPPLEMENTARY_CURTAILMENT": "TOP_MAIN",
    "SUPPLEMENTARY_REINFORCEMENT": "TOP_MAIN",
    "SUPPORT_REINFORCEMENT": "BOTTOM_MAIN",
    "CONTINUOUS_SUPPORT_REINFORCEMENT": "BOTTOM_MAIN",
}


def _canon_role(hint: str) -> str:
    h = (hint or "").lower().strip()
    for key, val in ROLE_CANONICAL.items():
        if key in h:
            return val
    return "UNKNOWN"


class EstimatorComparator:
    """Compare estimator schedule vs model for every beam, role and diameter."""

    def compare(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        estimator = snapshot.get("estimator_data") or {}
        beam_blocks = estimator.get("beam_blocks") or {}
        decisions = snapshot.get("decisions") or []
        decisions_by_beam = snapshot.get("decisions_by_beam") or {}
        payloads = snapshot.get("payloads") or {}
        artifact_presence = snapshot.get("artifact_presence") or {}

        # Build model row coverage from available outputs
        model_schedule = self._build_model_schedule(payloads, decisions_by_beam)
        v5_base = payloads.get("v5_accuracy_stats") or {}
        v5_comp = payloads.get("v5_comparison_stats") or {}
        v5_beam = payloads.get("v5_beam_comparison") or {}

        per_beam: List[Dict[str, Any]] = []
        total_est_rows = 0
        total_model_rows = 0
        total_est_weight = 0.0
        total_model_weight = 0.0
        all_est_beams = set(beam_blocks.keys())
        all_model_beams = set(decisions_by_beam.keys()) | set(model_schedule.keys())

        for beam_mark, block in sorted(beam_blocks.items()):
            est_rows = block.get("row_count", 0)
            est_weight = block.get("total_steel_weight_kg", 0.0)
            est_diams = set(block.get("diameters_mm") or [])
            est_roles = {_canon_role(r) for r in (block.get("roles") or [])}
            beam_decisions = decisions_by_beam.get(beam_mark, [])
            model_rows_data = model_schedule.get(beam_mark, {})
            model_rows = model_rows_data.get("row_count", 0) if model_rows_data else 0
            model_weight = model_rows_data.get("steel_weight_kg", 0.0) if model_rows_data else 0.0
            model_roles = {
                DECISION_CATEGORY_TO_ROLE.get(str(d.get("decision_category") or ""), "UNKNOWN")
                for d in beam_decisions
            }
            # Use V5 reference when V6 calculation outputs absent
            v5_beam_data = _beam_v5(v5_beam, beam_mark)
            per_beam.append({
                "beam_mark": beam_mark,
                "estimator_rows": est_rows,
                "model_rows": model_rows,
                "missing_rows": max(0, est_rows - model_rows),
                "extra_rows": max(0, model_rows - est_rows),
                "row_coverage_percent": round(100 * model_rows / max(est_rows, 1), 2),
                "estimator_weight_kg": est_weight,
                "model_weight_kg": round(model_weight, 3),
                "weight_difference_kg": round(est_weight - model_weight, 3),
                "weight_coverage_percent": round(100 * model_weight / max(est_weight, 0.001), 2),
                "estimator_diameters": sorted(est_diams),
                "estimator_roles": sorted(est_roles),
                "model_decision_count": len(beam_decisions),
                "model_roles_covered": sorted(model_roles - {"UNKNOWN"}),
                "beam_in_model": len(beam_decisions) > 0,
                "v5_generated_rows": v5_beam_data.get("generated_rows", 0) if v5_beam_data else 0,
                "v5_matched_rows": v5_beam_data.get("matched_rows", 0) if v5_beam_data else 0,
                "v5_row_coverage_percent": v5_beam_data.get("row_coverage_percent", 0.0) if v5_beam_data else 0.0,
            })
            total_est_rows += est_rows
            total_model_rows += model_rows
            total_est_weight += est_weight
            total_model_weight += model_weight

        # Diameter-level comparison
        all_est_diameters: Dict[float, Dict[str, Any]] = {}
        for block in beam_blocks.values():
            for row in block.get("rows") or []:
                d = row.get("diameter_mm")
                if d:
                    entry = all_est_diameters.setdefault(float(d), {
                        "diameter_mm": float(d), "estimator_bars": 0,
                        "estimator_weight_kg": 0.0, "estimator_rows": 0,
                        "model_bars": 0, "model_weight_kg": 0.0, "coverage_percent": 0.0,
                    })
                    entry["estimator_bars"] += int(row.get("bar_count") or 0)
                    entry["estimator_weight_kg"] = round(
                        entry["estimator_weight_kg"] + float(row.get("steel_weight_kg") or 0), 3
                    )
                    entry["estimator_rows"] += 1
        # Enrich diameter from V5 diameter coverage
        v5_diam = payloads.get("v5_diameter_coverage") or {}
        for entry in (v5_diam.get("diameter_entries") or v5_diam.get("entries") or []):
            d = float(entry.get("diameter_mm") or 0)
            if d and d in all_est_diameters:
                all_est_diameters[d]["v5_model_weight_kg"] = entry.get("generated_steel_kg", 0)
                all_est_diameters[d]["v5_estimator_weight_kg"] = entry.get("estimator_steel_kg", 0)
                all_est_diameters[d]["v5_coverage_percent"] = entry.get("coverage_percent", 0)
        diameter_comparison = sorted(all_est_diameters.values(), key=lambda x: x["diameter_mm"])

        beam_coverage_pct = round(100 * len(all_est_beams & all_model_beams) / max(len(all_est_beams), 1), 2)
        row_coverage_pct = round(100 * total_model_rows / max(total_est_rows, 1), 2)
        weight_coverage_pct = round(100 * total_model_weight / max(total_est_weight, 0.001), 2)

        # Pull V5 baseline for context
        v5_est_steel = float(v5_base.get("estimator_steel_kg") or v5_comp.get("estimator_steel_kg") or 0.0)
        v5_gen_steel = float(v5_base.get("generated_steel_kg") or v5_comp.get("generated_steel_kg") or 0.0)
        v5_row_cov = float(v5_base.get("row_coverage_percent") or 0.0)
        v5_miss_rows = int(v5_comp.get("missing_rows") or 0)
        v5_eng_diff = int(v5_comp.get("engineering_differences") or 0)

        return {
            "per_beam": per_beam,
            "diameter_comparison": diameter_comparison,
            "summary": {
                "estimator_beams": len(all_est_beams),
                "model_beams": len(all_model_beams & all_est_beams),
                "missing_beams": len(all_est_beams - all_model_beams),
                "beam_coverage_percent": beam_coverage_pct,
                "estimator_total_rows": total_est_rows,
                "model_total_rows": total_model_rows,
                "missing_rows": max(0, total_est_rows - total_model_rows),
                "row_coverage_percent": row_coverage_pct,
                "estimator_total_steel_kg": round(total_est_weight, 3),
                "model_total_steel_kg": round(total_model_weight, 3),
                "steel_gap_kg": round(total_est_weight - total_model_weight, 3),
                "steel_coverage_percent": weight_coverage_pct,
                "model_decision_count": len(snapshot.get("decisions") or []),
                "pipeline_outputs_available": artifact_presence.get("beam_schedule_results", False),
            },
            "v5_baseline": {
                "source": "Version5 reference run (read-only)",
                "estimator_steel_kg": v5_est_steel,
                "generated_steel_kg": v5_gen_steel,
                "steel_gap_kg": round(v5_est_steel - v5_gen_steel, 3),
                "steel_coverage_percent": round(100 * v5_gen_steel / max(v5_est_steel, 0.001), 2),
                "row_coverage_percent": v5_row_cov,
                "missing_rows": v5_miss_rows,
                "engineering_differences": v5_eng_diff,
                "v5_available": bool(v5_base or v5_comp),
            },
            "artifact_presence": artifact_presence,
        }

    def _build_model_schedule(
        self,
        payloads: Dict[str, Any],
        decisions_by_beam: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        schedule = {}
        sched_payload = payloads.get("beam_schedule_results") or {}
        for result in (sched_payload.get("results") or []):
            beam_id = str(result.get("beam_id") or result.get("beam_mark") or "")
            if not beam_id:
                continue
            rows = result.get("rows") or []
            schedule[beam_id] = {
                "row_count": len(rows),
                "steel_weight_kg": float(result.get("total_steel_weight_kg") or 0.0),
            }
        # If schedule not available, build stub from decisions (0 weight)
        for beam_id in decisions_by_beam:
            if beam_id not in schedule:
                schedule[beam_id] = {"row_count": 0, "steel_weight_kg": 0.0}
        return schedule


def _beam_v5(v5_beam_payload: Any, beam_mark: str) -> Optional[Dict[str, Any]]:
    if not v5_beam_payload:
        return None
    for entry in (v5_beam_payload.get("beams") or []):
        if str(entry.get("beam_mark") or "") == beam_mark:
            return entry
    return None
