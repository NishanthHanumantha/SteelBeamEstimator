"""
relationship_export.py — Export all 12 R.3.1 artefacts.
MODEL_VERSION: 8.1.0

Exports:
  EngineeringDrawingRelationships.json
  LeaderInventory.json
  ArrowInventory.json
  PhysicalBars.json
  RelationshipGraph.json
  RelationshipStatistics.json
  ConventionEvidence.json
  SupportCrossings.json
  ExtentEvidence.json
  RelationshipValidation.json
  EngineeringRelationshipReport.json
  EngineeringRelationshipReport.md
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from .relationship_models import (
    EngineeringDrawingRelationship, LeaderObject, ArrowObject,
    PhysicalBar, SupportCrossing,
)


class RelationshipExport:

    def export_all(
        self,
        out_dir:        pathlib.Path,
        relationships:  List[EngineeringDrawingRelationship],
        leaders:        List[LeaderObject],
        arrows:         List[ArrowObject],
        bars:           List[PhysicalBar],
        crossings:      List[SupportCrossing],
        extents_by_bar: Dict[str, Any],
        stats:          Dict[str, Any],
        validation:     Dict[str, Any],
        md_report:      str,
        phase_meta:     Dict[str, Any],
    ) -> Dict[str, pathlib.Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        ts    = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        paths: Dict[str, pathlib.Path] = {}

        # 1. EngineeringDrawingRelationships.json
        paths["EngineeringDrawingRelationships"] = self._w(
            out_dir / "EngineeringDrawingRelationships.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(relationships),
                "relationships": [self._rel_dict(r) for r in relationships],
            },
        )

        # 2. LeaderInventory.json
        paths["LeaderInventory"] = self._w(
            out_dir / "LeaderInventory.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(leaders),
                "leaders": [self._ldr_dict(l) for l in leaders],
            },
        )

        # 3. ArrowInventory.json
        paths["ArrowInventory"] = self._w(
            out_dir / "ArrowInventory.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(arrows),
                "arrows": [self._arr_dict(a) for a in arrows],
            },
        )

        # 4. PhysicalBars.json
        paths["PhysicalBars"] = self._w(
            out_dir / "PhysicalBars.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(bars),
                "bars": [self._bar_dict(b) for b in bars],
            },
        )

        # 5. RelationshipGraph.json
        paths["RelationshipGraph"] = self._w(
            out_dir / "RelationshipGraph.json",
            {
                **phase_meta, "generated_at": ts,
                "nodes": {
                    "annotations": len(relationships),
                    "leaders":     len(leaders),
                    "arrows":      len(arrows),
                    "bars":        len(bars),
                },
                "edges": [
                    {
                        "annotation_id": r.annotation_id,
                        "leader_id":     r.leader_id,
                        "arrow_id":      r.arrow_id,
                        "bar_id":        r.physical_bar_id,
                        "extent_label":  r.extent_label,
                        "confidence":    r.relationship_confidence,
                    }
                    for r in relationships
                ],
            },
        )

        # 6. RelationshipStatistics.json
        paths["RelationshipStatistics"] = self._w(
            out_dir / "RelationshipStatistics.json",
            {**phase_meta, "generated_at": ts, **stats},
        )

        # 7. ConventionEvidence.json
        all_conv = []
        for r in relationships:
            for cv in r.convention_evidence:
                all_conv.append({
                    "annotation_id": r.annotation_id,
                    "beam_id":       r.beam_id,
                    "convention":    cv,
                })
        paths["ConventionEvidence"] = self._w(
            out_dir / "ConventionEvidence.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(all_conv),
                "conventions": all_conv,
            },
        )

        # 8. SupportCrossings.json
        paths["SupportCrossings"] = self._w(
            out_dir / "SupportCrossings.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(crossings),
                "crossings": [self._cross_dict(c) for c in crossings],
            },
        )

        # 9. ExtentEvidence.json
        paths["ExtentEvidence"] = self._w(
            out_dir / "ExtentEvidence.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(relationships),
                "extents": [
                    {
                        "annotation_id":     r.annotation_id,
                        "beam_id":           r.beam_id,
                        "extent_label":      r.extent_label,
                        "extent_confidence": r.extent_confidence,
                        "extent_reason":     r.extent_reason,
                        "bar_normalized_start": r.bar_normalized_start,
                        "bar_normalized_end":   r.bar_normalized_end,
                    }
                    for r in relationships
                ],
            },
        )

        # 10. RelationshipValidation.json
        paths["RelationshipValidation"] = self._w(
            out_dir / "RelationshipValidation.json",
            {**phase_meta, "generated_at": ts, **validation},
        )

        # 11. EngineeringRelationshipReport.json
        paths["EngineeringRelationshipReport"] = self._w(
            out_dir / "EngineeringRelationshipReport.json",
            {
                **phase_meta, "generated_at": ts,
                "statistics": stats,
                "validation": validation,
                "artefacts":  [str(p) for p in paths.values()],
            },
        )

        # 12. EngineeringRelationshipReport.md
        md_path = out_dir / "EngineeringRelationshipReport.md"
        md_path.write_text(md_report, encoding="utf-8")
        paths["EngineeringRelationshipReport_md"] = md_path

        return paths

    # ── Serialisation helpers ─────────────────────────────────────────────────

    def _rel_dict(self, r: EngineeringDrawingRelationship) -> Dict:
        return {
            "relationship_id":        r.relationship_id,
            "beam_id":                r.beam_id,
            "annotation_id":          r.annotation_id,
            "leader_id":              r.leader_id,
            "arrow_id":               r.arrow_id,
            "physical_bar_id":        r.physical_bar_id,
            "projection_id":          r.projection_id,
            "geometry_context_id":    r.geometry_context_id,
            "support_ids":            r.support_ids,
            "extent_label":           r.extent_label,
            "extent_confidence":      r.extent_confidence,
            "extent_reason":          r.extent_reason,
            "support_crossings":      r.support_crossings,
            "left_support_crossed":   r.left_support_crossed,
            "right_support_crossed":  r.right_support_crossed,
            "leader_length":          r.leader_length,
            "bar_length":             r.bar_length,
            "bar_normalized_start":   r.bar_normalized_start,
            "bar_normalized_end":     r.bar_normalized_end,
            "bar_vertical_placement": r.bar_vertical_placement,
            "relationship_confidence":r.relationship_confidence,
            "relationship_reason":    r.relationship_reason,
            "convention_evidence":    r.convention_evidence,
            "geometry_notes":         r.geometry_notes,
        }

    def _ldr_dict(self, l: LeaderObject) -> Dict:
        return {
            "leader_id":     l.leader_id,
            "beam_id":       l.beam_id,
            "tip_x":         l.tip_x,
            "tip_y":         l.tip_y,
            "tail_x":        l.tail_x,
            "tail_y":        l.tail_y,
            "vertex_count":  l.vertex_count,
            "layer":         l.layer,
            "has_arrowhead": l.has_arrowhead,
            "leader_length": l.leader_length,
            "tip_direction": l.tip_direction,
        }

    def _arr_dict(self, a: ArrowObject) -> Dict:
        return {
            "arrow_id":        a.arrow_id,
            "leader_id":       a.leader_id,
            "beam_id":         a.beam_id,
            "tip_x":           a.tip_x,
            "tip_y":           a.tip_y,
            "direction":       a.direction,
            "annotation_side": a.annotation_side,
            "confidence":      a.confidence,
        }

    def _bar_dict(self, b: PhysicalBar) -> Dict:
        return {
            "bar_id":             b.bar_id,
            "beam_id":            b.beam_id,
            "entity_type":        b.entity_type,
            "layer":              b.layer,
            "start_x":            b.start_x,
            "end_x":              b.end_x,
            "y_position":         b.y_position,
            "bar_length_mm":      b.bar_length_mm,
            "vertical_placement": b.vertical_placement,
            "normalized_start":   b.normalized_start,
            "normalized_end":     b.normalized_end,
            "bar_confidence":     b.bar_confidence,
        }

    def _cross_dict(self, c: SupportCrossing) -> Dict:
        return {
            "crossing_id":          c.crossing_id,
            "bar_id":               c.bar_id,
            "beam_id":              c.beam_id,
            "support_id":           c.support_id,
            "support_type":         c.support_type,
            "crosses":              c.crosses,
            "normalized_depth":     c.normalized_depth,
            "crossing_confidence":  c.crossing_confidence,
        }

    def _w(self, path: pathlib.Path, data: Any) -> pathlib.Path:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path
