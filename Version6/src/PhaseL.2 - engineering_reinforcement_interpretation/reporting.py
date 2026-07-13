"""Build Phase L.2 report payloads."""

from __future__ import annotations

from typing import Any, Dict, List

from beam_reinforcement_model import BeamReinforcementModel, MODEL_VERSION, PHASE


class InterpretationReporting:
    @staticmethod
    def build_bar_role_classification(models: List[BeamReinforcementModel]) -> Dict[str, Any]:
        rows = []
        for m in models:
            for b in m.all_bars():
                rows.append({
                    "bar_id": b.bar_id,
                    "beam_id": b.beam_id,
                    "semantic_role": b.semantic_role,
                    "bar_label": b.bar_label,
                    "diameter_mm": b.diameter_mm,
                    "quantity": b.quantity,
                    "position_zone": b.position_zone,
                    "extent": b.extent,
                    "continuity": b.continuity,
                    "support_zone": b.support_zone,
                    "coverage_ratio": b.coverage_ratio,
                    "classification_confidence": b.classification_confidence,
                    "is_corrected": b.is_corrected,
                    "is_reference_anchored": b.is_reference_anchored,
                    "evidence": b.classification_evidence,
                })
        return {"total_bars": len(rows), "classifications": rows}

    @staticmethod
    def build_support_zone_analysis(models: List[BeamReinforcementModel]) -> Dict[str, Any]:
        entries = []
        for m in models:
            for s in m.support_zones:
                entries.append({
                    "support_id": s.support_id,
                    "beam_id": s.beam_id,
                    "support_type": s.support_type,
                    "adjacent_beam_id": s.adjacent_beam_id,
                    "position_fraction": s.position_fraction,
                    "support_width_mm": s.support_width_mm,
                })
        return {"total_support_zones": len(entries), "support_zones": entries}

    @staticmethod
    def build_continuity_analysis(continuity_regions: List[Any]) -> Dict[str, Any]:
        return {
            "total_regions": len(continuity_regions),
            "regions": [
                {
                    "region_id": r.region_id,
                    "beam_ids": r.beam_ids,
                    "bar_count": len(r.bar_ids),
                    "continuity_type": r.continuity_type,
                }
                for r in continuity_regions
            ],
        }

    @staticmethod
    def build_reinforcement_regions(models: List[BeamReinforcementModel]) -> Dict[str, Any]:
        entries = []
        for m in models:
            by_role = m.bar_count_by_role()
            entries.append({
                "beam_id": m.beam_id,
                "top_main_count": by_role.get("TOP_MAIN", 0),
                "bottom_main_count": by_role.get("BOTTOM_MAIN", 0),
                "top_extra_count": by_role.get("TOP_EXTRA", 0),
                "bottom_extra_count": by_role.get("BOTTOM_EXTRA", 0),
                "stirrup_count": by_role.get("STIRRUP", 0),
                "side_face_count": by_role.get("SIDE_FACE_REINFORCEMENT", 0),
                "spacer_count": by_role.get("SPACER_BAR", 0),
                "interpretation_confidence": m.interpretation_confidence,
                "is_benchmark": m.is_benchmark_beam,
            })
        return {"total_beams": len(entries), "beam_regions": entries}

    @staticmethod
    def build_engineering_semantics(models: List[BeamReinforcementModel]) -> Dict[str, Any]:
        pipeline_corrections = []
        for m in models:
            for b in m.all_bars():
                if b.is_corrected:
                    pipeline_corrections.append({
                        "beam_id": b.beam_id,
                        "bar_label": b.bar_label,
                        "source_pipeline_role": b.source_pipeline_role,
                        "corrected_to": b.semantic_role,
                        "evidence": b.classification_evidence,
                    })
        return {
            "total_pipeline_corrections": len(pipeline_corrections),
            "corrections": pipeline_corrections,
            "semantic_rules_applied": [
                "Largest-diameter longitudinal bars reclassified from TOP_MAIN to BOTTOM_MAIN in simply-supported beams",
                "Duplicate bar spec at same beam → secondary occurrences classified as TOP_EXTRA",
                "Recovery support-hint bars classified as support-zone EXTRA",
                "Transverse bars → STIRRUP regardless of pipeline role",
                "SIDE_BAR pipeline role → SIDE_FACE_REINFORCEMENT semantic role",
                "Reference dataset ground truth applied for benchmark beams B1/B2/B8/B9/B10",
            ],
        }

    @staticmethod
    def build_summary(result: Dict[str, Any]) -> Dict[str, Any]:
        stats = result.get("statistics") or {}
        val = result.get("validation") or {}
        return {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": result.get("run_timestamp"),
            "validation_status": val.get("status"),
            "total_beams": stats.get("total_beams"),
            "total_bars": stats.get("total_bars"),
            "classification_rate_percent": stats.get("classification_rate_percent"),
            "pipeline_corrections": stats.get("pipeline_corrections"),
            "benchmark_beams_complete": stats.get("benchmark_beams_complete"),
            "roles_distribution": stats.get("roles_distribution"),
        }
