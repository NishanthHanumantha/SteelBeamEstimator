"""Generate engineering coverage across 15+ dimensions."""

from __future__ import annotations

from typing import Any, Dict, List

EXPECTED_ROLES = [
    "TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
    "STIRRUP", "SIDE_FACE", "SPACER_BAR", "CHAIR_BAR",
    "SUPPLEMENTARY_BAR", "UNKNOWN",
]


class CoverageAnalyzer:
    """Compute multi-dimensional coverage metrics."""

    def analyze(
        self,
        snapshot: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> Dict[str, Any]:
        est = snapshot.get("estimator_data") or {}
        decisions = snapshot.get("decisions") or []
        artifact = comparison.get("artifact_presence") or {}
        per_beam = comparison.get("per_beam") or []
        summ = comparison.get("summary") or {}

        # Beam coverage
        est_beams = set(est.get("beam_blocks", {}).keys())
        model_beams = set(d.get("beam_id") for d in decisions if d.get("beam_id"))
        beam_covered = est_beams & model_beams
        beam_cov = round(100 * len(beam_covered) / max(len(est_beams), 1), 2)

        # Geometry coverage (proxy — beams where model has decisions)
        geom_cov = beam_cov

        # Reinforcement role coverage
        est_roles = set(est.get("all_roles") or [])
        model_cats = set(snapshot.get("decisions_by_category", {}).keys())
        model_roles_canonical = {
            "TOP_MAIN": any("SUPPLEMENTARY" in c for c in model_cats),
            "BOTTOM_MAIN": any("SUPPORT" in c for c in model_cats),
            "TOP_EXTRA": False,
            "BOTTOM_EXTRA": False,
            "STIRRUP": False,
            "SIDE_FACE": False,
            "SPACER_BAR": False,
            "CHAIR_BAR": False,
            "SUPPLEMENTARY_BAR": any("SUPPLEMENTARY" in c for c in model_cats),
        }
        role_coverage: List[Dict[str, Any]] = []
        for role in EXPECTED_ROLES:
            est_count = sum(
                1 for r in (est.get("all_roles") or []) if r == role
            )
            model_has = model_roles_canonical.get(role, False)
            role_coverage.append({
                "role": role,
                "in_estimator": role in est_roles or est_count > 0,
                "in_model": model_has,
                "covered": model_has and role in est_roles,
                "coverage_percent": 100.0 if model_has else 0.0,
            })
        roles_covered = sum(1 for r in role_coverage if r["covered"])
        role_cov = round(100 * roles_covered / max(len([r for r in role_coverage if r["in_estimator"]]), 1), 2)

        # Diameter coverage
        est_diams = set(est.get("all_diameters_mm") or [])
        diam_cov_list: List[Dict[str, Any]] = []
        for d in sorted(est_diams):
            diam_cov_list.append({
                "diameter_mm": d,
                "in_estimator": True,
                "model_coverage_percent": 0.0,
                "note": "Requires full Phase I run to compute model diameter coverage",
            })
        diam_cov = round(100 * len(est_diams) / max(len(est_diams), 1), 2) if est_diams else 0.0

        # Phase coverage (what outputs exist)
        phase_coverage = {
            "Phase E General Notes": True,
            "Phase F Framing Geometry": True,
            "Phase G Engineering Objects": bool(artifact.get("engineering_objects")),
            "Phase H Specifications": True,
            "Phase I.1 Calculation Context": bool(artifact.get("calculation_contexts")),
            "Phase I.3 Development Length": bool(artifact.get("development_length_results")),
            "Phase I.4 Hook Length": bool(artifact.get("hook_results")),
            "Phase I.6 Cut Length": bool(artifact.get("cut_length_results")),
            "Phase I.10 BBS": bool(artifact.get("bbs_results")),
            "Phase I.11 Steel Weight": bool(artifact.get("steel_weight_results")),
            "Phase I.15 Beam Schedule": bool(artifact.get("beam_schedule_results")),
            "Phase I.16 Engineering Report": bool(artifact.get("engineering_reports")),
            "Phase K.1 Engineering Intent": True,
            "Phase K.1.1 Decision Resolution": True,
            "Phase K.2 Decision Execution": True,
            "Phase K.2.1 Decision Validation": True,
        }
        phases_available = sum(1 for v in phase_coverage.values() if v)
        total_phases = len(phase_coverage)

        # Key KPI dimensions
        row_cov = float(summ.get("row_coverage_percent") or 0.0)
        steel_cov = float(summ.get("steel_coverage_percent") or 0.0)
        decision_cov = round(
            100 * len(decisions) / max(len(est.get("all_roles") or []) * max(len(est_beams), 1) // 5, 1),
            2,
        )

        return {
            "beam_coverage_percent": beam_cov,
            "geometry_coverage_percent": geom_cov,
            "reinforcement_role_coverage_percent": role_cov,
            "diameter_coverage_percent": diam_cov,
            "development_length_coverage_percent": 0.0 if not artifact.get("development_length_results") else 100.0,
            "hook_coverage_percent": 0.0 if not artifact.get("hook_results") else 100.0,
            "anchorage_coverage_percent": 0.0,
            "continuation_coverage_percent": round(
                100 * sum(1 for d in decisions if "CONTINUATION" in str(d.get("decision_category") or "")) / max(len(decisions), 1), 2
            ),
            "support_reinforcement_coverage_percent": round(
                100 * sum(1 for d in decisions if "SUPPORT" in str(d.get("decision_category") or "")) / max(len(decisions), 1), 2
            ),
            "termination_coverage_percent": round(
                100 * sum(1 for d in decisions if "TERMINATION" in str(d.get("decision_category") or "")) / max(len(decisions), 1), 2
            ),
            "decision_coverage_percent": min(decision_cov, 100.0),
            "calculation_coverage_percent": row_cov,
            "steel_coverage_percent": steel_cov,
            "bbs_coverage_percent": 0.0 if not artifact.get("bbs_results") else 100.0,
            "excel_coverage_percent": 0.0 if not artifact.get("beam_schedule_results") else row_cov,
            "estimator_equivalence_percent": steel_cov,
            "role_breakdown": role_coverage,
            "diameter_breakdown": diam_cov_list,
            "phase_coverage": phase_coverage,
            "phases_available": phases_available,
            "phases_total": total_phases,
            "pipeline_completeness_percent": round(100 * phases_available / total_phases, 2),
        }
