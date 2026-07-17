"""Beam consistency checks against registry."""
from __future__ import annotations
from typing import Any, Dict, List, Set

from .pipeline_data_loader import PipelineDataLoader
from .validation_models import RuleResult


class BeamConsistencyChecker:

    def check(
        self, loader: PipelineDataLoader, coverage: Dict[str, Any]
    ) -> Dict[str, RuleResult]:
        registry_ids = loader.registry_beam_ids()
        eng_ids = loader.engineering_beam_ids()
        eng_beams = loader.engineering_beams()

        orphan_eng = eng_ids - registry_ids
        missing_eng = registry_ids - eng_ids
        dups = coverage.get("duplicate_beams", [])

        rule2_pass = len(orphan_eng) == 0
        rule3_pass = coverage.get("orphan_reinforcement_groups", 0) == 0
        rule4_pass = len(dups) == 0

        invalid_refs = []
        for beam in eng_beams:
            geom = beam.get("geometry", {})
            if geom.get("beam_id") and geom["beam_id"] != beam.get("beam_id"):
                invalid_refs.append(beam.get("beam_id"))

        return {
            "RULE_2": RuleResult(
                "RULE_2",
                "PASS" if rule2_pass else "ERROR",
                f"orphan_engineering_beams={len(orphan_eng)}",
                rule2_pass,
            ),
            "RULE_3": RuleResult(
                "RULE_3",
                "PASS" if rule3_pass else "ERROR",
                f"orphan_groups={coverage.get('orphan_reinforcement_groups', 0)}",
                rule3_pass,
            ),
            "RULE_4": RuleResult(
                "RULE_4",
                "PASS" if rule4_pass else "ERROR",
                f"duplicate_beams={len(dups)}",
                rule4_pass,
            ),
            "_invalid_refs": RuleResult(
                "INVALID_REFS",
                "PASS" if not invalid_refs else "WARNING",
                f"invalid_geometry_refs={len(invalid_refs)}",
                not invalid_refs,
            ),
            "_missing_eng": missing_eng,
            "_orphan_eng": orphan_eng,
        }

    def build_beam_status(
        self, loader: PipelineDataLoader, classifications: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        registry_ids = sorted(loader.registry_beam_ids())
        eng_map = {b["beam_id"]: b for b in loader.engineering_beams()}
        matrix = []
        for bid in registry_ids:
            beam = eng_map.get(bid, {})
            bars = beam.get("bars", [])
            cls = classifications.get(bid, {})
            matrix.append({
                "beam_id": bid,
                "in_registry": True,
                "in_engineering_model": bid in eng_map,
                "bar_count": len(bars),
                "has_reinforcement": len(bars) > 0,
                "classification": cls.get("category", "UNKNOWN"),
                "classification_reason": cls.get("reason", ""),
                "status": cls.get("status", "UNKNOWN"),
            })
        return matrix
