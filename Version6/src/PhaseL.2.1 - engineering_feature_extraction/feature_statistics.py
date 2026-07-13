"""Compute statistics over the EngineeringFeatureModel collection."""

from __future__ import annotations

from typing import Any, Dict, List

from engineering_feature_model import (
    EngineeringFeatureModel,
    ZONE_TOP, ZONE_BOTTOM, ZONE_SIDE, ZONE_TRANSVERSE, ZONE_MIDDLE, ZONE_UNKNOWN,
    ORI_LONGITUDINAL, ORI_TRANSVERSE,
    EXT_FULL, EXT_LEFT_ONLY, EXT_RIGHT_ONLY, EXT_PARTIAL,
)


class FeatureStatistics:
    def build(self, features: List[EngineeringFeatureModel]) -> Dict[str, Any]:
        total = len(features)
        if not total:
            return {"total_features": 0}

        # Zone distribution
        zone_dist: Dict[str, int] = {}
        for f in features:
            z = f.position.position_zone
            zone_dist[z] = zone_dist.get(z, 0) + 1

        # Orientation distribution
        ori_dist: Dict[str, int] = {}
        for f in features:
            o = f.orientation.orientation
            ori_dist[o] = ori_dist.get(o, 0) + 1

        # Extent distribution
        ext_dist: Dict[str, int] = {}
        for f in features:
            e = f.extent.extent_type
            ext_dist[e] = ext_dist.get(e, 0) + 1

        # Continuity distribution
        cont_dist: Dict[str, int] = {}
        for f in features:
            c = f.continuity.continuity_type
            cont_dist[c] = cont_dist.get(c, 0) + 1

        # Coverage ratio stats
        cov_values = [f.extent.coverage_ratio for f in features if f.extent.coverage_ratio is not None]
        cov_mean = round(sum(cov_values) / len(cov_values), 3) if cov_values else None
        cov_min = round(min(cov_values), 3) if cov_values else None
        cov_max = round(max(cov_values), 3) if cov_values else None

        # Completeness
        complete_count = sum(1 for f in features if f.feature_completeness_score >= 0.8)

        # Multi-span
        multi_span = sum(1 for f in features if f.continuity.is_multi_span)

        # Beams covered
        beam_ids = sorted(set(f.beam_id for f in features))

        return {
            "total_features": total,
            "total_beams": len(beam_ids),
            "beam_ids": beam_ids,
            "completeness_high": complete_count,
            "completeness_rate_percent": round(100 * complete_count / total, 2),
            "multi_span_bars": multi_span,
            "zone_distribution": zone_dist,
            "orientation_distribution": ori_dist,
            "extent_distribution": ext_dist,
            "continuity_distribution": cont_dist,
            "coverage_ratio": {
                "mean": cov_mean,
                "min": cov_min,
                "max": cov_max,
                "count": len(cov_values),
            },
        }
