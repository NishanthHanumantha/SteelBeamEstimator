"""
reinforcement_reporter.py — 9-section engineering report for Phase R.1.
"""

from __future__ import annotations

import datetime
import logging
from typing import Dict, List, Optional

from .reinforcement_models import (
    BeamDetail,
    ReinforcementAnnotation,
    R1BeamReinforcementModel,
    ROLE_UNKNOWN,
)
from .reinforcement_validator import ValidationReport

log = logging.getLogger(__name__)


class ReinforcementReporter:
    """Generates the 9-section generalized reinforcement report."""

    def generate(
        self,
        details:     List[BeamDetail],
        annotations: Dict[str, List[ReinforcementAnnotation]],
        models:      Dict[str, R1BeamReinforcementModel],
        statistics:  dict,
        validation:  ValidationReport,
    ) -> dict:
        return {
            "report_id":      f"R1-REPORT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "generated_at":   datetime.datetime.now().isoformat(),
            "model_version":  "7.3.0",
            "phase":          "R.1",
            "sections": {
                "1_executive_summary":         self._exec_summary(statistics, validation),
                "2_beam_detail_discovery":     self._discovery_summary(details),
                "3_annotation_discovery":      self._annotation_summary(annotations),
                "4_reinforcement_classification": self._classification_summary(statistics),
                "5_engineering_role_summary":  self._role_summary(statistics, models),
                "6_coverage_statistics":       self._coverage_stats(statistics),
                "7_unknown_objects":           self._unknown_objects(annotations),
                "8_validation_summary":        self._validation_summary(validation),
                "9_engineering_recommendations": self._recommendations(statistics, validation),
            },
        }

    # ──────────────────────────────────────────────────────────────────────────
    def _exec_summary(self, stats: dict, val: ValidationReport) -> dict:
        return {
            "phase":         "R.1 — Generalized Reinforcement Discovery",
            "model_version": "7.3.0",
            "total_beams":   stats["total_beams"],
            "coverage_pct":  stats["coverage_pct"],
            "validation":    val.overall,
            "passed_rules":  val.passed,
            "failed_rules":  val.failed,
            "status":        "SUCCESS" if val.overall == "PASS" else "PARTIAL",
        }

    def _discovery_summary(self, details: List[BeamDetail]) -> dict:
        return {
            "total_discovered":  len(details),
            "source":            "V.ROOT.1 beam_registry (dynamic, no hardcoded IDs)",
            "beam_ids":          [d.beam_id for d in details],
            "avg_search_radius": details[0].detail_radius if details else 0,
        }

    def _annotation_summary(self, annotations: Dict[str, List[ReinforcementAnnotation]]) -> dict:
        total = sum(len(v) for v in annotations.values())
        rebar = sum(1 for anns in annotations.values() for a in anns if a.is_reinforcement)
        return {
            "total_annotations":  total,
            "rebar_annotations":  rebar,
            "noise_annotations":  total - rebar,
            "avg_per_beam":       round(total / len(annotations), 1) if annotations else 0,
        }

    def _classification_summary(self, stats: dict) -> dict:
        return {
            "classified":    stats["classified_annotations"],
            "unknown":       stats["unknown_annotations"],
            "coverage_pct":  stats["coverage_pct"],
            "unknown_pct":   stats["unknown_pct"],
        }

    def _role_summary(self, stats: dict, models: dict) -> dict:
        return {
            "top_main_beams":    stats["beams_with_top_main"],
            "bottom_main_beams": stats["beams_with_bottom_main"],
            "stirrup_beams":     stats["beams_with_stirrups"],
            "complete_beams":    stats["beams_classification_complete"],
            "role_distribution": stats["role_distribution"],
        }

    def _coverage_stats(self, stats: dict) -> dict:
        return {
            "coverage_pct":  stats["coverage_pct"],
            "unknown_pct":   stats["unknown_pct"],
            "avg_groups":    stats["avg_groups_per_beam"],
            "top_bar_qty":   stats["top_bar_quantity"],
            "bottom_bar_qty": stats["bottom_bar_quantity"],
            "stirrup_qty":   stats["stirrup_quantity"],
        }

    def _unknown_objects(
        self, annotations: Dict[str, List[ReinforcementAnnotation]]
    ) -> dict:
        unknowns = []
        for beam_id, anns in annotations.items():
            for ann in anns:
                if ann.is_reinforcement and ann.role == ROLE_UNKNOWN:
                    unknowns.append({
                        "beam_id":  beam_id,
                        "text":     ann.clean_text,
                        "position": (ann.x, ann.y),
                    })
        return {"count": len(unknowns), "objects": unknowns[:50]}

    def _validation_summary(self, val: ValidationReport) -> dict:
        return {
            "overall": val.overall,
            "passed":  val.passed,
            "failed":  val.failed,
            "warned":  val.warned,
            "rules":   [
                {"id": r.rule_id, "name": r.name, "status": r.status, "message": r.message}
                for r in val.rules
            ],
        }

    def _recommendations(self, stats: dict, val: ValidationReport) -> list:
        recs = []
        if stats["unknown_pct"] > 20:
            recs.append(
                "High unknown rate — consider expanding regex patterns to cover "
                "additional local annotation conventions."
            )
        if stats["beams_with_stirrups"] < 5:
            recs.append(
                "Stirrup callouts are limited in this drawing — stirrup data should be "
                "sourced from section view DXF or engineering notes."
            )
        if val.failed > 0:
            recs.append(
                "Validation failures detected — review failed rules and refine "
                "geometry thresholds if needed."
            )
        if not recs:
            recs.append("All checks passed.  R.1 engine is production-ready.")
        return recs
