"""Build estimator interpretation from validated workbook — Phase QA.3."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from src.estimator_validation.comparison_utils import (
    beam_sort_key,
    find_schedule_start_row,
    load_workbook_pair,
    parse_schedule_rows,
)
from src.estimator_validation.drawing_interpretation.interpretation_types import (
    BeamInterpretation,
    EngineeringConcept,
)
from src.estimator_validation.object_trace.identity_matcher import (
    identity_from_estimator_row,
    role_from_description,
)


class EstimatorInterpretationBuilder:
    def build(self, estimator_workbook: Path, generated_workbook: Path) -> Dict[str, BeamInterpretation]:
        _, _, _, estimator_ws = load_workbook_pair(generated_workbook, estimator_workbook)
        start = find_schedule_start_row(estimator_ws)
        beams = parse_schedule_rows(estimator_ws, start)
        interpretations: Dict[str, BeamInterpretation] = {}
        for beam_mark in sorted(beams.keys(), key=beam_sort_key):
            block = beams[beam_mark]
            concepts: List[EngineeringConcept] = []
            for row in block.rows:
                identity = identity_from_estimator_row(beam_mark, row)
                role = identity.role if identity.role != "UNKNOWN" else role_from_description(row.description)
                concepts.append(
                    EngineeringConcept(
                        beam_mark=beam_mark,
                        concept_type=role,
                        role=role,
                        diameter_mm=row.diameter_mm,
                        quantity=row.bar_count,
                        spacing_mm=row.spacing_m * 1000 if row.spacing_m else None,
                        raw_callouts=[row.description],
                        description=row.description,
                        source_layer="estimator_workbook",
                    )
                )
            interpretations[beam_mark] = BeamInterpretation(
                beam_mark=beam_mark,
                raw_annotations=[row.description for row in block.rows],
                concepts=concepts,
            )
        return interpretations
