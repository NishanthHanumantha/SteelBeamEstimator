"""
relationship_statistics.py — Compute R.3.1 statistics.
MODEL_VERSION: 8.1.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .relationship_models import (
    EngineeringDrawingRelationship, LeaderObject, ArrowObject, PhysicalBar, SupportCrossing,
)


class RelationshipStatistics:

    def compute(
        self,
        relationships: List[EngineeringDrawingRelationship],
        leaders:       List[LeaderObject],
        arrows:        List[ArrowObject],
        bars:          List[PhysicalBar],
        crossings:     List[SupportCrossing],
    ) -> Dict[str, Any]:

        stats: Dict[str, Any] = {}

        # ── Counts ────────────────────────────────────────────────────────────
        stats["total_annotations"]  = len(relationships)
        stats["total_leaders"]      = len(leaders)
        stats["total_arrows"]       = len(arrows)
        stats["total_physical_bars"]= len(bars)
        stats["total_crossings"]    = len(crossings)

        # ── Leader statistics ─────────────────────────────────────────────────
        ldr_by_beam = Counter(l.beam_id for l in leaders)
        ldr_dirs    = Counter(l.tip_direction for l in leaders)
        ldr_lengths = [l.leader_length for l in leaders]
        stats["leader_statistics"] = {
            "by_beam_sample":    dict(list(ldr_by_beam.most_common(5))),
            "direction_distribution": dict(ldr_dirs),
            "min_length_mm":     round(min(ldr_lengths), 1) if ldr_lengths else 0,
            "max_length_mm":     round(max(ldr_lengths), 1) if ldr_lengths else 0,
            "mean_length_mm":    round(sum(ldr_lengths) / len(ldr_lengths), 1) if ldr_lengths else 0,
        }

        # ── Arrow statistics ──────────────────────────────────────────────────
        arrow_dirs = Counter(a.direction for a in arrows)
        stats["arrow_statistics"] = {
            "total":                 len(arrows),
            "direction_distribution":dict(arrow_dirs),
        }

        # ── Physical bar statistics ───────────────────────────────────────────
        bar_types      = Counter(b.entity_type for b in bars)
        bar_placements = Counter(b.vertical_placement for b in bars)
        bar_lengths    = [b.bar_length_mm for b in bars]
        stats["physical_bar_statistics"] = {
            "by_entity_type":     dict(bar_types),
            "placement_distribution": dict(bar_placements),
            "min_length_mm":      round(min(bar_lengths), 1) if bar_lengths else 0,
            "max_length_mm":      round(max(bar_lengths), 1) if bar_lengths else 0,
            "mean_length_mm":     round(sum(bar_lengths) / len(bar_lengths), 1) if bar_lengths else 0,
        }

        # ── Relationship confidence distribution ──────────────────────────────
        rel_conf = Counter(r.relationship_confidence for r in relationships)
        stats["relationship_confidence_distribution"] = dict(rel_conf)

        # ── Extent distribution ───────────────────────────────────────────────
        ext_dist = Counter(r.extent_label for r in relationships)
        stats["extent_distribution"] = dict(ext_dist)

        # ── Support crossing distribution ─────────────────────────────────────
        cross_counts = Counter(r.support_crossings for r in relationships)
        stats["support_crossing_distribution"] = {
            str(k): v for k, v in cross_counts.items()
        }
        left_x  = sum(1 for r in relationships if r.left_support_crossed)
        right_x = sum(1 for r in relationships if r.right_support_crossed)
        both_x  = sum(1 for r in relationships if r.left_support_crossed and r.right_support_crossed)
        stats["support_crossing_summary"] = {
            "left_support_reached":  left_x,
            "right_support_reached": right_x,
            "both_supports_reached": both_x,
        }

        # ── Bar vertical placement distribution ───────────────────────────────
        bar_pl = Counter(r.bar_vertical_placement for r in relationships)
        stats["bar_placement_distribution"] = dict(bar_pl)

        # ── Convention statistics ─────────────────────────────────────────────
        total_conv = sum(len(r.convention_evidence) for r in relationships)
        stats["convention_statistics"] = {
            "total_conventions_observed": total_conv,
            "annotations_with_arrow_evidence": sum(
                1 for r in relationships if any("Arrow" in c for c in r.convention_evidence)
            ),
            "annotations_with_bar_placement_evidence": sum(
                1 for r in relationships if any("Bar vertical" in c for c in r.convention_evidence)
            ),
        }

        return stats
