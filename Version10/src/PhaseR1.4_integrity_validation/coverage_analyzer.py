"""Generalized coverage analysis — no hardcoded project constants."""
from __future__ import annotations
from typing import Any, Dict, List, Set

from .pipeline_data_loader import PipelineDataLoader


class CoverageAnalyzer:

    def analyze(self, loader: PipelineDataLoader) -> Dict[str, Any]:
        registry_ids = loader.registry_beam_ids()
        eng_ids = loader.engineering_beam_ids()
        r1_ids = loader.r1_beam_ids()

        beams_with_bars: Set[str] = set()
        total_bars = 0
        role_dist: Dict[str, int] = {}
        dia_dist: Dict[str, int] = {}
        orphan_groups = 0

        for beam in loader.engineering_beams():
            bid = beam.get("beam_id")
            bars = beam.get("bars", [])
            if bars:
                beams_with_bars.add(bid)
            total_bars += len(bars)
            for bar in bars:
                role = bar.get("bar_role", "UNKNOWN")
                role_dist[role] = role_dist.get(role, 0) + 1
                dia = str(int(bar.get("diameter_mm", 0)))
                qty = int(bar.get("quantity", 0))
                dia_dist[dia] = dia_dist.get(dia, 0) + qty
                if bid and bid not in registry_ids:
                    orphan_groups += 1

        empty_beams = registry_ids - beams_with_bars
        missing_from_eng = registry_ids - eng_ids
        orphan_eng = eng_ids - registry_ids
        duplicate_beams = self._find_duplicates(
            [b.get("beam_id") for b in loader.engineering_beams()]
        )

        r1_with_reinf = {
            bid for bid in r1_ids if loader.r1_beam_has_groups(bid)
        }
        propagated = beams_with_bars & r1_with_reinf

        total_registry = len(registry_ids)
        covered = len(eng_ids & registry_ids)
        coverage_pct = (
            round(100.0 * covered / total_registry, 2) if total_registry else 0.0
        )
        propagation_pct = (
            round(100.0 * len(propagated) / len(r1_with_reinf), 2)
            if r1_with_reinf else 100.0
        )
        bar_coverage_pct = (
            round(100.0 * len(beams_with_bars) / len(r1_with_reinf), 2)
            if r1_with_reinf else 100.0
        )

        avg_bars = (
            round(total_bars / len(beams_with_bars), 2) if beams_with_bars else 0.0
        )
        avg_diameters = (
            round(sum(float(d) for d in dia_dist) / len(dia_dist), 2)
            if dia_dist else 0.0
        )

        return {
            "total_discovered_beams": total_registry,
            "beams_with_reinforcement": len(beams_with_bars),
            "empty_beams": len(empty_beams),
            "empty_beam_ids": sorted(empty_beams),
            "coverage_pct": coverage_pct,
            "propagation_pct": propagation_pct,
            "bar_coverage_pct": bar_coverage_pct,
            "missing_beams": sorted(missing_from_eng),
            "orphan_engineering_beams": sorted(orphan_eng),
            "duplicate_beams": duplicate_beams,
            "orphan_reinforcement_groups": orphan_groups,
            "total_engineering_bars": total_bars,
            "average_bars_per_beam": avg_bars,
            "average_diameter_mm": avg_diameters,
            "role_distribution": role_dist,
            "diameter_distribution": dia_dist,
            "r1_beams_with_reinforcement": len(r1_with_reinf),
            "propagated_beams": len(propagated),
        }

    @staticmethod
    def _find_duplicates(ids: List[str]) -> List[str]:
        seen: Set[str] = set()
        dups: Set[str] = set()
        for i in ids:
            if i in seen:
                dups.add(i)
            seen.add(i)
        return sorted(dups)
