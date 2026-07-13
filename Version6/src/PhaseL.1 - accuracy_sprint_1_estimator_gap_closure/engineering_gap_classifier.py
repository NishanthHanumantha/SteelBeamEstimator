"""Classify every estimator difference into exactly one gap category."""

from __future__ import annotations

from typing import Any, Dict, List

GAP_CATEGORIES = (
    "PARSER_GAP",
    "GEOMETRY_GAP",
    "SPECIFICATION_GAP",
    "RECOVERY_GAP",
    "INTENT_GAP",
    "DECISION_GAP",
    "RULE_GAP",
    "CALCULATION_GAP",
    "REPORTING_GAP",
    "EXCEL_PRESENTATION_GAP",
    "UNKNOWN",
)


class EngineeringGapClassifier:
    """Assign exactly one gap category to each detected difference."""

    def classify(
        self,
        comparison: Dict[str, Any],
        snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        gaps: List[Dict[str, Any]] = []
        artifact = comparison.get("artifact_presence") or {}
        per_beam = comparison.get("per_beam") or []
        diameters = comparison.get("diameter_comparison") or []
        decisions = snapshot.get("decisions") or []
        payloads = snapshot.get("payloads") or {}
        v5_gap = payloads.get("v5_engineering_gap") or {}
        seq = [0]

        def _gap(category: str, title: str, description: str, affected_beams: List[str],
                 affected_roles: List[str], affected_diameters: List[float],
                 evidence: str, phase_origin: str, future_phase: str,
                 steel_impact_kg: float = 0.0) -> Dict[str, Any]:
            seq[0] += 1
            return {
                "gap_id": f"GAP::L.1::{seq[0]:04d}",
                "gap_category": category,
                "title": title,
                "description": description,
                "affected_beams": affected_beams,
                "affected_roles": affected_roles,
                "affected_diameters": [float(d) for d in affected_diameters],
                "evidence": evidence,
                "phase_origin": phase_origin,
                "future_phase": future_phase,
                "estimated_steel_impact_kg": round(steel_impact_kg, 3),
                "validated": False,
            }

        # --- MISSING CALCULATION PIPELINE (CALCULATION_GAP) ---
        missing_phases = [
            k for k in (
                "beam_schedule_results", "engineering_reports", "steel_weight_results",
                "bbs_results", "cut_length_results", "development_length_results",
            )
            if not artifact.get(k)
        ]
        if missing_phases:
            gaps.append(_gap(
                "CALCULATION_GAP",
                "Version6 Phase I calculation pipeline not yet executed",
                f"Phase I outputs absent: {', '.join(missing_phases)}. "
                "Engineering decisions exist (K.1.1/K.2.1) but calculation results are not yet "
                "generated in Version6. This is the single largest source of steel weight gap.",
                [],
                [],
                [],
                f"Missing artifacts: {missing_phases}",
                "Phase I (I.1–I.17)",
                "Phase L.2 — run full Version6 pipeline",
                comparison.get("summary", {}).get("steel_gap_kg", 0.0),
            ))

        # --- BOTTOM MAIN COVERAGE (RULE_GAP / INTENT_GAP) ---
        v5_gaps = {g.get("category", ""): g for g in (v5_gap.get("gaps") or [])}
        bm_gap = v5_gaps.get("Bottom Main")
        if bm_gap and bm_gap.get("count", 0) > 0:
            beams_affected = [b["beam_mark"] for b in per_beam]
            gaps.append(_gap(
                "RULE_GAP",
                "Bottom Main reinforcement — no engineering rule implemented",
                "Bottom Main bars are present in every estimator beam schedule but the pipeline "
                "produces 0 schedule rows for Bottom Main in all 18 beams. "
                "No engineering rule reconstructs main bottom reinforcement from drawings. "
                "Root cause: Bottom Main detection requires positive moment reinforcement rules "
                "that are not yet implemented in Engineering Intent Reconstruction.",
                beams_affected,
                ["BOTTOM_MAIN"],
                [],
                f"V5 baseline: found_in_pipeline=0, written_to_schedule=0, count={bm_gap.get('count')}",
                "Phase K.1 Engineering Intent / Phase I.3 Development Length",
                "Phase L.2 — implement bottom main engineering rule",
                0.0,
            ))

        # --- TOP EXTRA COVERAGE (RULE_GAP) ---
        te_gap = v5_gaps.get("Top Extra")
        if te_gap and te_gap.get("count", 0) > 0:
            gaps.append(_gap(
                "RULE_GAP",
                "Top Extra reinforcement — no engineering rule implemented",
                "Top Extra bars are present in the estimator for many beams but the pipeline "
                "produces 0 schedule rows for Top Extra. "
                "Negative moment redistribution and secondary top reinforcement rules are absent.",
                [b["beam_mark"] for b in per_beam],
                ["TOP_EXTRA"],
                [],
                f"V5 baseline: found_in_pipeline=0, written_to_schedule=0, count={te_gap.get('count')}",
                "Phase K.1 Engineering Intent",
                "Phase L.2",
                0.0,
            ))

        # --- BOTTOM EXTRA COVERAGE (RULE_GAP) ---
        be_gap = v5_gaps.get("Bottom Extra")
        if be_gap and be_gap.get("count", 0) > 0:
            gaps.append(_gap(
                "RULE_GAP",
                "Bottom Extra reinforcement — no engineering rule implemented",
                "Bottom Extra bars (positive moment extra reinforcement) absent from pipeline. "
                "No engineering rule targets this detailing category.",
                [b["beam_mark"] for b in per_beam],
                ["BOTTOM_EXTRA"],
                [],
                f"V5 baseline: found_in_pipeline=0, written_to_schedule=0, count={be_gap.get('count')}",
                "Phase K.1 Engineering Intent",
                "Phase L.2",
                0.0,
            ))

        # --- TOP MAIN partial coverage (INTENT_GAP) ---
        tm_gap = v5_gaps.get("Top Main")
        if tm_gap:
            missing_tm = tm_gap.get("count", 0)
            found_tm = (tm_gap.get("details") or {}).get("found_in_pipeline", 0)
            if missing_tm > 0:
                gaps.append(_gap(
                    "INTENT_GAP",
                    f"Top Main reinforcement — {missing_tm} beams not reaching schedule",
                    f"Top Main reinforcement found in pipeline for {found_tm} beams but "
                    f"{missing_tm} beams produce no schedule row. "
                    "Engineering intent is reconstructed for some beams but the intent-to-decision "
                    "resolution fails for a subset. May be caused by zone configuration or "
                    "support context missing.",
                    [],
                    ["TOP_MAIN"],
                    [],
                    f"V5: missing_from_schedule={missing_tm}, found_in_pipeline={found_tm}",
                    "Phase K.1.1 Engineering Intent Resolution",
                    "Phase L.2",
                    0.0,
                ))

        # --- PER-BEAM MISSING ROWS (CALCULATION_GAP) ---
        for beam_data in per_beam:
            miss = beam_data.get("missing_rows", 0)
            if miss > 0 and artifact.get("beam_schedule_results"):
                gaps.append(_gap(
                    "CALCULATION_GAP",
                    f"Beam {beam_data['beam_mark']} — {miss} missing schedule rows",
                    f"Beam {beam_data['beam_mark']}: estimator has {beam_data['estimator_rows']} rows, "
                    f"model produced {beam_data['model_rows']} rows. "
                    f"Coverage: {beam_data['row_coverage_percent']}%.",
                    [beam_data["beam_mark"]],
                    [],
                    [],
                    f"Row coverage {beam_data['row_coverage_percent']}%",
                    "Phase I.15 Beam Schedule",
                    "Phase L.2",
                    beam_data.get("weight_difference_kg", 0.0),
                ))

        # --- STEEL WEIGHT GAP (CALCULATION_GAP aggregated) ---
        summ = comparison.get("summary") or {}
        steel_gap = summ.get("steel_gap_kg", 0.0)
        if steel_gap > 0:
            v5b = comparison.get("v5_baseline") or {}
            v5_steel_gap = v5b.get("steel_gap_kg", 0.0)
            gaps.append(_gap(
                "CALCULATION_GAP",
                f"Steel weight undercount: {steel_gap:.1f} kg gap vs estimator",
                f"Estimator total steel: {summ.get('estimator_total_steel_kg', 0)} kg. "
                f"Model total steel: {summ.get('model_total_steel_kg', 0)} kg. "
                f"Gap: {steel_gap:.1f} kg ({100 - summ.get('steel_coverage_percent', 0):.1f}%). "
                f"V5 baseline gap was {v5_steel_gap:.1f} kg. "
                "Driven by missing reinforcement categories (Bottom Main, Top/Bottom Extra) "
                "and incomplete Phase I pipeline execution in Version6.",
                [],
                ["BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA", "TOP_MAIN"],
                [],
                f"Model steel={summ.get('model_total_steel_kg')} kg vs estimator={summ.get('estimator_total_steel_kg')} kg",
                "Phase I.11 Steel Weight",
                "Phase L.2",
                steel_gap,
            ))

        # --- DEVELOPMENT LENGTH / HOOK RULES (RULE_GAP) ---
        if not artifact.get("development_length_results") or not artifact.get("hook_results"):
            gaps.append(_gap(
                "RULE_GAP",
                "Development length and hook calculation outputs absent",
                "Phase I.3 Development Length and Phase I.4 Hook Length results are not present. "
                "These drive cut length and ultimately steel weight accuracy. "
                "Without these, any schedule rows produced cannot have accurate bar lengths.",
                [],
                [],
                [],
                "development_length_results and hook_results absent from V6 output",
                "Phase I.3–I.4",
                "Phase L.2 — run full pipeline",
                0.0,
            ))

        # --- DECISION COVERAGE vs ESTIMATOR ROLES (DECISION_GAP) ---
        all_model_categories = set(snapshot.get("decisions_by_category", {}).keys())
        supplementary_cats = {c for c in all_model_categories if c.startswith("SUPPLEMENTARY_")}
        main_cats = {c for c in all_model_categories if "SUPPORT" in c or "MAIN" in c.upper()}
        if not any("BOTTOM" in c.upper() or "MAIN" in c.upper() for c in all_model_categories):
            gaps.append(_gap(
                "DECISION_GAP",
                "Engineering Decision system has no Bottom Main or negative moment categories",
                "The K.1.1 decision graph only contains SUPPLEMENTARY_* and SUPPORT_REINFORCEMENT "
                "categories. Bottom Main, Top Extra, Bottom Extra and Stirrup categories are absent "
                "from the engineering decision vocabulary. "
                "These must be added as new decision categories in Phase K.1.1.",
                [],
                ["BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA", "STIRRUP"],
                [],
                f"Model categories found: {sorted(all_model_categories)}",
                "Phase K.1.1 Engineering Intent Resolution",
                "Phase L.2",
                0.0,
            ))

        # --- STIRRUP COVERAGE (RULE_GAP) ---
        gaps.append(_gap(
            "RULE_GAP",
            "Stirrup/Shear link reinforcement — no engineering rule implemented",
            "Stirrups are present in every estimator beam schedule with specified spacing and "
            "diameter. The pipeline has no dedicated stirrup intent reconstruction or decision "
            "category. Stirrup cut length includes bends, hooks and clear span geometry — "
            "a distinct engineering rule set is required.",
            [b["beam_mark"] for b in per_beam],
            ["STIRRUP"],
            [],
            "Stirrup category absent from V6 decision vocabulary",
            "Phase K.1 Engineering Intent",
            "Phase L.2",
            0.0,
        ))

        # --- SPECIFICATION GAP (concrete/steel grade per beam) ---
        gaps.append(_gap(
            "SPECIFICATION_GAP",
            "Per-beam specification parameters not validated against estimator",
            "The estimator workbook header specifies: Cover=25mm, M30, Fe550D, Spacer=25mm@1m. "
            "Current pipeline reads specifications from general notes but does not "
            "validate per-beam specification against the estimator workbook header. "
            "Specification mismatch would propagate to development length errors.",
            [],
            [],
            [],
            "Estimator header: Cover=25mm, M30, Fe550D confirmed. V6 spec alignment not verified.",
            "Phase H.1 Engineering Specifications",
            "Phase L.2",
            0.0,
        ))

        # --- EXCEL PRESENTATION (EXCEL_PRESENTATION_GAP) ---
        v5_pres_diff = (payloads.get("v5_comparison_stats") or {}).get("presentation_differences", 0)
        if v5_pres_diff > 0:
            gaps.append(_gap(
                "EXCEL_PRESENTATION_GAP",
                f"Excel output format differences vs estimator ({v5_pres_diff} detected in V5)",
                "V5 baseline found presentation differences in Excel template layout, "
                "column ordering and formatting vs estimator workbook. "
                "These are lower-priority cosmetic/format gaps that do not affect engineering accuracy.",
                [],
                [],
                [],
                f"V5 presentation_differences={v5_pres_diff}",
                "Phase I.17 Excel Export",
                "Phase L.3",
                0.0,
            ))

        # --- GEOMETRY GAP (if any beam geometry mismatches) ---
        gaps.append(_gap(
            "GEOMETRY_GAP",
            "Clear span and beam section geometry accuracy not yet fully validated in V6",
            "Beam geometry (clear span, width, depth) read from drawing must match the estimator. "
            "The V5 pipeline achieved beam-level presence but geometry mismatches drive "
            "cut length and development length errors. "
            "V6 geometry accuracy requires Phase F and Phase H to be re-run.",
            [],
            [],
            [],
            "Framing geometry and beam section data present in V6 source but not yet validated against estimator in V6",
            "Phase F.1–F.6 Framing Geometry",
            "Phase L.2",
            0.0,
        ))

        return gaps
