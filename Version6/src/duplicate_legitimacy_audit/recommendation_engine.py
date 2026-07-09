"""Deterministic engineering recommendations for duplicate suppression."""

from __future__ import annotations

from typing import Any, Dict, List

from src.duplicate_legitimacy_audit.duplicate_group_loader import DuplicateLegitimacy, LEGITIMATE_CLASSES, RISK_CLASSES


RECOMMENDATION_MAP = {
    DuplicateLegitimacy.TRUE_GRAPHICAL_REPEAT: {
        "recommendation": "Duplicate correctly merged. Keep suppression rule.",
        "action": "KEEP_SUPPRESSION",
        "expected_impact": "No steel loss",
        "priority": "LOW",
    },
    DuplicateLegitimacy.TRUE_DUPLICATE: {
        "recommendation": "Duplicate correctly merged. Keep suppression rule.",
        "action": "KEEP_SUPPRESSION",
        "expected_impact": "No steel loss",
        "priority": "LOW",
    },
    DuplicateLegitimacy.VALID_MERGE: {
        "recommendation": "Duplicate correctly merged. Keep suppression rule.",
        "action": "KEEP_SUPPRESSION",
        "expected_impact": "No steel loss",
        "priority": "LOW",
    },
    DuplicateLegitimacy.REINFORCEMENT_REGION_VARIANT: {
        "recommendation": "Independent reinforcement regions detected. Review duplicate signature.",
        "action": "REVIEW_SIGNATURE",
        "expected_impact": "Potential steel recovery",
        "priority": "HIGH",
    },
    DuplicateLegitimacy.LEFT_RIGHT_VARIANT: {
        "recommendation": "Left/right placement differs. Incorporate placement-aware signatures.",
        "action": "PLACEMENT_AWARE_SIGNATURE",
        "expected_impact": "Potential steel recovery",
        "priority": "HIGH",
    },
    DuplicateLegitimacy.TOP_BOTTOM_VARIANT: {
        "recommendation": "Top/bottom placement differs. Incorporate position-aware signatures.",
        "action": "POSITION_AWARE_SIGNATURE",
        "expected_impact": "Potential steel recovery",
        "priority": "HIGH",
    },
    DuplicateLegitimacy.SPAN_VARIANT: {
        "recommendation": "Different beam stations detected. Incorporate station-aware signatures.",
        "action": "STATION_AWARE_SIGNATURE",
        "expected_impact": "Potential steel recovery",
        "priority": "HIGH",
    },
    DuplicateLegitimacy.SUPPORT_VARIANT: {
        "recommendation": "Support regions differ. Support-aware suppression recommended.",
        "action": "SUPPORT_AWARE_SUPPRESSION",
        "expected_impact": "Potential steel recovery",
        "priority": "HIGH",
    },
    DuplicateLegitimacy.CENTER_VARIANT: {
        "recommendation": "Center-span reinforcement differs. Review center-span duplicate policy.",
        "action": "CENTER_SPAN_REVIEW",
        "expected_impact": "Potential steel recovery",
        "priority": "MEDIUM",
    },
    DuplicateLegitimacy.LEADER_VARIANT: {
        "recommendation": "Leader context differs. Improve leader-aware duplicate detection.",
        "action": "LEADER_AWARE_DETECTION",
        "expected_impact": "Potential steel recovery",
        "priority": "HIGH",
    },
    DuplicateLegitimacy.POTENTIAL_ENGINEERING_BAR: {
        "recommendation": "Potential independent engineering bars suppressed. Manual engineering review required.",
        "action": "MANUAL_REVIEW",
        "expected_impact": "Likely steel loss",
        "priority": "CRITICAL",
    },
    DuplicateLegitimacy.LIKELY_ENGINEERING_BAR: {
        "recommendation": "Independent reinforcement regions detected. Review duplicate signature.",
        "action": "REVIEW_SIGNATURE",
        "expected_impact": "Likely steel loss",
        "priority": "CRITICAL",
    },
    DuplicateLegitimacy.INCORRECT_SUPPRESSION: {
        "recommendation": "Duplicate suppression appears incorrect. Review duplicate signature and station context.",
        "action": "CORRECT_SUPPRESSION",
        "expected_impact": "Likely steel loss",
        "priority": "CRITICAL",
    },
    DuplicateLegitimacy.INSUFFICIENT_EVIDENCE: {
        "recommendation": "Insufficient engineering evidence. Collect station, leader, and region context before changing rules.",
        "action": "COLLECT_EVIDENCE",
        "expected_impact": "Unknown",
        "priority": "MEDIUM",
    },
    DuplicateLegitimacy.UNKNOWN: {
        "recommendation": "Classification unknown. Manual engineering review required.",
        "action": "MANUAL_REVIEW",
        "expected_impact": "Unknown",
        "priority": "MEDIUM",
    },
}


class DuplicateRecommendationEngine:
    """Generate deterministic recommendations per duplicate group."""

    def build_group_recommendation(
        self,
        classification: dict[str, Any],
        confidence: dict[str, Any],
    ) -> dict[str, Any]:
        legitimacy = DuplicateLegitimacy(classification.get("legitimacy_class"))
        template = RECOMMENDATION_MAP.get(legitimacy, RECOMMENDATION_MAP[DuplicateLegitimacy.UNKNOWN])
        return {
            "group_id": classification.get("group_id"),
            "signature": classification.get("signature"),
            "beam_id": classification.get("beam_id"),
            "legitimacy_class": legitimacy.value,
            "should_suppression_occur": classification.get("should_suppression_occur"),
            "confidence_score": confidence.get("confidence_score"),
            "confidence_band": confidence.get("confidence_band"),
            **template,
        }

    def build_all(self, group_results: List[dict[str, Any]]) -> dict[str, Any]:
        priority_counts: Dict[str, int] = {}
        for item in group_results:
            priority = item.get("priority", "MEDIUM")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        return {
            "recommendation_count": len(group_results),
            "priority_counts": priority_counts,
            "recommendations": group_results,
        }

    def build_health(
        self,
        group_results: List[dict[str, Any]],
        confidence_scores: List[dict[str, Any]],
    ) -> dict[str, Any]:
        total_groups = len(group_results)
        legitimate = sum(
            1
            for item in group_results
            if DuplicateLegitimacy(item.get("legitimacy_class")) in LEGITIMATE_CLASSES
            and item.get("should_suppression_occur")
        )
        incorrect = sum(
            1
            for item in group_results
            if DuplicateLegitimacy(item.get("legitimacy_class")) in RISK_CLASSES
            or item.get("legitimacy_class") == DuplicateLegitimacy.INCORRECT_SUPPRESSION.value
        )
        likely_bars = sum(
            1
            for item in group_results
            if item.get("legitimacy_class")
            in {
                DuplicateLegitimacy.LIKELY_ENGINEERING_BAR.value,
                DuplicateLegitimacy.POTENTIAL_ENGINEERING_BAR.value,
            }
        )
        suppressed_members = sum(len(item.get("suppressed_callouts") or []) for item in group_results)
        potential_steel_loss = sum(
            len(item.get("suppressed_callouts") or [])
            for item in group_results
            if not item.get("should_suppression_occur")
        )
        merge_accuracy = round((legitimate / total_groups) * 100, 2) if total_groups else 100.0
        suppression_accuracy = round(
            ((total_groups - incorrect) / total_groups) * 100, 2
        ) if total_groups else 100.0
        engineering_confidence = round(
            sum(item.get("confidence_score", 0.0) for item in confidence_scores) / max(len(confidence_scores), 1),
            2,
        )
        overall_duplicate_health = round(
            min(100.0, (suppression_accuracy * 0.5) + (engineering_confidence * 0.3) + (merge_accuracy * 0.2)),
            2,
        )
        overall_engineering_risk = round(max(0.0, 100.0 - overall_duplicate_health), 2)
        return {
            "duplicate_groups": total_groups,
            "legitimate_duplicates": legitimate,
            "incorrect_suppressions": incorrect,
            "likely_independent_engineering_bars": likely_bars,
            "suppressed_callout_count": suppressed_members,
            "potential_steel_loss_callouts": potential_steel_loss,
            "potential_steel_recovery": potential_steel_loss,
            "merge_accuracy_percent": merge_accuracy,
            "suppression_accuracy_percent": suppression_accuracy,
            "engineering_confidence": engineering_confidence,
            "overall_duplicate_health": overall_duplicate_health,
            "overall_engineering_risk": overall_engineering_risk,
        }
