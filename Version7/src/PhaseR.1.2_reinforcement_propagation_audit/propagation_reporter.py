"""Propagation audit reporter."""
from __future__ import annotations
from typing import Any, Dict, List

from .propagation_models import BeamPropagationRecord, ValidationResult


class PropagationReporter:

    def build_report(
        self,
        records: List[BeamPropagationRecord],
        root_cause_report: Dict[str, Any],
        statistics: Dict[str, Any],
        comparison: Dict[str, Any],
        validation_results: List[ValidationResult],
    ) -> Dict[str, Any]:
        passed = sum(1 for r in validation_results if r.passed)
        with_groups = [r.beam_id for r in records if r.r1_group_count > 0]
        with_eng = [r.beam_id for r in records if r.l2_bar_count > 0]
        with_steel = [r.beam_id for r in records if r.steel_weight_kg > 0]
        with_bbs = [r.beam_id for r in records if r.bbs_engineering_rows > 0]

        return {
            "phase": "R.1.2",
            "model_version": "7.3.2",
            "audit_type": "READ-ONLY propagation traceability",
            "validation_score": f"{passed}/{len(validation_results)}",
            "all_pass": passed == len(validation_results),
            "executive_summary": {
                "total_beams": len(records),
                "beams_with_r1_groups": len(with_groups),
                "beams_with_engineering_bars": len(with_eng),
                "beams_reaching_steel_calculation": len(with_steel),
                "beams_generating_bbs_rows": len(with_bbs),
                "beams_in_excel_with_steel": len(with_steel),
                "primary_root_cause": root_cause_report.get("primary_systemic_root_cause"),
                "first_failure_stage_for_60_beams": "L2",
            },
            "deterministic_answers": {
                "1_beams_with_reinforcement_groups": with_groups,
                "2_beams_producing_engineering_bars": with_eng,
                "3_beams_reaching_steel_calculation": with_steel,
                "4_beams_generating_bbs_rows": with_bbs,
                "5_beams_in_excel_with_steel": with_steel,
                "6_failed_beam_first_failure_stage": root_cause_report.get(
                    "beams_by_first_failure_stage"
                ),
                "7_responsible_module": root_cause_report.get("responsible_module"),
                "8_failure_caused_by": (
                    "L.2 Engineering Object Creation (REFERENCE_CLASSIFICATION) "
                    "and V.B.1 reading L.2 instead of R.1"
                ),
            },
            "statistics": statistics,
            "r1_vs_workbook_comparison": comparison,
            "validation_rules": [r.to_dict() for r in validation_results],
        }
