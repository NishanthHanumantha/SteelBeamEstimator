"""Duplicate Suppression Legitimacy Audit orchestrator."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.duplicate_legitimacy_audit.annotation_context import AnnotationContextBuilder
from src.duplicate_legitimacy_audit.duplicate_confidence import DuplicateConfidenceScorer
from src.duplicate_legitimacy_audit.duplicate_group_loader import (
    ENGINE_VERSION,
    MODEL_VERSION,
    PHASE,
    DuplicateGroupLoader,
    DuplicateLegitimacy,
    LEGITIMATE_CLASSES,
    RISK_CLASSES,
    default_paths,
)
from src.duplicate_legitimacy_audit.engineering_region_detector import EngineeringRegionDetector
from src.duplicate_legitimacy_audit.export import DuplicateLegitimacyExporter, DuplicateLegitimacyValidator
from src.duplicate_legitimacy_audit.graphical_repeat_detector import GraphicalRepeatDetector
from src.duplicate_legitimacy_audit.leader_analysis import LeaderAnalysis
from src.duplicate_legitimacy_audit.recommendation_engine import DuplicateRecommendationEngine
from src.duplicate_legitimacy_audit.stationing_comparator import StationingComparator
from src.duplicate_legitimacy_audit.suppression_legitimacy import SuppressionLegitimacyClassifier


class DuplicateLegitimacyAuditEngine:
    """Run read-only duplicate suppression legitimacy audit."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or Path.cwd()
        self._paths = default_paths(self._project_root)

    def run(self) -> dict[str, Any]:
        snapshot = DuplicateGroupLoader(self._project_root).load()
        duplicate_groups = snapshot.get("duplicate_groups") or []

        context_builder = AnnotationContextBuilder()
        graphical_detector = GraphicalRepeatDetector()
        region_detector = EngineeringRegionDetector()
        stationing_comparator = StationingComparator()
        leader_analysis = LeaderAnalysis()
        classifier = SuppressionLegitimacyClassifier()
        confidence_scorer = DuplicateConfidenceScorer()
        recommendation_engine = DuplicateRecommendationEngine()

        group_analyses: List[dict[str, Any]] = []
        engineering_contexts: List[dict[str, Any]] = []
        confidence_scores: List[dict[str, Any]] = []
        root_cause_chains: List[dict[str, Any]] = []
        decision_matrix: List[dict[str, Any]] = []
        group_recommendations: List[dict[str, Any]] = []

        for group in duplicate_groups:
            group_context = context_builder.build_group_context(group)
            contexts = group_context.get("member_contexts") or []
            graphical = graphical_detector.analyze(group, contexts)
            region = region_detector.analyze(contexts)
            stationing = stationing_comparator.analyze(contexts)
            leader = leader_analysis.analyze(contexts)

            classification = classifier.classify_group(
                group,
                group_context,
                graphical,
                region,
                stationing,
                leader,
            )
            confidence = confidence_scorer.score_group(
                classification,
                group_context,
                graphical,
                region,
                stationing,
                leader,
            )
            recommendation = recommendation_engine.build_group_recommendation(classification, confidence)
            root_cause = self._build_root_cause_chain(
                group,
                classification,
                confidence,
                recommendation,
                graphical,
                region,
                stationing,
                leader,
            )
            decision_record = self._build_decision_matrix_record(
                group,
                classification,
                confidence,
                recommendation,
                group_context,
                graphical,
                region,
                stationing,
                leader,
            )

            analysis = {
                **classification,
                "confidence_score": confidence.get("confidence_score"),
                "confidence_band": confidence.get("confidence_band"),
                "confidence_components": confidence.get("components"),
                "recommendation": recommendation.get("recommendation"),
                "recommendation_action": recommendation.get("action"),
                "recommendation_priority": recommendation.get("priority"),
                "graphical_analysis": graphical,
                "region_analysis": region,
                "stationing_analysis": stationing,
                "leader_analysis": leader,
            }

            group_analyses.append(analysis)
            engineering_contexts.append(group_context)
            confidence_scores.append(confidence)
            root_cause_chains.append(root_cause)
            decision_matrix.append(decision_record)
            group_recommendations.append(recommendation)

        recommendations = recommendation_engine.build_all(group_recommendations)
        health = recommendation_engine.build_health(group_analyses, confidence_scores)
        statistics = self._build_statistics(group_analyses, confidence_scores)
        summary = self._build_summary(group_analyses, health, recommendations)

        result: dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self._paths["output_dir"]),
            "engineering_code_modified": False,
            "prior_phase_outputs_modified": False,
            "engineering_pipeline_frozen": True,
            "parser_executed": False,
            "dxf_accessed": False,
            "read_only_analysis": True,
            "load_status": snapshot.get("load_status"),
            "duplicate_groups": duplicate_groups,
            "group_analyses": group_analyses,
            "engineering_contexts": engineering_contexts,
            "confidence_scores": confidence_scores,
            "root_cause_chains": root_cause_chains,
            "decision_matrix": decision_matrix,
            "recommendations": recommendations,
            "health": health,
            "statistics": statistics,
            "summary": summary,
        }

        output_dir = self._paths["output_dir"]
        DuplicateLegitimacyExporter.export_all(output_dir, result)
        validation = DuplicateLegitimacyValidator().validate(result)
        export_validation = DuplicateLegitimacyValidator().validate_exports(output_dir, result)
        result["validation_report"] = validation
        result["export_validation"] = export_validation
        DuplicateLegitimacyExporter.print_summary(result)
        return result

    @staticmethod
    def _build_root_cause_chain(
        group: dict[str, Any],
        classification: dict[str, Any],
        confidence: dict[str, Any],
        recommendation: dict[str, Any],
        graphical: dict[str, Any],
        region: dict[str, Any],
        stationing: dict[str, Any],
        leader: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "group_id": group.get("group_id"),
            "signature": group.get("signature"),
            "beam_id": group.get("beam_id"),
            "original_callouts": classification.get("original_callouts"),
            "suppressed_callouts": classification.get("suppressed_callouts"),
            "engineering_similarities": classification.get("engineering_similarities"),
            "engineering_differences": classification.get("engineering_differences"),
            "why_suppression_occurred": group.get("duplicate_type"),
            "should_suppression_occur": classification.get("should_suppression_occur"),
            "legitimacy_class": classification.get("legitimacy_class"),
            "confidence_score": confidence.get("confidence_score"),
            "confidence_band": confidence.get("confidence_band"),
            "engineering_recommendation": recommendation.get("recommendation"),
            "evidence": {
                "engineering_evidence": classification.get("engineering_evidence"),
                "graphical_analysis": graphical,
                "region_analysis": region,
                "stationing_analysis": stationing,
                "leader_analysis": leader,
            },
        }

    @staticmethod
    def _build_decision_matrix_record(
        group: dict[str, Any],
        classification: dict[str, Any],
        confidence: dict[str, Any],
        recommendation: dict[str, Any],
        group_context: dict[str, Any],
        graphical: dict[str, Any],
        region: dict[str, Any],
        stationing: dict[str, Any],
        leader: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "group_id": group.get("group_id"),
            "signature": group.get("signature"),
            "beam_id": group.get("beam_id"),
            "member_count": group.get("member_count"),
            "normalized_count": group.get("normalized_count"),
            "rejected_count": group.get("rejected_count"),
            "duplicate_type": group.get("duplicate_type"),
            "legitimacy_class": classification.get("legitimacy_class"),
            "should_suppression_occur": classification.get("should_suppression_occur"),
            "confidence_score": confidence.get("confidence_score"),
            "confidence_band": confidence.get("confidence_band"),
            "recommendation": recommendation.get("recommendation"),
            "recommendation_action": recommendation.get("action"),
            "comparison_matrix": group_context.get("comparison_matrix"),
            "graphical_analysis": graphical,
            "region_analysis": region,
            "stationing_analysis": stationing,
            "leader_analysis": leader,
            "member_classifications": classification.get("member_classifications"),
        }

    @staticmethod
    def _build_statistics(
        group_analyses: List[dict[str, Any]],
        confidence_scores: List[dict[str, Any]],
    ) -> dict[str, Any]:
        legitimacy_counts = Counter(item.get("legitimacy_class") for item in group_analyses)
        confidence_bands = Counter(item.get("confidence_band") for item in confidence_scores)
        risk_groups = [
            item
            for item in group_analyses
            if item.get("legitimacy_class") in {member.value for member in RISK_CLASSES}
            or item.get("legitimacy_class") == DuplicateLegitimacy.INCORRECT_SUPPRESSION.value
        ]
        legitimate_groups = [
            item
            for item in group_analyses
            if DuplicateLegitimacy(item.get("legitimacy_class")) in LEGITIMATE_CLASSES
            and item.get("should_suppression_occur")
        ]
        return {
            "duplicate_group_count": len(group_analyses),
            "legitimacy_class_counts": dict(sorted(legitimacy_counts.items())),
            "confidence_band_counts": dict(sorted(confidence_bands.items())),
            "average_confidence_score": round(
                sum(item.get("confidence_score", 0.0) for item in confidence_scores)
                / max(len(confidence_scores), 1),
                2,
            ),
            "risk_group_count": len(risk_groups),
            "legitimate_group_count": len(legitimate_groups),
            "suppressed_callout_count": sum(len(item.get("suppressed_callouts") or []) for item in group_analyses),
        }

    @staticmethod
    def _build_summary(
        group_analyses: List[dict[str, Any]],
        health: dict[str, Any],
        recommendations: dict[str, Any],
    ) -> dict[str, Any]:
        risk_sorted = sorted(
            group_analyses,
            key=lambda item: (
                0 if item.get("legitimacy_class") in {member.value for member in RISK_CLASSES} else 1,
                -float(item.get("confidence_score") or 0.0),
            ),
        )
        highest_risk = [
            {
                "group_id": item.get("group_id"),
                "signature": item.get("signature"),
                "beam_id": item.get("beam_id"),
                "legitimacy_class": item.get("legitimacy_class"),
                "confidence_score": item.get("confidence_score"),
                "should_suppression_occur": item.get("should_suppression_occur"),
            }
            for item in risk_sorted[:5]
        ]
        return {
            "total_duplicate_groups": health.get("duplicate_groups", 0),
            "legitimate_duplicates": health.get("legitimate_duplicates", 0),
            "potential_incorrect_suppressions": health.get("incorrect_suppressions", 0),
            "likely_independent_engineering_bars": health.get("likely_independent_engineering_bars", 0),
            "potential_steel_recovery": health.get("potential_steel_recovery", 0),
            "overall_duplicate_health": health.get("overall_duplicate_health", 0),
            "overall_engineering_risk": health.get("overall_engineering_risk", 0),
            "highest_risk_groups": highest_risk,
            "top_recommendations": (recommendations.get("recommendations") or [])[:5],
        }
