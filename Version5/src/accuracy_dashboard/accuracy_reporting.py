"""Management and visual coverage reporting — Phase QA.ACCURACY.1."""

from __future__ import annotations

from typing import Any, Dict, List

from src.accuracy_dashboard.accuracy_types import DASHBOARD_TITLE, DIAMETER_SUMMARY_SOURCE, MANAGEMENT_NOTE, STANDARD_DIAMETERS_MM


class AccuracyReporting:
    @staticmethod
    def build(result: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
        excel = result.get("excel_accuracy", {})
        steel = result.get("steel_accuracy", {})
        pipeline = result.get("pipeline_metadata", {})
        recommendation = AccuracyReporting._recommended_focus(excel, steel)
        improvement_potential = AccuracyReporting._improvement_potential(excel, steel, recommendation)
        diameter_coverage = result.get("diameter_coverage", {})
        official_summary = result.get("official_quantity_summary", {})
        diameter_recommendations = AccuracyReporting._diameter_recommendations(diameter_coverage)
        return {
            "phase": result.get("phase"),
            "coverage_extension": result.get("coverage_extension"),
            "official_summary_extension": result.get("official_summary_extension"),
            "terminology_refinement": result.get("terminology_refinement"),
            "model_version": result.get("model_version"),
            "dashboard_title": DASHBOARD_TITLE,
            "executive_summary": AccuracyReporting._executive_summary(summary, recommendation, diameter_coverage, official_summary),
            "management_note": MANAGEMENT_NOTE,
            "engineering_benefits_of_summary_comparison": AccuracyReporting._summary_comparison_benefits(),
            "project_status": AccuracyReporting._project_status(recommendation),
            "current_kpis": {
                "beam_coverage_percent": excel.get("beam_coverage_percent"),
                "schedule_coverage_percent": excel.get("row_coverage_percent"),
                "missing_rows": excel.get("missing_rows"),
                "missing_values": excel.get("missing_values"),
                "steel_quantity_coverage_percent": steel.get("accuracy_percent"),
                "steel_difference_kg": steel.get("difference_kg"),
            },
            "coverage_table": result.get("beam_coverage_table", []),
            "steel_comparison": {
                "generated_steel_kg": steel.get("generated_steel_kg"),
                "estimator_steel_kg": steel.get("estimator_steel_kg"),
                "coverage_percent": steel.get("accuracy_percent"),
                "difference_kg": steel.get("difference_kg"),
                "difference_percent": steel.get("difference_percent"),
            },
            "diameter_coverage_table": diameter_coverage.get("diameters", []),
            "diameter_coverage_summary": diameter_coverage.get("summary", {}),
            "official_quantity_summary": official_summary,
            "diameter_coverage_ranking": AccuracyReporting._diameter_ranking(diameter_coverage),
            "engineering_recommendations_by_diameter": diameter_recommendations,
            "improvement_potential": improvement_potential,
            "recommended_next_engineering_focus": recommendation,
            "pipeline_status": {
                "engineering_report": (
                    "Working correctly"
                    if pipeline.get("engineering_report_present")
                    else "Output not found"
                ),
                "beam_schedule": (
                    "Working correctly"
                    if pipeline.get("beam_schedule_present")
                    else "Output not found"
                ),
                "excel_export": (
                    "Working correctly"
                    if excel.get("beam_coverage_percent", 0) >= 99.0
                    else "Requires review"
                ),
            },
        }

    @staticmethod
    def build_management_summary(result: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
        excel = result.get("excel_accuracy", {})
        steel = result.get("steel_accuracy", {})
        pipeline = result.get("pipeline_metadata", {})
        beam_coverage = excel.get("beam_coverage_percent", 0.0)
        schedule_coverage = excel.get("row_coverage_percent", 0.0)
        steel_coverage = steel.get("accuracy_percent", 0.0)
        diameter_coverage = result.get("diameter_coverage", {})
        official_summary = result.get("official_quantity_summary", {})
        diameter_summary = diameter_coverage.get("summary", {})
        primary_area = AccuracyReporting._primary_diameter_improvement_area(diameter_coverage)
        official_steel = {
            "estimator_kg": official_summary.get("estimator", {}).get("total"),
            "generated_kg": official_summary.get("generated", {}).get("total"),
            "coverage_percent": steel.get("accuracy_percent"),
            "quantity_source": official_summary.get("diameter_summary_source", DIAMETER_SUMMARY_SOURCE),
        }
        diameter_coverage_summary = {
            str(entry.get("diameter_mm")): entry.get("coverage_percent")
            for entry in diameter_coverage.get("diameters", [])
        }
        return {
            "title": "Current Prototype Coverage",
            "dashboard_title": DASHBOARD_TITLE,
            "beam_coverage_percent": beam_coverage,
            "schedule_coverage_percent": schedule_coverage,
            "steel_quantity_coverage_percent": round(steel_coverage, 1),
            "official_steel_quantity": official_steel,
            "diameter_wise_steel_coverage": {
                "best_performing_diameter_mm": diameter_summary.get("best_performing_diameter_mm"),
                "best_performing_coverage_percent": diameter_summary.get("best_performing_coverage_percent"),
                "worst_performing_diameter_mm": diameter_summary.get("worst_performing_diameter_mm"),
                "worst_performing_coverage_percent": diameter_summary.get("worst_performing_coverage_percent"),
                "largest_quantity_gap": diameter_summary.get("largest_quantity_gap"),
                "primary_improvement_area": primary_area,
                "diameter_coverage": diameter_coverage_summary,
            },
            "major_improvement_opportunity": recommendation.get("major_improvement_opportunity", "Unknown"),
            "major_cause": recommendation.get("major_cause", "Unknown"),
            "management_note": MANAGEMENT_NOTE,
            "project_status": AccuracyReporting._project_status(recommendation),
            "excel_export_status": (
                "Working correctly"
                if beam_coverage >= 99.0 and excel.get("missing_beams", 0) == 0
                else "Requires review"
            ),
            "engineering_report_status": (
                "Working correctly"
                if pipeline.get("engineering_report_present")
                else "Output not found"
            ),
            "pipeline_stage_requiring_improvement": recommendation.get("pipeline_stage", "Unknown"),
            "metrics": {
                "beam_coverage": excel.get("beam_coverage"),
                "schedule_coverage": excel.get("row_coverage"),
                "missing_rows": excel.get("missing_rows"),
                "missing_values": excel.get("missing_values"),
                "generated_steel_kg": steel.get("generated_steel_kg"),
                "estimator_steel_kg": steel.get("estimator_steel_kg"),
            },
        }

    @staticmethod
    def _project_status(recommendation: dict[str, Any]) -> dict[str, Any]:
        return {
            "engineering_status": "Prototype",
            "description": "Engineering interpretation under active development.",
            "current_priority": "Improve reinforcement interpretation and schedule completeness.",
            "do_not_recommend_excel_improvements": not recommendation.get("recommend_excel_improvement", False),
        }

    @staticmethod
    def _summary_comparison_benefits() -> List[str]:
        return [
            "Uses estimator-approved official diameter summary quantities.",
            "Presentation independent — ignores row ordering and merged layout differences.",
            "Row independent — not affected by missing individual schedule rows.",
            "Matches engineering validation methodology used for final diameter totals.",
            "Management friendly — compares the same summary tables engineers review.",
        ]

    @staticmethod
    def _executive_summary(
        summary: dict[str, Any],
        recommendation: dict[str, Any],
        diameter_coverage: dict[str, Any],
        official_summary: dict[str, Any],
    ) -> str:
        diameter_summary = diameter_coverage.get("summary", {})
        best = diameter_summary.get("best_performing_diameter_mm")
        worst = diameter_summary.get("worst_performing_diameter_mm")
        official_estimator = official_summary.get("estimator", {}).get("total")
        official_generated = official_summary.get("generated", {}).get("total")
        diameter_note = ""
        if best is not None and worst is not None:
            diameter_note = (
                f" Official diameter summary coverage ranges from "
                f"D{worst} ({diameter_summary.get('worst_performing_coverage_percent')}%) "
                f"to D{best} ({diameter_summary.get('best_performing_coverage_percent')}%)."
            )
        return (
            f"Beam coverage is {summary.get('beam_coverage_percent', 0):.1f}% "
            f"({summary.get('missing_beams', 0)} missing beams). "
            f"The current schedule generation covers approximately "
            f"{summary.get('schedule_coverage_percent', 0):.1f}% of the estimator reinforcement schedule "
            f"with {summary.get('missing_rows', 0)} missing reinforcement rows and "
            f"{summary.get('missing_values', 0)} engineering value differences. "
            f"Official summary totals show {official_generated} kg generated against "
            f"{official_estimator} kg estimator-approved steel "
            f"({summary.get('steel_quantity_coverage_percent', 0):.1f}% coverage)."
            f"{diameter_note} "
            f"Recommended focus: {recommendation.get('focus', 'Unknown')}."
        )

    @staticmethod
    def _diameter_ranking(diameter_coverage: dict[str, Any]) -> dict[str, Any]:
        calculable = [
            entry for entry in diameter_coverage.get("diameters", [])
            if isinstance(entry.get("coverage_percent"), (int, float))
        ]
        ranked = sorted(calculable, key=lambda item: float(item["coverage_percent"]), reverse=True)
        summary = diameter_coverage.get("summary", {})
        return {
            "best_diameter_mm": summary.get("best_performing_diameter_mm"),
            "worst_diameter_mm": summary.get("worst_performing_diameter_mm"),
            "largest_quantity_difference": summary.get("largest_quantity_gap"),
            "ranked_diameters": [
                {
                    "diameter_mm": entry["diameter_mm"],
                    "coverage_percent": entry["coverage_percent"],
                    "difference_kg": entry["difference_kg"],
                }
                for entry in ranked
            ],
        }

    @staticmethod
    def _primary_diameter_improvement_area(diameter_coverage: dict[str, Any]) -> str:
        summary = diameter_coverage.get("summary", {})
        worst = summary.get("worst_performing_diameter_mm")
        if worst is None:
            return "Unknown"
        entry = next(
            (item for item in diameter_coverage.get("diameters", []) if item.get("diameter_mm") == worst),
            {},
        )
        roles = entry.get("roles_present") or []
        if worst == 8 or "STIRRUP" in roles or "SFR" in roles:
            return "Ø8 Stirrups"
        if worst in (16, 12):
            return f"Ø{worst} Top/Bottom Bars"
        if worst == 20:
            return "Ø20 Main Bars"
        return f"Ø{worst} Reinforcement"

    @staticmethod
    def _diameter_recommendations(diameter_coverage: dict[str, Any]) -> List[dict[str, Any]]:
        recommendations: List[dict[str, Any]] = []
        for entry in diameter_coverage.get("diameters", []):
            diameter = entry.get("diameter_mm")
            coverage = entry.get("coverage_percent")
            roles = entry.get("roles_present") or []
            estimator_kg = float(entry.get("estimator_steel_kg") or 0.0)
            generated_kg = float(entry.get("generated_steel_kg") or 0.0)

            if estimator_kg > 0 and generated_kg <= 0:
                recommendations.append({
                    "diameter_mm": diameter,
                    "recommendation": "Review parser callout interpretation.",
                    "reason": "Diameter entirely missing from generated schedule.",
                })
                continue

            if coverage == "N/A":
                continue

            coverage_value = float(coverage)
            if diameter == 8 and coverage_value < 30.0:
                recommendations.append({
                    "diameter_mm": diameter,
                    "recommendation": "Review stirrup interpretation.",
                    "reason": "Ø8 coverage extremely low.",
                })
            elif diameter == 20 and coverage_value >= 70.0:
                recommendations.append({
                    "diameter_mm": diameter,
                    "recommendation": "Main bar interpretation healthy.",
                    "reason": "Ø20 coverage is comparatively strong.",
                })
            elif diameter == 16 and coverage_value < 70.0:
                recommendations.append({
                    "diameter_mm": diameter,
                    "recommendation": "Review top/bottom bar interpretation.",
                    "reason": "Ø16 coverage is low.",
                })
            elif coverage_value < 30.0:
                recommendations.append({
                    "diameter_mm": diameter,
                    "recommendation": "Review reinforcement interpretation for this diameter.",
                    "reason": f"Ø{diameter} coverage is very low.",
                })
        return recommendations

    @staticmethod
    def _recommended_focus(excel: dict[str, Any], steel: dict[str, Any]) -> dict[str, Any]:
        beam_coverage = float(excel.get("beam_coverage_percent") or 0.0)
        row_coverage = float(excel.get("row_coverage_percent") or 0.0)
        steel_coverage = float(steel.get("accuracy_percent") or 0.0)
        missing_beams = int(excel.get("missing_beams") or 0)

        if missing_beams > 0 or beam_coverage < 95.0:
            return {
                "focus": "Beam detection and beam schedule coverage",
                "pipeline_stage": "Beam Schedule / Beam Detection",
                "major_cause": "Missing beams in generated schedule",
                "major_improvement_opportunity": "Beam Detection",
                "recommend_excel_improvement": False,
            }

        if row_coverage < 80.0 or excel.get("missing_rows", 0) > 0:
            return {
                "focus": "Reinforcement interpretation and bar identity",
                "pipeline_stage": "Bar Identity / Engineering Interpretation",
                "major_cause": "Missing reinforcement interpretation",
                "major_improvement_opportunity": "Reinforcement Interpretation",
                "recommend_excel_improvement": False,
            }

        if steel_coverage < 95.0:
            return {
                "focus": "Quantity and steel weight derivation",
                "pipeline_stage": "Quantity / Steel Weight",
                "major_cause": "Steel quantity not yet fully generated on matched rows",
                "major_improvement_opportunity": "Steel Quantity Generation",
                "recommend_excel_improvement": False,
            }

        return {
            "focus": "Maintain current coverage baseline",
            "pipeline_stage": "None — within target",
            "major_cause": "No major gap identified",
            "major_improvement_opportunity": "None",
            "recommend_excel_improvement": False,
        }

    @staticmethod
    def _improvement_potential(
        excel: dict[str, Any],
        steel: dict[str, Any],
        recommendation: dict[str, Any],
    ) -> dict[str, Any]:
        beam_gap = max(0.0, 100.0 - float(excel.get("beam_coverage_percent") or 0.0))
        schedule_gap = max(0.0, 100.0 - float(excel.get("row_coverage_percent") or 0.0))
        steel_gap = max(0.0, 100.0 - float(steel.get("accuracy_percent") or 0.0))
        opportunities: List[Dict[str, Any]] = [
            {
                "area": "Beam Coverage",
                "current_percent": excel.get("beam_coverage_percent"),
                "gap_percent": round(beam_gap, 2),
            },
            {
                "area": "Schedule Coverage",
                "current_percent": excel.get("row_coverage_percent"),
                "gap_percent": round(schedule_gap, 2),
            },
            {
                "area": "Steel Quantity Coverage",
                "current_percent": steel.get("accuracy_percent"),
                "gap_percent": round(steel_gap, 2),
            },
        ]
        largest = max(opportunities, key=lambda item: item["gap_percent"])
        return {
            "largest_opportunity": largest["area"],
            "largest_gap_percent": largest["gap_percent"],
            "opportunities": opportunities,
            "recommendation": recommendation.get("focus"),
            "do_not_recommend_excel_improvement": not recommendation.get("recommend_excel_improvement", False),
        }
