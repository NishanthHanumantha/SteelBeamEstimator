"""Detect missing bars and assign root causes."""
from __future__ import annotations
from typing import Any, Dict, List

from .propagation_models import BENCHMARK_BEAMS, BeamPropagationRecord
from .reinforcement_model_reader import ReinforcementModelReader


class MissingBarDetector:

    def detect(
        self, records: List[BeamPropagationRecord]
    ) -> Dict[str, Any]:
        missing: List[Dict[str, Any]] = []
        for rec in records:
            if rec.steel_weight_kg > 0:
                continue
            missing.append({
                "beam_id": rec.beam_id,
                "r1_quantity": rec.r1_total_quantity,
                "l2_bars": rec.l2_bar_count,
                "adapter_bars": rec.adapter_bar_count,
                "first_failure_stage": rec.first_failure_stage,
                "root_cause": rec.root_cause,
            })
        return {
            "missing_steel_beams": len(missing),
            "beams": missing,
            "benchmark_beams_with_steel": sorted(
                r.beam_id for r in records if r.steel_weight_kg > 0
            ),
            "non_benchmark_missing": sorted(
                r.beam_id for r in records
                if r.steel_weight_kg == 0 and r.beam_id not in BENCHMARK_BEAMS
            ),
        }


class RootCauseLocator:

    L2_MODULE = "PhaseL.2 - engineering_reinforcement_interpretation/bar_role_classifier.py"
    L2_FUNCTION = "BarRoleClassifier.classify() — REFERENCE_CLASSIFICATION"
    VB1_MODULE = "PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py"
    VB1_FUNCTION = "_step_steel_weight() — reads L.2 models only"

    def locate(
        self,
        records: List[BeamPropagationRecord],
        reader: ReinforcementModelReader,
    ) -> List[BeamPropagationRecord]:
        for rec in records:
            rec.first_failure_stage, rec.root_cause, rec.responsible_module, \
                rec.responsible_function, rec.evidence = self._classify(rec, reader)
        return records

    def _classify(
        self,
        rec: BeamPropagationRecord,
        reader: ReinforcementModelReader,
    ) -> tuple:
        beam_id = rec.beam_id

        if not rec.in_registry:
            return "VROOT", "UNKNOWN", "beam_registry_builder.py", "build()", "Beam not in registry"

        if rec.r1_total_quantity == 0:
            return "R1", "NO_REINFORCEMENT", (
                "PhaseR.1_generalized_reinforcement_discovery/annotation_discovery.py"
            ), "discover()", (
                f"No reinforcement annotations found for {beam_id} in R.1 DXF discovery"
            )

        if rec.l2_bar_count == 0 and rec.r1_total_quantity > 0:
            if beam_id not in BENCHMARK_BEAMS:
                return (
                    "L2", "L2_FILTERED",
                    self.L2_MODULE, self.L2_FUNCTION,
                    (
                        f"Beam {beam_id} has {rec.r1_total_quantity} R.1 group qty but 0 L.2 bars. "
                        f"REFERENCE_CLASSIFICATION only defines bars for {sorted(BENCHMARK_BEAMS)}. "
                        f"Non-benchmark beams receive empty bar lists in L.2 interpretation."
                    ),
                )
            return "L2", "BAR_CREATION_FAILED", self.L2_MODULE, self.L2_FUNCTION, (
                f"Benchmark beam {beam_id} has R.1 data but no L.2 bars"
            )

        if rec.l2_bar_count > 0 and rec.steel_weight_kg == 0:
            return (
                "STEEL", "STEEL_SKIPPED",
                "steel_weight_completion.py", "compute()",
                f"{rec.l2_bar_count} L.2 bars present but steel weight = 0",
            )

        if rec.steel_weight_kg > 0 and rec.bbs_engineering_rows == 0:
            return (
                "BBS", "BBS_SKIPPED",
                "bbs_completion_engine.py", "generate()",
                f"Steel weight {rec.steel_weight_kg} kg but no BBS engineering rows",
            )

        if rec.steel_weight_kg > 0:
            return (
                "EXCEL", "FULLY_PROPAGATED",
                "estimator_excel_generator.py", "generate()",
                f"Fully propagated: {rec.steel_bar_count} bars, {rec.steel_weight_kg:.3f} kg",
            )

        return "UNKNOWN", "UNKNOWN", "", "", "Unable to classify"

    def report(self, records: List[BeamPropagationRecord]) -> Dict[str, Any]:
        by_cause: Dict[str, List[str]] = {}
        by_stage: Dict[str, List[str]] = {}
        for rec in records:
            by_cause.setdefault(rec.root_cause, []).append(rec.beam_id)
            by_stage.setdefault(rec.first_failure_stage, []).append(rec.beam_id)

        primary = (
            "L2_FILTERED at bar_role_classifier.py — "
            "REFERENCE_CLASSIFICATION limits L.2 bars to 5 benchmark beams; "
            "V.B.1 consumes L.2 not R.1"
        )

        return {
            "primary_systemic_root_cause": primary,
            "responsible_module": self.L2_MODULE,
            "responsible_function": self.L2_FUNCTION,
            "downstream_module": self.VB1_MODULE,
            "downstream_function": self.VB1_FUNCTION,
            "beams_by_root_cause": {k: sorted(v) for k, v in sorted(by_cause.items())},
            "beams_by_first_failure_stage": {k: sorted(v) for k, v in sorted(by_stage.items())},
            "per_beam": [r.to_dict() for r in records],
        }
