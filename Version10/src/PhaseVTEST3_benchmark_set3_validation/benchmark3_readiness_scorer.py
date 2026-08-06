"""
benchmark3_readiness_scorer.py — Engineering Readiness Score for Benchmark Set 3.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from benchmark3_models import ReadinessScore


class Benchmark3ReadinessScorer:

    def score(
        self,
        beams: Dict[str, Any],
        gn: Dict[str, Any],
        reinf: Dict[str, Any],
        interp: Dict[str, Any],
        bars: Dict[str, Any],
        prod: Dict[str, Any],
        pipeline: Dict[str, Any],
        audit: Dict[str, Any],
    ) -> Tuple[List[ReadinessScore], float, str]:
        scores: List[ReadinessScore] = []

        # Beam Discovery
        beam_cnt = beams.get("total_beams", 0)
        s_beam = min(100.0, 100.0 if beam_cnt >= 10 else 100.0 * beam_cnt / 10)
        if beams.get("duplicate_beams"):
            s_beam *= 0.8
        scores.append(ReadinessScore(
            "Beam Discovery", round(s_beam, 1),
            detail=f"{beam_cnt} beams, geometry coverage {beams.get('geometry_coverage_pct', 0)}%",
        ))

        # General Notes Parsing
        if gn.get("engineering_context_available"):
            conf = float(gn.get("parse_confidence") or 0.5)
            s_gn = round(100.0 * conf, 1)
            if gn.get("development_length_table", 0) > 0:
                s_gn = min(100.0, s_gn + 10)
        else:
            s_gn = 0.0
        scores.append(ReadinessScore(
            "General Notes Parsing", s_gn,
            detail=f"DL entries={gn.get('development_length_table', 0)}, "
                   f"cover rules={gn.get('cover_rules', 0)}",
        ))

        # Annotation Discovery
        ann = reinf.get("reinforcement_annotations", 0)
        s_ann = min(100.0, 100.0 if ann >= 50 else 100.0 * ann / 50)
        scores.append(ReadinessScore(
            "Annotation Discovery", round(s_ann, 1),
            detail=f"{ann} annotations across {reinf.get('beams_with_annotations', 0)} beams",
        ))

        # Semantic Interpretation
        s_sem = interp.get("semantic_coverage_pct", 0.0)
        scores.append(ReadinessScore(
            "Semantic Interpretation", round(s_sem, 1),
            detail=f"{interp.get('semantic_objects', 0)} semantic objects",
        ))

        # Geometry Context
        s_geo = interp.get("geometry_coverage_pct", 0.0)
        scores.append(ReadinessScore(
            "Geometry Context", round(s_geo, 1),
            detail=f"{interp.get('geometry_contexts', 0)} geometry contexts",
        ))

        # Drawing Relationships
        s_rel = interp.get("relationship_coverage_pct", 0.0)
        scores.append(ReadinessScore(
            "Drawing Relationships", round(s_rel, 1),
            detail=f"{interp.get('drawing_relationships', 0)} relationships",
        ))

        # Engineering Bar Generation
        s_bar = bars.get("reinforcement_coverage_pct", 0.0)
        scores.append(ReadinessScore(
            "Engineering Bar Generation", round(s_bar, 1),
            detail=f"{bars.get('beams_with_bars', 0)}/{bars.get('engineering_bar_models', 0)} beams with bars",
        ))

        # Production Workbook Generation
        if prod.get("workbook_generated") and prod.get("steel_quantity_kg", 0) > 0:
            s_prod = 100.0
        elif prod.get("workbook_generated"):
            s_prod = 70.0
        else:
            s_prod = 0.0
        scores.append(ReadinessScore(
            "Production Workbook Generation", s_prod,
            detail=f"steel={prod.get('steel_quantity_kg', 0):.1f} kg, "
                   f"BBS rows={prod.get('bbs_rows', 0)}",
        ))

        # Pipeline completion bonus/penalty
        pipe_rate = pipeline.get("success_rate_pct", 0.0)
        overall = round(sum(s.score for s in scores) / len(scores), 1)

        # Penalise generalization failures
        if not audit.get("all_checks_passed"):
            overall = round(overall * 0.85, 1)

        # Penalise pipeline failures
        if pipe_rate < 100:
            overall = round(overall * (pipe_rate / 100), 1)

        classification = self._classify(overall)
        return scores, overall, classification

    @staticmethod
    def _classify(score: float) -> str:
        if score >= 80:
            return "PRODUCTION READY"
        if score >= 60:
            return "ENGINEERING READY"
        if score >= 40:
            return "PARTIALLY READY"
        return "NOT READY"
