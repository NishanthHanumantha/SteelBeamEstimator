"""
geometry_statistics.py — Compute R.3 geometry statistics.
MODEL_VERSION: 8.0.0

Statistics computed:
  - Beam count (total beams processed)
  - Context count (total GeometryContext objects)
  - Beam axis statistics (length distribution, orientation counts)
  - Support statistics (count, average widths)
  - Projection statistics (confidence distribution, DXF vs fallback)
  - Normalized position histogram (10 bins)
  - Support zone distribution
  - Span zone distribution
  - Extent evidence distribution
  - Geometry confidence distribution
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .geometry_models import BeamAxis, GeometryContext, SupportLocation


_HISTOGRAM_BINS = 10


class GeometryStatistics:

    def compute(
        self,
        contexts_by_beam: Dict[str, List[GeometryContext]],
        axes_by_beam:     Dict[str, BeamAxis],
        supports_by_beam: Dict[str, List[SupportLocation]],
    ) -> Dict[str, Any]:

        all_ctxs = [c for cl in contexts_by_beam.values() for c in cl]
        beam_ids = list(axes_by_beam.keys())

        stats: Dict[str, Any] = {}

        # ── Counts ────────────────────────────────────────────────────────────
        stats["beam_count"]    = len(beam_ids)
        stats["context_count"] = len(all_ctxs)

        # ── Beam axis statistics ──────────────────────────────────────────────
        lengths = [ax.beam_length_mm for ax in axes_by_beam.values()]
        orientations = Counter(ax.orientation for ax in axes_by_beam.values())
        sources      = Counter(ax.geometry_source for ax in axes_by_beam.values())
        stats["beam_axis"] = {
            "count":             len(lengths),
            "min_length_mm":     round(min(lengths), 1) if lengths else 0,
            "max_length_mm":     round(max(lengths), 1) if lengths else 0,
            "mean_length_mm":    round(sum(lengths) / len(lengths), 1) if lengths else 0,
            "orientations":      dict(orientations),
            "geometry_sources":  dict(sources),
        }

        # ── Support statistics ────────────────────────────────────────────────
        all_sups  = [s for sl in supports_by_beam.values() for s in sl]
        sup_types = Counter(s.support_type for s in all_sups)
        avg_width = (sum(s.support_width_mm for s in all_sups) / len(all_sups)) if all_sups else 0
        stats["support"] = {
            "total_supports":  len(all_sups),
            "type_distribution": dict(sup_types),
            "avg_support_width_mm": round(avg_width, 1),
            "beams_with_supports": len(supports_by_beam),
        }

        # ── Projection statistics ─────────────────────────────────────────────
        proj_conf    = Counter(c.projection_confidence for c in all_ctxs)
        pos_sources  = Counter(c.position_source for c in all_ctxs)
        proj_dists   = [c.projection_distance_mm for c in all_ctxs]
        stats["projection"] = {
            "confidence_distribution": dict(proj_conf),
            "position_source_distribution": dict(pos_sources),
            "min_projection_mm": round(min(proj_dists), 1) if proj_dists else 0,
            "max_projection_mm": round(max(proj_dists), 1) if proj_dists else 0,
            "mean_projection_mm": round(sum(proj_dists) / len(proj_dists), 1) if proj_dists else 0,
        }

        # ── Normalized position histogram ─────────────────────────────────────
        bin_size = 1.0 / _HISTOGRAM_BINS
        hist     = {f"{i * bin_size:.1f}-{(i+1) * bin_size:.1f}": 0 for i in range(_HISTOGRAM_BINS)}
        for c in all_ctxs:
            idx = min(int(c.normalized_position / bin_size), _HISTOGRAM_BINS - 1)
            key = f"{idx * bin_size:.1f}-{(idx + 1) * bin_size:.1f}"
            hist[key] = hist.get(key, 0) + 1
        stats["normalized_position_histogram"] = hist

        # ── Support zone distribution ─────────────────────────────────────────
        sup_zone_dist = Counter(c.support_zone for c in all_ctxs)
        stats["support_zone_distribution"] = dict(sup_zone_dist)

        # ── Span zone distribution ────────────────────────────────────────────
        span_zone_dist = Counter(c.span_zone for c in all_ctxs)
        stats["span_zone_distribution"] = dict(span_zone_dist)

        # ── Extent evidence distribution ──────────────────────────────────────
        extent_dist = Counter(c.candidate_extent for c in all_ctxs)
        stats["extent_distribution"] = dict(extent_dist)

        # ── Geometry confidence distribution ──────────────────────────────────
        geo_conf_dist = Counter(c.geometry_confidence for c in all_ctxs)
        stats["geometry_confidence_distribution"] = dict(geo_conf_dist)

        # ── Intent check (always UNKNOWN — confirmed by R.9) ─────────────────
        stats["intent_check"] = {
            "all_intent_unknown": True,
            "note": "Intent remains UNKNOWN — R.3 produces geometry evidence only",
        }

        return stats
