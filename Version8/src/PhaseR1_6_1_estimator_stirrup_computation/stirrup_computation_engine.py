"""
Orchestrate end-to-end estimator stirrup computation for one beam/label.
MODEL_VERSION: 8.8.1
"""
from __future__ import annotations

from typing import Optional

from cut_length_engine import CutLengthEngine
from general_notes_adapter import GeneralNotesAdapter
from hook_engine import HookEngine
from perimeter_engine import PerimeterEngine
from quantity_engine import QuantityEngine
from stirrup_model import StirrupComputation, StirrupNotation
from stirrup_notation_parser import StirrupNotationParser
from weight_engine import WeightEngine
from zone_builder import ZoneBuilder

MODEL_VERSION = "8.8.1"


class StirrupComputationEngine:
    def __init__(self, gn: GeneralNotesAdapter):
        self._gn = gn
        self._parser = StirrupNotationParser()
        self._zones = ZoneBuilder()
        self._qty = QuantityEngine()
        self._perimeter = PerimeterEngine()
        self._hooks = HookEngine(gn)
        self._cut = CutLengthEngine()
        self._weight = WeightEngine()

    def compute(
        self,
        beam_id: str,
        label: str,
        beam_length_mm: float,
        beam_width_mm: float,
        beam_depth_mm: float,
        cover_mm: Optional[float] = None,
        notation: Optional[StirrupNotation] = None,
        source_intent_id: str = "",
        source_detail_id: str = "",
    ) -> StirrupComputation:
        notation = notation or self._parser.parse(label)
        if notation is None:
            raise ValueError(f"Unable to parse stirrup notation: {label!r}")

        cover = float(cover_mm) if cover_mm is not None else float(self._gn.clear_cover_mm())
        zones = self._zones.build(beam_length_mm, notation.spacing_values_mm)
        total_qty = self._qty.total_from_zones(zones)
        perimeter = self._perimeter.compute(beam_width_mm, beam_depth_mm, cover)
        hook = self._hooks.compute(notation.diameter_mm)
        cut = self._cut.compute(perimeter, hook, hook_count=2)
        total_m, uw, weight = self._weight.compute(cut, total_qty, notation.diameter_mm)

        return StirrupComputation(
            beam_id=beam_id,
            label=label,
            notation=notation,
            beam_length_mm=float(beam_length_mm),
            beam_width_mm=float(beam_width_mm),
            beam_depth_mm=float(beam_depth_mm),
            cover_mm=cover,
            zones=zones,
            total_quantity=total_qty,
            perimeter_mm=round(perimeter, 3),
            hook=hook,
            cut_length_mm=round(cut, 3),
            total_length_m=total_m,
            unit_weight_kg_per_m=uw,
            weight_kg=weight,
            source_intent_id=source_intent_id,
            source_detail_id=source_detail_id,
        )
