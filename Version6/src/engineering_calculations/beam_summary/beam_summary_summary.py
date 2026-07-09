"""Beam summary summary — Phase I.12."""

from __future__ import annotations

from typing import Any, List

from src.engineering_calculations.beam_summary.beam_summary_types import (
    COMPLETION_REFINEMENT_PHASE,
    CREATED_PHASE,
    QUALITY_GRADE_A,
    QUALITY_GRADE_B,
    QUALITY_GRADE_C,
    QUALITY_GRADE_D,
    QUALITY_GRADE_UNKNOWN,
    QUALITY_REFINEMENT_PHASE,
    READINESS_BLOCKED,
    READINESS_EMPTY,
    READINESS_PARTIAL,
    READINESS_READY,
    BeamSummaryState,
)


class BeamSummarySummary:
    """Build project-level beam summary statistics."""

    @staticmethod
    def build(
        beams: List[dict[str, Any]],
        summary_records: List[dict[str, Any]],
        registry: dict[str, Any],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        calculated = [
            item for item in summary_records
            if item.get("determination_state") == BeamSummaryState.CALCULATED.value
        ]
        weights = [
            float(item.get("total_steel_weight_kg") or 0.0)
            for item in summary_records
        ]
        bar_counts = [int(item.get("bar_count") or 0) for item in summary_records]

        largest_beam = max(
            summary_records,
            key=lambda item: float(item.get("total_steel_weight_kg") or 0.0),
            default=None,
        )
        smallest_beam = min(
            [item for item in summary_records if float(item.get("total_steel_weight_kg") or 0.0) > 0.0],
            key=lambda item: float(item.get("total_steel_weight_kg") or 0.0),
            default=None,
        )
        longest_beam = max(
            summary_records,
            key=lambda item: int(item.get("largest_bar_length_mm") or 0),
            default=None,
        )

        diameter_distribution: dict[str, int] = {}
        shape_distribution: dict[str, int] = {}
        role_distribution: dict[str, int] = {}
        fabrication_state_distribution: dict[str, int] = {}
        engineering_state_distribution: dict[str, int] = {}

        for record in summary_records:
            fabrication_state_distribution[str(record.get("fabrication_state", ""))] = (
                fabrication_state_distribution.get(str(record.get("fabrication_state", "")), 0) + 1
            )
            engineering_state_distribution[str(record.get("engineering_state", ""))] = (
                engineering_state_distribution.get(str(record.get("engineering_state", "")), 0) + 1
            )
            for diameter in record.get("diameters") or []:
                key = str(diameter)
                diameter_distribution[key] = diameter_distribution.get(key, 0) + 1
            for shape in record.get("shape_codes") or []:
                key = str(shape)
                shape_distribution[key] = shape_distribution.get(key, 0) + 1
            for role in record.get("roles") or []:
                key = str(role)
                role_distribution[key] = role_distribution.get(key, 0) + 1

        total_bars = sum(bar_counts)
        beam_count = len(summary_records)

        engineering_ready_beams = 0
        partial_beams = 0
        blocked_beams = 0
        empty_beams = 0
        completion_percents: list[float] = []
        beam_completion_report: list[dict[str, Any]] = []

        for record in summary_records:
            completion = record.get("completion") or {}
            readiness = str(completion.get("readiness", ""))
            completion_percent = float(completion.get("completion_percent") or 0.0)
            completion_percents.append(completion_percent)
            if completion.get("engineering_ready"):
                engineering_ready_beams += 1
            if readiness == READINESS_PARTIAL:
                partial_beams += 1
            elif readiness == READINESS_BLOCKED:
                blocked_beams += 1
            elif readiness == READINESS_EMPTY:
                empty_beams += 1
            beam_completion_report.append({
                "beam_id": record.get("beam_id"),
                "beam_mark": record.get("beam_mark"),
                "bars_total": completion.get("bars_total", record.get("bar_count", 0)),
                "completion_percent": completion_percent,
                "readiness": readiness,
                "engineering_ready": bool(completion.get("engineering_ready")),
            })

        average_completion_percent = (
            round(sum(completion_percents) / len(completion_percents), 1)
            if completion_percents
            else 0.0
        )

        quality_grade_distribution = {
            QUALITY_GRADE_A: 0,
            QUALITY_GRADE_B: 0,
            QUALITY_GRADE_C: 0,
            QUALITY_GRADE_D: 0,
            QUALITY_GRADE_UNKNOWN: 0,
        }
        confidence_scores: list[float] = []
        quality_ready_beams = 0
        beam_quality_report: list[dict[str, Any]] = []
        highest_confidence_beam = None
        lowest_confidence_beam = None

        for record in summary_records:
            quality = record.get("quality") or {}
            confidence_score = float(quality.get("confidence_score") or 0.0)
            quality_grade = str(quality.get("quality_grade", QUALITY_GRADE_UNKNOWN))
            confidence_scores.append(confidence_score)
            quality_grade_distribution[quality_grade] = (
                quality_grade_distribution.get(quality_grade, 0) + 1
            )
            if quality.get("quality_ready"):
                quality_ready_beams += 1
            beam_quality_report.append({
                "beam_id": record.get("beam_id"),
                "beam_mark": record.get("beam_mark"),
                "confidence_score": confidence_score,
                "quality_grade": quality_grade,
                "quality_ready": bool(quality.get("quality_ready")),
                "source_diversity": quality.get("source_diversity", 0),
                "inference_count": quality.get("inference_count", 0),
            })
            if highest_confidence_beam is None or confidence_score > float(
                (highest_confidence_beam.get("quality") or {}).get("confidence_score") or 0.0
            ):
                highest_confidence_beam = record
            if lowest_confidence_beam is None or confidence_score < float(
                (lowest_confidence_beam.get("quality") or {}).get("confidence_score") or 0.0
            ):
                lowest_confidence_beam = record

        average_confidence_score = (
            round(sum(confidence_scores) / len(confidence_scores), 2)
            if confidence_scores
            else 0.0
        )

        return {
            "phase": "Phase I.12.2",
            "framework_phase": CREATED_PHASE,
            "completion_refinement_phase": COMPLETION_REFINEMENT_PHASE,
            "quality_refinement_phase": QUALITY_REFINEMENT_PHASE,
            "total_beams": len(beams),
            "total_summaries": beam_count,
            "total_bars": total_bars,
            "calculated_summaries": len(calculated),
            "partial_summaries": sum(
                1 for item in summary_records
                if item.get("determination_state") == BeamSummaryState.PARTIAL.value
            ),
            "blocked_summaries": sum(
                1 for item in summary_records
                if item.get("determination_state") == BeamSummaryState.BLOCKED.value
            ),
            "empty_summaries": sum(
                1 for item in summary_records
                if item.get("determination_state") == BeamSummaryState.EMPTY.value
            ),
            "average_bars_per_beam": round(total_bars / beam_count, 2) if beam_count else 0.0,
            "average_steel_weight_kg": round(sum(weights) / beam_count, 3) if beam_count else 0.0,
            "total_steel_weight_kg": round(sum(weights), 3),
            "largest_beam": largest_beam,
            "smallest_beam": smallest_beam,
            "beam_with_largest_steel_weight": largest_beam,
            "beam_with_longest_reinforcement": longest_beam,
            "diameter_distribution": dict(
                sorted(diameter_distribution.items(), key=lambda kv: float(kv[0]))
            ),
            "shape_distribution": dict(sorted(shape_distribution.items())),
            "role_distribution": dict(sorted(role_distribution.items())),
            "fabrication_state_distribution": dict(fabrication_state_distribution),
            "engineering_state_distribution": dict(engineering_state_distribution),
            "engineering_ready_beams": engineering_ready_beams,
            "partial_beams": partial_beams,
            "blocked_beams": blocked_beams,
            "empty_beams": empty_beams,
            "average_completion_percent": average_completion_percent,
            "beam_completion_report": beam_completion_report,
            "average_confidence_score": average_confidence_score,
            "quality_grade_distribution": quality_grade_distribution,
            "quality_ready_beams": quality_ready_beams,
            "highest_confidence_beam": highest_confidence_beam,
            "lowest_confidence_beam": lowest_confidence_beam,
            "beam_quality_report": beam_quality_report,
            "registry_statistics": {
                "namespace": registry.get("namespace"),
                "determination_count": registry.get("determination_count", 0),
                "state_counts": registry.get("state_counts", {}),
            },
            "validation_summary": {
                "status": validation.get("status", "SKIP"),
                "passed": validation.get("summary", {}).get("passed", 0),
                "failed": validation.get("summary", {}).get("failed", 0),
                "total_checks": validation.get("summary", {}).get("total_checks", 0),
            },
        }
