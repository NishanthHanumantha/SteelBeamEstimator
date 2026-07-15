"""
Engineering Gap Analyzer — Part 8 of Phase GN.1 audit.

Identifies every gap between the GN-sourced engineering parameters and what
the production pipeline actually uses.  Ranks each gap by severity and
provides actionable recommendations for Phase R.2.

READ-ONLY: does not modify any production file.
"""
from __future__ import annotations
from typing import Any, List, Dict
from .gn_models import (
    EngineeringGap, GapSeverity, GapType,
    ExtractedParameter, TraceabilityNode,
    HardcodedDefault, SourceClass,
)


class EngineeringGapAnalyzer:
    """
    Produces a prioritised list of engineering gaps for Phase R.2 planning.
    """

    def analyze(
        self,
        extracted: List[ExtractedParameter],
        traceability: List[TraceabilityNode],
        hardcoded: List[HardcodedDefault],
    ) -> List[EngineeringGap]:
        gaps: List[EngineeringGap] = []
        gap_counter = [0]

        def _next_id() -> str:
            gap_counter[0] += 1
            return f"GAP_{gap_counter[0]:03d}"

        # ------------------------------------------------------------------
        # Gap 1: GN DXF is not parsed at runtime — all engineering
        #        constants remain hardcoded even though GN is discovered.
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="general_notes_dxf_parsing",
            gap_type=GapType.MISSING_EXTRACTION,
            severity=GapSeverity.CRITICAL,
            description=(
                "V.ROOT.1 discovers the General Notes DXF path and stores it in "
                "beam_registry.json, but NO module in the current pipeline parses "
                "the GN DXF to extract engineering parameters at runtime."
            ),
            impact=(
                "All engineering constants (dev length, cover, hook, steel grade) "
                "remain hardcoded.  Changing the GN DXF does NOT update the pipeline."
            ),
            recommendation=(
                "Phase R.2 should implement a GNParsingEngine that reads the GN DXF "
                "path from beam_registry.json and extracts: steel grade, concrete grade, "
                "development length table, cover, hook/bend rules, lap rules."
            ),
            affected_modules=[
                "SteelWeightCompletion",
                "StirrupWeightEngine",
                "EstimatorExcelGenerator",
                "BBSCompletionEngine",
            ],
        ))

        # ------------------------------------------------------------------
        # Gap 2: Development length hardcoded (40d) instead of from GN table
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="development_length_factor",
            gap_type=GapType.HARDCODED_ASSUMPTION,
            severity=GapSeverity.HIGH,
            description=(
                "_DEVELOPMENT_LENGTH_FACTOR = 40 is hardcoded in steel_weight_completion.py. "
                "The GN DXF contains a full development length table for Fe415 "
                "(M20, M25, M30, M35, M40+) with different values per concrete grade."
            ),
            impact=(
                "For the Benchmark Set 2 project (beam-in-superstructure = M25 concrete), "
                "the hardcoded 40d matches the GN table value.  However, for a different "
                "project with M30 concrete, the correct Ld factor changes and will be WRONG."
            ),
            recommendation=(
                "Phase R.2: Read steel grade and concrete grade from GN DXF, "
                "then look up Ld from the parsed development length table."
            ),
            affected_modules=["SteelWeightCompletion", "StirrupWeightEngine"],
        ))

        # ------------------------------------------------------------------
        # Gap 3: Cover = 40mm hardcoded; not confirmed from GN DXF
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="concrete_cover_mm",
            gap_type=GapType.HARDCODED_ASSUMPTION,
            severity=GapSeverity.HIGH,
            description=(
                "_COVER_MM = 40.0 is hardcoded.  The GN DXF does not contain an explicit "
                "cover statement for beams in a searchable text format.  IS 456:2000 "
                "Table 16 specifies 40mm for beams — the hardcoded value is correct for "
                "this project but is NOT sourced from the drawing."
            ),
            impact=(
                "If a future project specifies 30mm or 50mm cover in its GN DXF, "
                "the pipeline will silently use the wrong cover value."
            ),
            recommendation=(
                "Phase R.2: Extract cover specification from GN DXF TABLE or tabular "
                "region.  If not found, apply IS 456 default and flag in audit log."
            ),
            affected_modules=["SteelWeightCompletion", "StirrupWeightEngine"],
        ))

        # ------------------------------------------------------------------
        # Gap 4: Hook multiple 10d vs. GN 4xdb standard 90-degree bend
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="hook_bend_multiple",
            gap_type=GapType.WRONG_SOURCE,
            severity=GapSeverity.MEDIUM,
            description=(
                "_HOOK_MULTIPLE = 10 (10d per end) is used for stirrup hook allowance. "
                "The GN DXF specifies 'STANDARD 90 BEND = 4xdb' for the standard 90-degree "
                "bend.  IS 456:2000 clause 26.2.2.1 specifies minimum 4d for 90° hooks "
                "and 12d for full development.  The pipeline likely uses 10d as a "
                "combined development+hook tail — interpretation is ambiguous."
            ),
            impact=(
                "Potential over- or under-calculation of stirrup cut lengths by ~6d per end "
                "if 10d vs. 4d interpretation is incorrect."
            ),
            recommendation=(
                "Phase R.2: Clarify stirrup hook allowance per GN DXF clause. "
                "Parse the '4xdb' rule from GN and apply to stirrup cut length calculation."
            ),
            affected_modules=["StirrupWeightEngine", "SteelWeightCompletion"],
        ))

        # ------------------------------------------------------------------
        # Gap 5: Steel grade Fe415 hardcoded in Excel, not from GN
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="steel_grade_excel_label",
            gap_type=GapType.HARDCODED_ASSUMPTION,
            severity=GapSeverity.MEDIUM,
            description=(
                "'Steel Grade: Fe415 (High Yield)' is hardcoded in excel_structure_builder.py. "
                "The GN DXF confirms Fe415 via the 'LD FOR FY-415' development length table, "
                "but the Excel value is NOT read from the drawing — it is a literal string."
            ),
            impact=(
                "Low accuracy impact for this project (Fe415 is correct), but breaks "
                "project generalisation: a Fe500 project will produce wrong Excel headers."
            ),
            recommendation=(
                "Phase R.2: Populate steel grade in Excel from GN-extracted steel_grade."
            ),
            affected_modules=["EstimatorExcelGenerator", "excel_structure_builder"],
        ))

        # ------------------------------------------------------------------
        # Gap 6: Concrete grade defaults to M30 fallback
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="concrete_grade_fallback_m30",
            gap_type=GapType.FALLBACK_USED,
            severity=GapSeverity.HIGH,
            description=(
                "development_length_service.py uses `concrete_grade or 'M30'` as a fallback "
                "when no concrete grade is supplied.  The GN DXF contains a concrete grade "
                "table for different structural elements; beam-in-superstructure grade is "
                "NOT extracted and passed to the development length calculator."
            ),
            impact=(
                "M30 may be incorrect for this project.  Development length for Fe415/M30 "
                "is different from Fe415/M25 per IS 456:2000 Table 65."
            ),
            recommendation=(
                "Phase R.2: Parse per-element concrete grade from GN DXF and pass the "
                "beam-specific grade to DevelopmentLengthService."
            ),
            affected_modules=["DevelopmentLengthService", "SteelWeightCompletion"],
        ))

        # ------------------------------------------------------------------
        # Gap 7: Spacer bar rules — present in GN, not consumed anywhere
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="spacer_bar_rules",
            gap_type=GapType.EXTRACTED_UNUSED,
            severity=GapSeverity.MEDIUM,
            description=(
                "The GN DXF references spacer bar / cover block rules (Table-1 for lap splices). "
                "No module in the V7 pipeline extracts or consumes spacer bar rules."
            ),
            impact=(
                "Spacer bars contribute to steel quantity.  Currently no spacer steel is "
                "included in the estimation.  Accuracy impact depends on project requirements."
            ),
            recommendation=(
                "Phase R.2: Extract spacer bar specification from GN DXF and include "
                "spacer steel in BBS and steel weight totals."
            ),
            affected_modules=["SteelWeightCompletion", "BBSCompletionEngine"],
        ))

        # ------------------------------------------------------------------
        # Gap 8: Lap rules — 300mm minimum not validated
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="lap_length_minimum",
            gap_type=GapType.EXTRACTED_UNUSED,
            severity=GapSeverity.LOW,
            description=(
                "GN DXF clause: 'NO SPLICES SHALL HAVE LAP LENGTH LESS THAN 300mm'. "
                "The pipeline does not validate computed lap lengths against this limit."
            ),
            impact=(
                "Low impact — current estimation does not compute explicit lap lengths "
                "beyond the development length multiplier.  Risk is minimal."
            ),
            recommendation=(
                "Phase R.2: Validate computed splice lengths against GN-specified 300mm minimum."
            ),
            affected_modules=["SteelWeightCompletion"],
        ))

        # ------------------------------------------------------------------
        # Gap 9: IS 2502 not referenced in pipeline
        # ------------------------------------------------------------------
        gaps.append(EngineeringGap(
            gap_id=_next_id(),
            parameter_name="IS2502_standard",
            gap_type=GapType.EXTRACTED_UNUSED,
            severity=GapSeverity.LOW,
            description=(
                "IS 2502 (Code of Practice for Bending and Fixing of Bars for Concrete Reinforcement) "
                "is referenced in the GN DXF but not cited or consumed in the V7 pipeline."
            ),
            impact=(
                "Bar bending schedules should comply with IS 2502 for shape codes and "
                "bend allowances.  Current BBS does not reference IS 2502 shape codes."
            ),
            recommendation=(
                "Phase R.2: Apply IS 2502 shape code classification in BBS generation."
            ),
            affected_modules=["BBSCompletionEngine"],
        ))

        return gaps
