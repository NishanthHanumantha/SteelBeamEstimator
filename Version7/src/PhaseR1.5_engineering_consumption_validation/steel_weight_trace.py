"""Steel weight consumption trace — READ-ONLY."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple

from .engineering_bar_loader import EngineeringBarLoader
from .engineering_consumption_models import EngineeringBarTrace, SteelConsumptionTrace

SKIP_UNSUPPORTED_ROLE = "UNSUPPORTED_ROLE"
SKIP_ZERO_QUANTITY = "Zero quantity"
SKIP_NOT_IN_PRODUCTION = "No mapping in production model"
SKIP_ROLE_MAPPING = "ROLE_MAPPING_ERROR"
SKIP_FILTERED = "Filtered by steel module"
SKIP_MISSING_GEOMETRY = "Missing geometry"
SKIP_UNKNOWN = "UNKNOWN"


class SteelWeightTrace:

    def trace(self, loader: EngineeringBarLoader) -> Dict[str, SteelConsumptionTrace]:
        steel_bars = loader.all_steel_bars()
        consumed_indices: Set[int] = set()
        results: Dict[str, SteelConsumptionTrace] = {}
        signature_owner: Dict[str, str] = {}

        for trace in loader.traces:
            if trace.quantity <= 0:
                results[trace.trace_id] = SteelConsumptionTrace(
                    trace_id=trace.trace_id, consumed=False,
                    skip_reason=SKIP_ZERO_QUANTITY,
                )
                continue

            if trace.steel_role not in {
                "TOP_MAIN", "TOP_EXTRA", "BOTTOM_MAIN", "BOTTOM_EXTRA",
                "STIRRUP", "SPACER", "SIDE_FACE", "DEVELOPMENT", "LAP", "BENT",
            }:
                results[trace.trace_id] = SteelConsumptionTrace(
                    trace_id=trace.trace_id, consumed=False,
                    skip_reason=SKIP_UNSUPPORTED_ROLE,
                )
                continue

            sig = self._bar_signature(trace)
            matches = self._find_steel_matches(trace, steel_bars, consumed_indices)

            if not matches:
                owner_id = signature_owner.get(sig)
                if owner_id and results.get(owner_id, {}).consumed:
                    owner = results[owner_id]
                    results[trace.trace_id] = SteelConsumptionTrace(
                        trace_id=trace.trace_id,
                        consumed=True,
                        weight_kg=0.0,
                        unit_weight_kg=owner.unit_weight_kg,
                        cut_length_mm=owner.cut_length_mm,
                        formula_used=owner.formula_used,
                        steel_bar_id=owner.steel_bar_id,
                        skip_reason="DUPLICATE_EXPANSION",
                    )
                    continue
                reason = self._classify_skip(trace, loader)
                results[trace.trace_id] = SteelConsumptionTrace(
                    trace_id=trace.trace_id, consumed=False, skip_reason=reason,
                )
                continue

            primary = matches[0]
            bar, idx = primary
            consumed_indices.add(idx)
            for _, midx in matches[1:]:
                consumed_indices.add(midx)

            results[trace.trace_id] = SteelConsumptionTrace(
                trace_id=trace.trace_id,
                consumed=True,
                weight_kg=round(sum(m[0].total_weight_kg for m in matches), 4),
                unit_weight_kg=round(bar.weight_per_bar_kg, 4),
                cut_length_mm=bar.cut_length_mm,
                formula_used=bar.formula_used,
                steel_bar_id=bar.bar_id,
                skip_reason=(
                    "MULTIPLE_COUNTING" if len(matches) > 1 else ""
                ),
            )
            if sig not in signature_owner:
                signature_owner[sig] = trace.trace_id

        return results

    def _find_steel_matches(
        self,
        trace: EngineeringBarTrace,
        steel_bars: List[Tuple[Any, int]],
        consumed: Set[int],
    ) -> List[Tuple[Any, int]]:
        matches = []
        for bar, idx in steel_bars:
            if idx in consumed:
                continue
            if bar.beam_id != trace.beam_id:
                continue
            if bar.role != trace.steel_role:
                continue
            if int(bar.diameter_mm) != int(trace.diameter_mm):
                continue
            if trace.bar_label and bar.bar_label == trace.bar_label:
                matches.append((bar, idx))
            elif int(bar.quantity) == trace.quantity:
                matches.append((bar, idx))

        if not matches and trace.steel_role == "STIRRUP":
            for bar, idx in steel_bars:
                if idx in consumed:
                    continue
                if bar.beam_id == trace.beam_id and bar.role == "STIRRUP":
                    if int(bar.diameter_mm) == int(trace.diameter_mm):
                        matches.append((bar, idx))

        return matches

    @staticmethod
    def _bar_signature(trace: EngineeringBarTrace) -> str:
        return (
            f"{trace.beam_id}|{trace.steel_role}|{int(trace.diameter_mm)}|"
            f"{trace.quantity}|{trace.bar_label}"
        )

    def _classify_skip(
        self, trace: EngineeringBarTrace, loader: EngineeringBarLoader
    ) -> str:
        if not loader.bar_in_production_model(trace):
            return SKIP_NOT_IN_PRODUCTION
        model = loader.production_model_for_beam(trace.beam_id)
        if model:
            geom = model.get("geometry", {})
            if not geom.get("clear_span_mm"):
                return SKIP_MISSING_GEOMETRY
        from .engineering_bar_loader import ENG_ROLE_TO_STEEL
        if trace.bar_role not in ENG_ROLE_TO_STEEL:
            return SKIP_ROLE_MAPPING
        return SKIP_FILTERED
