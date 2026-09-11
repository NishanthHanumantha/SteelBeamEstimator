"""
geometry_export.py — Export all 12 R.3 artefacts.
MODEL_VERSION: 8.0.0

Exports:
  GeometryContexts.json
  BeamAxis.json
  SupportLocations.json
  ProjectionData.json
  NormalizedPositions.json
  SupportZones.json
  SpanZones.json
  ExtentEvidence.json
  GeometryStatistics.json
  GeometryValidation.json
  GeometryReport.json
  GeometryReport.md
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List

from .geometry_models import BeamAxis, GeometryContext, SupportLocation


class GeometryExport:

    def export_all(
        self,
        out_dir:          pathlib.Path,
        contexts_by_beam: Dict[str, List[GeometryContext]],
        axes_by_beam:     Dict[str, BeamAxis],
        supports_by_beam: Dict[str, List[SupportLocation]],
        stats:            Dict[str, Any],
        validation:       Dict[str, Any],
        md_report:        str,
        phase_meta:       Dict[str, Any],
    ) -> Dict[str, pathlib.Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        all_ctxs = [c for cl in contexts_by_beam.values() for c in cl]

        paths: Dict[str, pathlib.Path] = {}

        # 1. GeometryContexts.json
        paths["GeometryContexts"] = self._write(
            out_dir / "GeometryContexts.json",
            {
                **phase_meta, "generated_at": ts,
                "total_contexts": len(all_ctxs),
                "contexts_by_beam": {
                    bid: [self._ctx_dict(c) for c in cl]
                    for bid, cl in contexts_by_beam.items()
                },
            },
        )

        # 2. BeamAxis.json
        paths["BeamAxis"] = self._write(
            out_dir / "BeamAxis.json",
            {
                **phase_meta, "generated_at": ts,
                "beam_count": len(axes_by_beam),
                "axes": {
                    bid: self._axis_dict(ax)
                    for bid, ax in axes_by_beam.items()
                },
            },
        )

        # 3. SupportLocations.json
        paths["SupportLocations"] = self._write(
            out_dir / "SupportLocations.json",
            {
                **phase_meta, "generated_at": ts,
                "beam_count": len(supports_by_beam),
                "supports": {
                    bid: [self._sup_dict(s) for s in sl]
                    for bid, sl in supports_by_beam.items()
                },
            },
        )

        # 4. ProjectionData.json
        paths["ProjectionData"] = self._write(
            out_dir / "ProjectionData.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(all_ctxs),
                "projections": [
                    {
                        "annotation_id":          c.annotation_id,
                        "beam_id":                c.beam_id,
                        "projection_point_x":     c.projection_point_x,
                        "projection_distance_mm": c.projection_distance_mm,
                        "perpendicular_offset":   c.perpendicular_offset,
                        "projection_confidence":  c.projection_confidence,
                        "position_source":        c.position_source,
                    }
                    for c in all_ctxs
                ],
            },
        )

        # 5. NormalizedPositions.json
        paths["NormalizedPositions"] = self._write(
            out_dir / "NormalizedPositions.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(all_ctxs),
                "positions": [
                    {
                        "annotation_id":      c.annotation_id,
                        "beam_id":            c.beam_id,
                        "normalized_position": c.normalized_position,
                        "beam_length_mm":     c.beam_length_mm,
                    }
                    for c in all_ctxs
                ],
            },
        )

        # 6. SupportZones.json
        paths["SupportZones"] = self._write(
            out_dir / "SupportZones.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(all_ctxs),
                "support_zones": [
                    {
                        "annotation_id":      c.annotation_id,
                        "beam_id":            c.beam_id,
                        "inside_left_support":  c.inside_left_support,
                        "inside_right_support": c.inside_right_support,
                        "inside_support_zone":  c.inside_support_zone,
                        "support_zone":          c.support_zone,
                        "nearest_support":       c.nearest_support,
                        "distance_left_mm":      c.distance_left_mm,
                        "distance_right_mm":     c.distance_right_mm,
                    }
                    for c in all_ctxs
                ],
            },
        )

        # 7. SpanZones.json
        paths["SpanZones"] = self._write(
            out_dir / "SpanZones.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(all_ctxs),
                "span_zones": [
                    {
                        "annotation_id":     c.annotation_id,
                        "beam_id":           c.beam_id,
                        "span_zone":         c.span_zone,
                        "normalized_position": c.normalized_position,
                    }
                    for c in all_ctxs
                ],
            },
        )

        # 8. ExtentEvidence.json
        paths["ExtentEvidence"] = self._write(
            out_dir / "ExtentEvidence.json",
            {
                **phase_meta, "generated_at": ts,
                "total": len(all_ctxs),
                "extent_evidence": [
                    {
                        "annotation_id":    c.annotation_id,
                        "beam_id":          c.beam_id,
                        "candidate_extent": c.candidate_extent,
                        "extent_confidence": c.extent_confidence,
                        "extent_reason":    c.extent_reason,
                    }
                    for c in all_ctxs
                ],
            },
        )

        # 9. GeometryStatistics.json
        paths["GeometryStatistics"] = self._write(
            out_dir / "GeometryStatistics.json",
            {**phase_meta, "generated_at": ts, **stats},
        )

        # 10. GeometryValidation.json
        paths["GeometryValidation"] = self._write(
            out_dir / "GeometryValidation.json",
            {**phase_meta, "generated_at": ts, **validation},
        )

        # 11. GeometryReport.json
        paths["GeometryReport"] = self._write(
            out_dir / "GeometryReport.json",
            {
                **phase_meta, "generated_at": ts,
                "statistics":    stats,
                "validation":    validation,
                "artefacts":     [str(p) for p in paths.values()],
            },
        )

        # 12. GeometryReport.md
        md_path = out_dir / "GeometryReport.md"
        md_path.write_text(md_report, encoding="utf-8")
        paths["GeometryReport_md"] = md_path

        return paths

    # ── Serialisation helpers ─────────────────────────────────────────────────

    def _ctx_dict(self, c: GeometryContext) -> Dict[str, Any]:
        return {
            "beam_id":                c.beam_id,
            "annotation_id":          c.annotation_id,
            "projection_point_x":     c.projection_point_x,
            "projection_distance_mm": c.projection_distance_mm,
            "perpendicular_offset":   c.perpendicular_offset,
            "projection_confidence":  c.projection_confidence,
            "normalized_position":    c.normalized_position,
            "beam_length_mm":         c.beam_length_mm,
            "nearest_support":        c.nearest_support,
            "distance_left_mm":       c.distance_left_mm,
            "distance_right_mm":      c.distance_right_mm,
            "inside_left_support":    c.inside_left_support,
            "inside_right_support":   c.inside_right_support,
            "inside_support_zone":    c.inside_support_zone,
            "support_zone":           c.support_zone,
            "span_zone":              c.span_zone,
            "candidate_extent":       c.candidate_extent,
            "extent_confidence":      c.extent_confidence,
            "extent_reason":          c.extent_reason,
            "geometry_confidence":    c.geometry_confidence,
            "geometry_required":      c.geometry_required,
            "geometry_notes":         c.geometry_notes,
            "geometry_source":        c.geometry_source,
            "position_source":        c.position_source,
        }

    def _axis_dict(self, ax: BeamAxis) -> Dict[str, Any]:
        return {
            "beam_id":          ax.beam_id,
            "start_x":          ax.start_x,
            "start_y":          ax.start_y,
            "end_x":            ax.end_x,
            "end_y":            ax.end_y,
            "beam_length_mm":   ax.beam_length_mm,
            "dxf_centroid_x":   ax.dxf_centroid_x,
            "dxf_centroid_y":   ax.dxf_centroid_y,
            "dxf_start_x":      ax.dxf_start_x,
            "dxf_end_x":        ax.dxf_end_x,
            "orientation":      ax.orientation,
            "geometry_source":  ax.geometry_source,
            "axis_confidence":  ax.axis_confidence,
        }

    def _sup_dict(self, s: SupportLocation) -> Dict[str, Any]:
        return {
            "support_id":          s.support_id,
            "beam_id":             s.beam_id,
            "support_type":        s.support_type,
            "position_fraction":   s.position_fraction,
            "position_mm":         s.position_mm,
            "support_width_mm":    s.support_width_mm,
            "zone_start_fraction": s.zone_start_fraction,
            "zone_end_fraction":   s.zone_end_fraction,
            "confidence":          s.confidence,
        }

    def _write(self, path: pathlib.Path, data: Any) -> pathlib.Path:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path
