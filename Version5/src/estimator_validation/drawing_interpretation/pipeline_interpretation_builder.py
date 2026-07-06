"""Build pipeline interpretation from engineering JSON — Phase QA.3."""

from __future__ import annotations

from typing import Any, Dict, List

from src.estimator_validation.drawing_interpretation.interpretation_types import (
    BeamInterpretation,
    EngineeringConcept,
)


class PipelineInterpretationBuilder:
    def build(self, data: dict[str, Any], beam_marks: List[str]) -> Dict[str, BeamInterpretation]:
        interpretations: Dict[str, BeamInterpretation] = {}
        for beam_mark in beam_marks:
            concepts: List[EngineeringConcept] = []
            seen: set[str] = set()

            def add_concept(concept: EngineeringConcept) -> None:
                key = concept.concept_key()
                if key in seen:
                    return
                seen.add(key)
                concepts.append(concept)

            schedule = data["schedules_by_beam"].get(beam_mark, {})
            for row in schedule.get("rows") or []:
                add_concept(
                    EngineeringConcept(
                        beam_mark=beam_mark,
                        concept_type=str(row.get("role") or "UNKNOWN"),
                        role=str(row.get("role") or "UNKNOWN"),
                        diameter_mm=float(row["diameter_mm"]) if row.get("diameter_mm") is not None else None,
                        quantity=float(row["bar_count"]) if row.get("bar_count") is not None else None,
                        spacing_mm=float(row["spacing_mm"]) if row.get("spacing_mm") is not None else None,
                        raw_callouts=[str(row.get("description") or "")],
                        description=str(row.get("description") or ""),
                        source_layer="beam_schedule",
                    )
                )

            report = data["reports_by_beam"].get(beam_mark, {})
            for row in report.get("sections", {}).get("schedule_table") or []:
                add_concept(
                    EngineeringConcept(
                        beam_mark=beam_mark,
                        concept_type=str(row.get("role") or "UNKNOWN"),
                        role=str(row.get("role") or "UNKNOWN"),
                        diameter_mm=float(row["diameter_mm"]) if row.get("diameter_mm") is not None else None,
                        quantity=float(row["bar_count"]) if row.get("bar_count") is not None else None,
                        spacing_mm=float(row["spacing_mm"]) if row.get("spacing_mm") is not None else None,
                        raw_callouts=[str(row.get("description") or "")],
                        description=str(row.get("description") or ""),
                        source_layer="engineering_report",
                    )
                )

            for record in data["bar_identities"]:
                if str(record.get("beam_id") or record.get("beam_mark")) != beam_mark:
                    continue
                add_concept(
                    EngineeringConcept(
                        beam_mark=beam_mark,
                        concept_type=str(record.get("reinforcement_role") or "UNKNOWN"),
                        role=str(record.get("reinforcement_role") or "UNKNOWN"),
                        diameter_mm=float(record["bar_diameter_mm"])
                        if record.get("bar_diameter_mm") is not None
                        else None,
                        raw_callouts=[str(record.get("engineering_bar_mark") or "")],
                        description=str(record.get("engineering_bar_mark") or ""),
                        source_layer="bar_identity",
                    )
                )

            for record in data["bar_groups"]:
                member_beams = [str(item) for item in (record.get("member_beams") or [])]
                if beam_mark not in member_beams:
                    continue
                roles = record.get("member_roles") or ["UNKNOWN"]
                diameter = record.get("diameter")
                for role in roles:
                    add_concept(
                        EngineeringConcept(
                            beam_mark=beam_mark,
                            concept_type=str(role),
                            role=str(role),
                            diameter_mm=float(diameter) if diameter is not None else None,
                            raw_callouts=[str(record.get("fabrication_mark") or "")],
                            description=str(record.get("fabrication_mark") or ""),
                            source_layer="bar_group",
                        )
                    )

            for bar in self._bars_for_beam(data, beam_mark):
                callout = ""
                trace = bar.get("traceability") or {}
                if isinstance(trace, dict):
                    callout = str(trace.get("callout") or "")
                add_concept(
                    EngineeringConcept(
                        beam_mark=beam_mark,
                        concept_type=str(bar.get("role") or "UNKNOWN"),
                        role=str(bar.get("role") or "UNKNOWN"),
                        diameter_mm=float(bar["diameter_mm"]) if bar.get("diameter_mm") is not None else None,
                        quantity=float(bar["quantity"]) if bar.get("quantity") is not None else None,
                        raw_callouts=[callout] if callout else [],
                        description=callout or str(bar.get("role") or ""),
                        source_layer="reinforcement_objects",
                    )
                )

            interpretations[beam_mark] = BeamInterpretation(
                beam_mark=beam_mark,
                raw_annotations=[item.description or "" for item in concepts],
                concepts=concepts,
            )
        return interpretations

    @staticmethod
    def _bars_for_beam(data: dict[str, Any], beam_mark: str) -> List[dict[str, Any]]:
        payload = data.get("reinforcement_objects") or {}
        return [item for item in (payload.get("bars") or []) if str(item.get("beam_id")) == beam_mark]
