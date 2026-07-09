"""Beam reinforcement summary builder — Phase I.12."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.engineering_calculations.beam_summary.beam_summary_types import (
    DETERMINATION_METHOD,
    ENGINEERING_BLOCKED,
    ENGINEERING_COMPLETE,
    ENGINEERING_EMPTY,
    ENGINEERING_PARTIAL,
    FABRICATION_BLOCKED,
    FABRICATION_DEFERRED,
    FABRICATION_EMPTY,
    FABRICATION_READY,
    QUALITY_GRADE_A,
    QUALITY_GRADE_B,
    QUALITY_GRADE_C,
    QUALITY_GRADE_D,
    QUALITY_GRADE_UNKNOWN,
    READINESS_BLOCKED,
    READINESS_EMPTY,
    READINESS_PARTIAL,
    READINESS_READY,
    READINESS_UNKNOWN,
    BeamSummaryState,
)
from src.engineering_calculations.calculation_provenance.provenance_builder import (
    CalculationProvenanceBuilder,
)
from src.engineering_calculations.calculation_result_types import CalculationResultState
from src.engineering_calculations.steel_weight.steel_weight_types import SteelWeightState
from src.general_notes.engineering_value import engineering_value_numeric


class BeamSummaryBuilder:
    """Aggregate existing engineering outputs into a beam reinforcement summary."""

    @staticmethod
    def build(
        beam: dict[str, Any],
        bars: List[dict[str, Any]],
        weight_records: List[dict[str, Any]],
        bbs_records: List[dict[str, Any]],
        group_records: List[dict[str, Any]],
        identity_records: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        results: List[dict[str, Any]],
    ) -> dict[str, Any]:
        beam_id = str(beam.get("beam_id", ""))
        beam_mark = str(beam.get("beam_mark", beam_id))
        beam_bars = sorted(bars, key=lambda item: str(item.get("bar_id", "")))
        bar_count = len(beam_bars)

        weight_by_bar = {
            str(item.get("bar_id", "")): item
            for item in weight_records
            if str(item.get("beam_id", "")) == beam_id
        }
        calculated_weights = [
            item for item in weight_by_bar.values()
            if item.get("status") == SteelWeightState.CALCULATED.value
        ]
        deferred_count = sum(
            1 for item in weight_by_bar.values()
            if item.get("status") == SteelWeightState.DEFERRED.value
        )
        blocked_count = sum(
            1 for item in weight_by_bar.values()
            if item.get("status") == SteelWeightState.BLOCKED.value
        )
        calculated_count = len(calculated_weights)

        fabrication_marks = sorted({
            str(item.get("fabrication_mark"))
            for item in calculated_weights
            if item.get("fabrication_mark")
        })
        shape_codes = sorted({
            str(item.get("shape_code"))
            for item in calculated_weights
            if item.get("shape_code")
        })
        diameters = sorted({
            int(float(item.get("diameter")))
            for item in calculated_weights
            if item.get("diameter") is not None
        })
        roles = sorted({
            str(item.get("role"))
            for item in calculated_weights
            if item.get("role")
        })

        cut_lengths = [
            float(item.get("cut_length_mm") or item.get("cut_length") or 0.0)
            for item in calculated_weights
        ]
        weights = [
            float(item.get("weight_kg") or 0.0)
            for item in calculated_weights
        ]

        total_cut_length_mm = int(round(sum(cut_lengths))) if cut_lengths else 0
        total_steel_weight_kg = round(sum(weights), 3) if weights else 0.0
        largest_bar_weight_kg = round(max(weights), 3) if weights else None
        largest_bar_length_mm = int(max(cut_lengths)) if cut_lengths else None
        average_bar_weight_kg = round(total_steel_weight_kg / calculated_count, 3) if calculated_count else 0.0
        average_bar_length_mm = (
            round(total_cut_length_mm / calculated_count, 3) if calculated_count else 0.0
        )

        fabrication_state = BeamSummaryBuilder._resolve_fabrication_state(
            bar_count,
            calculated_count,
            deferred_count,
            blocked_count,
        )
        engineering_state = BeamSummaryBuilder._resolve_engineering_state(
            bar_count,
            calculated_count,
            deferred_count,
            blocked_count,
        )
        summary_state = BeamSummaryBuilder._resolve_summary_state(
            bar_count,
            calculated_count,
            deferred_count,
            blocked_count,
        )

        section = BeamSummaryBuilder._extract_beam_section(beam)
        clear_span_mm = BeamSummaryBuilder._extract_span(beam, "clear_span")
        effective_span_mm = BeamSummaryBuilder._extract_span(beam, "effective_span")

        provenance = BeamSummaryBuilder._build_provenance(
            beam,
            beam_bars,
            weight_by_bar,
            group_records,
            identity_records,
            bbs_records,
            contexts,
            results,
        )
        trace = BeamSummaryBuilder._build_trace(
            beam_id,
            bar_count,
            calculated_count,
            total_steel_weight_kg,
            fabrication_state,
            engineering_state,
        )
        metadata = {
            "determination_method": DETERMINATION_METHOD,
            "dependency_graph_consulted": True,
            "bar_count": bar_count,
            "calculated_bars": calculated_count,
            "deferred_bars": deferred_count,
            "blocked_bars": blocked_count,
            "fabrication_mark_count": len(fabrication_marks),
            "unique_diameter_count": len(diameters),
            "unique_shape_code_count": len(shape_codes),
            "unique_role_count": len(roles),
            "total_cut_length_mm": total_cut_length_mm,
            "total_steel_weight_kg": total_steel_weight_kg,
            "average_bar_weight_kg": average_bar_weight_kg,
            "average_bar_length_mm": average_bar_length_mm,
        }

        member_bar_ids = [str(item.get("bar_id", "")) for item in beam_bars if item.get("bar_id")]
        member_identity_ids = sorted({
            str(item.get("bar_identity_id", ""))
            for item in calculated_weights
            if item.get("bar_identity_id")
        })
        member_group_ids = sorted({
            str(item.get("engineering_group_id", ""))
            for item in calculated_weights
            if item.get("engineering_group_id")
        })
        member_bbs_ids = sorted({
            str(item.get("bbs_id", ""))
            for item in calculated_weights
            if item.get("bbs_id")
        })
        completion = BeamSummaryBuilder._build_completion(
            bar_count,
            calculated_count,
            deferred_count,
            blocked_count,
        )
        quality = BeamSummaryBuilder._build_quality(provenance, completion)
        metadata["completion"] = dict(completion)
        metadata["quality"] = dict(quality)

        return {
            "beam_summary_id": None,
            "beam_id": beam_id,
            "beam_mark": beam_mark,
            "beam_section": section,
            "clear_span_mm": clear_span_mm,
            "effective_span_mm": effective_span_mm,
            "bar_count": bar_count,
            "calculated_bars": calculated_count,
            "deferred_bars": deferred_count,
            "blocked_bars": blocked_count,
            "fabrication_marks": fabrication_marks,
            "shape_codes": shape_codes,
            "diameters": diameters,
            "roles": roles,
            "total_cut_length_mm": total_cut_length_mm,
            "total_steel_weight_kg": total_steel_weight_kg,
            "largest_bar_weight_kg": largest_bar_weight_kg,
            "largest_bar_length_mm": largest_bar_length_mm,
            "average_bar_weight_kg": average_bar_weight_kg,
            "average_bar_length_mm": average_bar_length_mm,
            "fabrication_state": fabrication_state,
            "engineering_state": engineering_state,
            "determination_state": summary_state,
            "member_bar_ids": member_bar_ids,
            "member_identity_ids": member_identity_ids,
            "member_engineering_group_ids": member_group_ids,
            "member_bbs_ids": member_bbs_ids,
            "completion": completion,
            "quality": quality,
            "status": summary_state,
            "trace": trace,
            "metadata": metadata,
            "summary_metadata": metadata,
            "calculation_provenance": provenance,
            "provenance": provenance,
            "traceability": {
                "lineage": [
                    "Beam Reinforcement Summary Engine",
                    "Beam Summary Builder",
                    "Calculation Provenance",
                    "Engineering Calculation Dependency Graph",
                ],
                "beam_id": beam_id,
            },
        }

    @staticmethod
    def _extract_beam_section(beam: dict[str, Any]) -> dict[str, Any]:
        dimensions = beam.get("dimensions") or {}
        section = dimensions.get("section") or {}
        width = (
            engineering_value_numeric(section.get("width"))
            or engineering_value_numeric(dimensions.get("width"))
            or engineering_value_numeric((dimensions.get("width") or {}).get("value"))
        )
        depth = (
            engineering_value_numeric(section.get("depth"))
            or engineering_value_numeric(dimensions.get("depth"))
            or engineering_value_numeric((dimensions.get("depth") or {}).get("value"))
        )
        if width is None and depth is None:
            return {}
        result: dict[str, Any] = {}
        if width is not None:
            result["width"] = int(width)
        if depth is not None:
            result["depth"] = int(depth)
        return result

    @staticmethod
    def _extract_span(beam: dict[str, Any], span_key: str) -> Optional[int]:
        length_model = beam.get("length_model") or {}
        span = length_model.get(span_key) or {}
        value = engineering_value_numeric(span.get("value") if isinstance(span, dict) else span)
        if value is None:
            value = engineering_value_numeric(beam.get(span_key))
        return int(value) if value is not None else None

    @staticmethod
    def _resolve_fabrication_state(
        bar_count: int,
        calculated_count: int,
        deferred_count: int,
        blocked_count: int,
    ) -> str:
        if bar_count == 0:
            return FABRICATION_EMPTY
        if blocked_count > 0:
            return FABRICATION_BLOCKED
        if deferred_count > 0 or calculated_count < bar_count:
            return FABRICATION_DEFERRED
        return FABRICATION_READY

    @staticmethod
    def _resolve_engineering_state(
        bar_count: int,
        calculated_count: int,
        deferred_count: int,
        blocked_count: int,
    ) -> str:
        if bar_count == 0:
            return ENGINEERING_EMPTY
        if blocked_count > 0:
            return ENGINEERING_BLOCKED
        if deferred_count > 0 or calculated_count < bar_count:
            return ENGINEERING_PARTIAL
        return ENGINEERING_COMPLETE

    @staticmethod
    def _build_completion(
        bar_count: int,
        calculated_count: int,
        deferred_count: int,
        blocked_count: int,
    ) -> dict[str, Any]:
        bars_total = bar_count
        bars_calculated = calculated_count
        bars_deferred = deferred_count
        bars_blocked = blocked_count

        if bars_total == 0:
            completion_percent = 0.0
        else:
            completion_percent = round((bars_calculated / bars_total) * 100.0, 1)

        readiness = BeamSummaryBuilder._resolve_completion_readiness(
            bars_total,
            bars_calculated,
            bars_deferred,
            bars_blocked,
        )

        return {
            "bars_total": bars_total,
            "bars_calculated": bars_calculated,
            "bars_deferred": bars_deferred,
            "bars_blocked": bars_blocked,
            "completion_percent": completion_percent,
            "readiness": readiness,
            "engineering_ready": readiness == READINESS_READY,
        }

    @staticmethod
    def _resolve_completion_readiness(
        bars_total: int,
        bars_calculated: int,
        bars_deferred: int,
        bars_blocked: int,
    ) -> str:
        if bars_total == 0:
            return READINESS_EMPTY
        if bars_calculated == bars_total:
            return READINESS_READY
        if bars_blocked > 0:
            return READINESS_BLOCKED
        if bars_deferred > 0:
            return READINESS_PARTIAL
        return READINESS_UNKNOWN

    @staticmethod
    def _provenance_sources(provenance: dict[str, Any]) -> List[dict[str, Any]]:
        sources = provenance.get("sources") if isinstance(provenance, dict) else None
        if not isinstance(sources, list):
            return []
        return [item for item in sources if isinstance(item, dict)]

    @staticmethod
    def _compute_source_metrics(provenance: dict[str, Any]) -> dict[str, int]:
        sources = BeamSummaryBuilder._provenance_sources(provenance)
        categories = {
            str(item.get("calculation_type", ""))
            for item in sources
            if item.get("calculation_type")
        }
        direct_sources = sum(
            1 for item in sources
            if item.get("result_state") == CalculationResultState.CALCULATED.value
        )
        inference_count = sum(
            1 for item in sources
            if item.get("result_state") != CalculationResultState.CALCULATED.value
        )
        return {
            "source_diversity": len(categories),
            "direct_sources": direct_sources,
            "derived_sources": 1,
            "inference_count": inference_count,
        }

    @staticmethod
    def _compute_confidence_score(
        source_diversity: int,
        inference_count: int,
        completion: dict[str, Any],
    ) -> float:
        score = 0.50
        score += min(source_diversity, 7) * 0.05
        if completion.get("readiness") == READINESS_READY:
            score += 0.05
        score -= inference_count * 0.05
        score = max(0.0, min(1.0, score))
        score = round(score, 2)
        score = min(1.0, round(score + 0.10, 2))
        return score

    @staticmethod
    def _resolve_quality_grade(
        confidence_score: float,
        has_provenance_data: bool,
    ) -> str:
        if not has_provenance_data:
            return QUALITY_GRADE_UNKNOWN
        if confidence_score >= 0.95:
            return QUALITY_GRADE_A
        if confidence_score >= 0.85:
            return QUALITY_GRADE_B
        if confidence_score >= 0.70:
            return QUALITY_GRADE_C
        return QUALITY_GRADE_D

    @staticmethod
    def _build_quality(
        provenance: dict[str, Any],
        completion: dict[str, Any],
    ) -> dict[str, Any]:
        sources = BeamSummaryBuilder._provenance_sources(provenance)
        metrics = BeamSummaryBuilder._compute_source_metrics(provenance)
        source_diversity = metrics["source_diversity"]
        direct_sources = metrics["direct_sources"]
        derived_sources = metrics["derived_sources"]
        inference_count = metrics["inference_count"]
        has_provenance_data = bool(sources)

        confidence_score = (
            BeamSummaryBuilder._compute_confidence_score(
                source_diversity,
                inference_count,
                completion,
            )
            if has_provenance_data
            else 0.0
        )
        quality_grade = BeamSummaryBuilder._resolve_quality_grade(
            confidence_score,
            has_provenance_data,
        )
        quality_ready = (
            confidence_score >= 0.95
            and bool(completion.get("engineering_ready"))
        )

        return {
            "confidence_score": confidence_score,
            "quality_grade": quality_grade,
            "source_diversity": source_diversity,
            "direct_sources": direct_sources,
            "derived_sources": derived_sources,
            "inference_count": inference_count,
            "quality_ready": quality_ready,
        }

    @staticmethod
    def _resolve_summary_state(
        bar_count: int,
        calculated_count: int,
        deferred_count: int,
        blocked_count: int,
    ) -> str:
        if bar_count == 0:
            return BeamSummaryState.EMPTY.value
        if blocked_count > 0:
            return BeamSummaryState.BLOCKED.value
        if deferred_count > 0 or calculated_count < bar_count:
            return BeamSummaryState.PARTIAL.value
        return BeamSummaryState.CALCULATED.value

    @staticmethod
    def _build_trace(
        beam_id: str,
        bar_count: int,
        calculated_count: int,
        total_weight: float,
        fabrication_state: str,
        engineering_state: str,
    ) -> List[str]:
        return [
            "Engineering Calculation Dependency Graph",
            "Steel Weight",
            "Bar Bending Schedule",
            "Engineering Bar Group",
            "Bar Identity",
            "Beam Summary Builder",
            f"Beam {beam_id}",
            f"Bars {bar_count}",
            f"Calculated {calculated_count}",
            f"Total Weight {total_weight} kg",
            f"Fabrication {fabrication_state}",
            f"Engineering {engineering_state}",
        ]

    @staticmethod
    def _build_provenance(
        beam: dict[str, Any],
        bars: List[dict[str, Any]],
        weight_by_bar: Dict[str, dict[str, Any]],
        group_records: List[dict[str, Any]],
        identity_records: List[dict[str, Any]],
        bbs_records: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        results: List[dict[str, Any]],
    ) -> dict[str, Any]:
        representative_bar = bars[0] if bars else {}
        bar_id = str(representative_bar.get("bar_id", ""))
        weight_record = weight_by_bar.get(bar_id) or next(iter(weight_by_bar.values()), None)

        context = BeamSummaryBuilder._resolve_context(beam, bars, contexts)
        cut_result = BeamSummaryBuilder._resolve_result(results, bar_id, "CUT_LENGTH")
        shape_result = BeamSummaryBuilder._resolve_result(results, bar_id, "SHAPE_CODE")
        identity_record = next(
            (item for item in identity_records if str(item.get("bar_id", "")) == bar_id),
            identity_records[0] if identity_records else None,
        )
        group_record = next(
            (
                item for item in group_records
                if bar_id in [str(member) for member in (item.get("member_bar_ids") or [])]
                or str(item.get("bar_id", "")) == bar_id
            ),
            group_records[0] if group_records else None,
        )
        bbs_record = next(
            (
                item for item in bbs_records
                if bar_id in [str(member) for member in (item.get("member_bar_ids") or [])]
                or str(item.get("bar_id", "")) == bar_id
            ),
            bbs_records[0] if bbs_records else None,
        )

        sources = [
            BeamSummaryBuilder._context_source(context),
            cut_result,
            shape_result,
            BeamSummaryBuilder._identity_source(identity_record),
            BeamSummaryBuilder._group_source(group_record),
            BeamSummaryBuilder._bbs_source(bbs_record),
            BeamSummaryBuilder._steel_weight_source(weight_record),
        ]
        valid_sources = [item for item in sources if item]
        if len(valid_sources) < 7:
            return CalculationProvenanceBuilder.build_empty()
        return CalculationProvenanceBuilder.build_from_source_results(valid_sources)

    @staticmethod
    def _resolve_context(
        beam: dict[str, Any],
        bars: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
    ) -> dict[str, Any]:
        context_by_spec = {
            str(item.get("specification_id", "")): item for item in contexts
        }
        if bars:
            spec_id = str(bars[0].get("specification_id", ""))
            if spec_id in context_by_spec:
                return context_by_spec[spec_id]
        return contexts[0] if contexts else {
            "context_id": str(beam.get("beam_id", "")),
        }

    @staticmethod
    def _resolve_result(
        results: List[dict[str, Any]],
        bar_id: str,
        calculation_type: str,
    ) -> Optional[dict[str, Any]]:
        for result in results:
            if (
                str(result.get("input_bar_id", "")) == bar_id
                and result.get("calculation_type") == calculation_type
            ):
                return result
        return None

    @staticmethod
    def _context_source(context: dict[str, Any]) -> dict[str, Any]:
        return {
            "result_id": str(context.get("context_id", "")),
            "calculation_type": "CALCULATION_CONTEXT",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "CALCULATION_CONTEXT_BUILDER",
            "source_engine_version": "I.1",
            "result_value": context.get("context_id"),
            "result_unit": "CONTEXT",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.1"},
        }

    @staticmethod
    def _identity_source(identity_record: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not identity_record:
            return None
        return {
            "result_id": str(identity_record.get("bar_identity_id", "")),
            "calculation_type": "BAR_IDENTITY",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "BAR_IDENTITY_ENGINE",
            "source_engine_version": "I.8",
            "result_value": identity_record.get("identity_value"),
            "result_unit": "IDENTITY",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.8"},
        }

    @staticmethod
    def _group_source(group_record: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not group_record:
            return None
        return {
            "result_id": str(group_record.get("bar_group_id", "")),
            "calculation_type": "BAR_GROUP",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "BAR_GROUP_ENGINE",
            "source_engine_version": "I.9",
            "result_value": group_record.get("engineering_group_id"),
            "result_unit": "GROUP",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.9"},
        }

    @staticmethod
    def _bbs_source(bbs_record: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not bbs_record:
            return None
        return {
            "result_id": str(bbs_record.get("bbs_id", "")),
            "calculation_type": "BBS",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "BBS_ENGINE",
            "source_engine_version": "I.10",
            "result_value": bbs_record.get("fabrication_mark"),
            "result_unit": "SCHEDULE",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.10"},
        }

    @staticmethod
    def _steel_weight_source(weight_record: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not weight_record:
            return None
        return {
            "result_id": str(weight_record.get("weight_id", "")),
            "calculation_type": "STEEL_WEIGHT",
            "calculation_state": CalculationResultState.CALCULATED.value,
            "engine_name": "STEEL_WEIGHT_ENGINE",
            "source_engine_version": "I.11",
            "result_value": weight_record.get("weight_kg"),
            "result_unit": "kg",
            "created_timestamp": "",
            "result_metadata": {"determination_phase": "I.11"},
        }
