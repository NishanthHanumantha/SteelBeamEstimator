"""
reinforcement_export.py — Export 8 R.1 JSON artefacts.
"""

from __future__ import annotations

import json
import logging
import pathlib
from dataclasses import asdict
from typing import Dict, List, Optional

from .adaptive_association_engine import AdaptiveAssociationEngine
from .reinforcement_models import (
    BeamDetail,
    ReinforcementAnnotation,
    ReinforcementGroup,
    R1BeamReinforcementModel,
)
from .reinforcement_validator import ValidationReport

log = logging.getLogger(__name__)


def _json(obj: object) -> str:
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


class ReinforcementExport:
    """Writes all R.1 output artefacts to disk."""

    def __init__(self, config: dict, project_root: pathlib.Path):
        out_rel       = config.get("export", {}).get(
            "output_dir", "data/output/PhaseR.1_generalized_reinforcement_discovery"
        )
        self._out_dir = project_root / out_rel
        self._project_root = project_root
        self._out_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    def export_all(
        self,
        details:       List[BeamDetail],
        annotations:   Dict[str, List[ReinforcementAnnotation]],
        groups:        Dict[str, Dict[str, ReinforcementGroup]],
        models:        Dict[str, R1BeamReinforcementModel],
        relationships: Dict[str, List[dict]],
        statistics:    dict,
        validation:    ValidationReport,
        report:        dict,
        association_engine: Optional[AdaptiveAssociationEngine] = None,
    ) -> Dict[str, str]:
        """Write all 8 artefacts.  Returns {filename: path_str}."""
        written: Dict[str, str] = {}

        written["beam_details.json"] = self._write(
            "beam_details.json",
            {
                "total": len(details),
                "beam_details": [
                    {
                        "beam_id":       d.beam_id,
                        "beam_mark":     d.beam_mark,
                        "centroid_x":    d.centroid_x,
                        "centroid_y":    d.centroid_y,
                        "section":       d.section,
                        "detail_radius": d.detail_radius,
                        "entity_count":  d.entity_count,
                    }
                    for d in details
                ],
            },
        )

        written["reinforcement_annotations.json"] = self._write(
            "reinforcement_annotations.json",
            {
                "total_beams":  len(annotations),
                "total_annotations": sum(len(v) for v in annotations.values()),
                "by_beam": {
                    beam_id: [
                        {
                            "annotation_id":    a.annotation_id,
                            "clean_text":       a.clean_text,
                            "x":                a.x,
                            "y":                a.y,
                            "dy_from_centroid": a.dy_from_centroid,
                            "role":             a.role,
                            "position_zone":    a.position_zone,
                            "quantity":         a.quantity,
                            "diameter_mm":      a.diameter_mm,
                            "steel_grade":      a.steel_grade,
                            "spacing_mm":       a.spacing_mm,
                            "bar_label":        a.bar_label,
                            "confidence":       a.confidence,
                            "is_reinforcement": a.is_reinforcement,
                            "association_score": a.association_score,
                            "association_method": a.association_method,
                            "association_confidence": a.association_confidence,
                            "association_evidence": a.association_evidence,
                        }
                        for a in anns
                    ]
                    for beam_id, anns in annotations.items()
                },
            },
        )

        written["reinforcement_groups.json"] = self._write(
            "reinforcement_groups.json",
            {
                "total_beams":  len(groups),
                "total_groups": sum(len(g) for g in groups.values()),
                "by_beam": {
                    beam_id: {
                        role: {
                            "group_id":       grp.group_id,
                            "role":           grp.role,
                            "total_quantity": grp.total_quantity,
                            "diameters_mm":   grp.diameters_mm,
                            "labels":         grp.labels,
                            "bar_count":      len(grp.bars),
                        }
                        for role, grp in grp_dict.items()
                    }
                    for beam_id, grp_dict in groups.items()
                },
            },
        )

        written["beam_reinforcement_models.json"] = self._write(
            "beam_reinforcement_models.json",
            {
                "model_version":  "8.2.0",
                "phase":          "R.1",
                "total_models":   len(models),
                "models": {
                    beam_id: m.to_dict()
                    for beam_id, m in models.items()
                },
            },
        )

        written["engineering_relationships.json"] = self._write(
            "engineering_relationships.json",
            {
                "total_beams":         len(relationships),
                "total_relationships": sum(len(v) for v in relationships.values()),
                "by_beam":             relationships,
            },
        )

        written["reinforcement_statistics.json"] = self._write(
            "reinforcement_statistics.json", statistics
        )

        written["reinforcement_validation_report.json"] = self._write(
            "reinforcement_validation_report.json", validation.to_dict()
        )

        written["generalized_reinforcement_report.json"] = self._write(
            "generalized_reinforcement_report.json", report
        )

        if association_engine is not None:
            r11a_dir = self._project_root / "data/output/PhaseR1_1A_annotation_coverage"
            r11a_dir.mkdir(parents=True, exist_ok=True)
            self._export_r11a_artefacts(r11a_dir, association_engine, details, annotations)

        log.info("ReinforcementExport: %d artefacts written to %s", len(written), self._out_dir)
        return written

    def _export_r11a_artefacts(
        self,
        out_dir: pathlib.Path,
        engine: AdaptiveAssociationEngine,
        details: List[BeamDetail],
        annotations: Dict[str, List[ReinforcementAnnotation]],
    ) -> None:
        beam_ids = {d.beam_id for d in details}
        beams_with_reinf = sum(
            1 for bid, anns in annotations.items()
            if any(a.is_reinforcement for a in anns)
        )
        total_anns = sum(len(v) for v in annotations.values())
        recovered = sum(1 for o in engine.orphan_recoveries if o.get("beam_id"))
        leader_assoc = sum(
            1 for s in engine.association_scores
            if s.get("association_method") == "leader"
        )
        cluster_assoc = sum(
            1 for s in engine.association_scores
            if s.get("association_method") in ("cluster", "hybrid")
        )
        confidences = [
            s.get("association_confidence", 0.0)
            for s in engine.association_scores
        ]
        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        payloads = {
            "beam_detail_clusters.json": {
                "total_clusters": len(engine.clusters),
                "clusters": [
                    {
                        "cluster_id": c.cluster_id,
                        "beam_id": c.beam_id,
                        "center_x": c.center_x,
                        "center_y": c.center_y,
                        "member_count": c.member_count,
                        "has_beam_mark": c.has_beam_mark,
                        "leader_count": c.leader_count,
                    }
                    for c in engine.clusters
                ],
            },
            "adaptive_search_regions.json": {
                "total_regions": len(engine.search_regions),
                "regions": [
                    {
                        "beam_id": r.beam_id,
                        "center_x": r.center_x,
                        "center_y": r.center_y,
                        "radius": r.radius,
                        "span_mm": r.span_mm,
                        "depth_mm": r.depth_mm,
                        "width_mm": r.width_mm,
                        "anchor_sources": r.anchor_sources,
                    }
                    for r in engine.search_regions
                ],
            },
            "annotation_association_scores.json": {
                "total_scores": len(engine.association_scores),
                "scores": engine.association_scores,
            },
            "orphan_annotation_recovery.json": {
                "total_orphans": len(engine.orphan_recoveries),
                "recovered": recovered,
                "unrecovered": len(engine.orphan_recoveries) - recovered,
                "records": engine.orphan_recoveries,
            },
            "beam_annotation_coverage.json": {
                "total_beams": len(details),
                "beams_with_reinforcement": beams_with_reinf,
                "beams_without_reinforcement": len(details) - beams_with_reinf,
                "total_annotations": total_anns,
                "by_beam": {
                    d.beam_id: {
                        "annotation_count": len(annotations.get(d.beam_id, [])),
                        "rebar_count": sum(
                            1 for a in annotations.get(d.beam_id, [])
                            if a.is_reinforcement
                        ),
                        "detail_radius": d.detail_radius,
                    }
                    for d in details
                },
            },
            "engineering_confidence_summary.json": {
                "average_confidence": avg_conf,
                "leader_associations": leader_assoc,
                "cluster_associations": cluster_assoc,
                "score_count": len(engine.association_scores),
            },
        }
        for name, data in payloads.items():
            (out_dir / name).write_text(_json(data), encoding="utf-8")

    # ──────────────────────────────────────────────────────────────────────────
    def _write(self, filename: str, data: object) -> str:
        path = self._out_dir / filename
        path.write_text(_json(data), encoding="utf-8")
        log.debug("Wrote %s", path)
        return str(path)
