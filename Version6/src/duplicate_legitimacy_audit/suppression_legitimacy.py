"""Deterministic duplicate suppression legitimacy classifier."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.duplicate_legitimacy_audit.duplicate_group_loader import DuplicateLegitimacy, LEGITIMATE_CLASSES, RISK_CLASSES


class SuppressionLegitimacyClassifier:
    """Apply deterministic decision tree to duplicate groups."""

    def classify_group(
        self,
        group: dict[str, Any],
        group_context: dict[str, Any],
        graphical: dict[str, Any],
        region: dict[str, Any],
        stationing: dict[str, Any],
        leader: dict[str, Any],
    ) -> dict[str, Any]:
        members = group.get("members") or []
        contexts = group_context.get("member_contexts") or []
        suppressed = [item for item in contexts if item.get("suppressed")]
        accepted = [item for item in contexts if not item.get("suppressed")]
        shared_bar_ids = group.get("shared_bar_ids") or []
        rejected_count = int(group.get("rejected_count") or 0)
        normalized_count = int(group.get("normalized_count") or 0)

        legitimacy, should_suppress, evidence = self._decide(
            group,
            group_context,
            graphical,
            region,
            stationing,
            leader,
            shared_bar_ids,
            rejected_count,
            normalized_count,
            suppressed,
            accepted,
        )

        member_classifications = self._classify_members(
            legitimacy,
            contexts,
            graphical,
            stationing,
            region,
            leader,
        )

        return {
            "group_id": group.get("group_id"),
            "signature": group.get("signature"),
            "beam_id": group.get("beam_id"),
            "legitimacy_class": legitimacy.value,
            "should_suppression_occur": should_suppress,
            "suppression_reason": group.get("duplicate_type"),
            "engineering_evidence": evidence,
            "original_callouts": [item.get("discovery_id") for item in accepted],
            "suppressed_callouts": [item.get("discovery_id") for item in suppressed],
            "member_classifications": member_classifications,
            "engineering_similarities": self._similarities(group_context),
            "engineering_differences": self._differences(group_context, stationing, region, leader),
        }

    def _decide(
        self,
        group: dict[str, Any],
        group_context: dict[str, Any],
        graphical: dict[str, Any],
        region: dict[str, Any],
        stationing: dict[str, Any],
        leader: dict[str, Any],
        shared_bar_ids: List[str],
        rejected_count: int,
        normalized_count: int,
        suppressed: List[dict[str, Any]],
        accepted: List[dict[str, Any]],
    ) -> Tuple[DuplicateLegitimacy, bool, List[str]]:
        evidence: List[str] = []
        matrix = group_context.get("comparison_matrix") or {}

        if graphical.get("all_coordinates_equal"):
            evidence.append("All member coordinates match within tolerance")
            return DuplicateLegitimacy.TRUE_GRAPHICAL_REPEAT, True, evidence

        if leader.get("leader_variant"):
            evidence.append("Leader ownership differs between duplicate members")
            if rejected_count > 0:
                return DuplicateLegitimacy.LEADER_VARIANT, False, evidence
            return DuplicateLegitimacy.LEADER_VARIANT, True, evidence

        if stationing.get("support_variant"):
            evidence.append("Support zone differs across duplicate members")
            supports = set(stationing.get("unique_supports") or [])
            if "CENTER" in supports:
                return DuplicateLegitimacy.CENTER_VARIANT, rejected_count == 0, evidence
            return DuplicateLegitimacy.SUPPORT_VARIANT, rejected_count == 0, evidence

        position_matrix = matrix.get("position") or {}
        if not position_matrix.get("uniform", True):
            evidence.append("Position differs while specification matches")
            positions = position_matrix.get("values") or []
            position_text = " ".join(str(item) for item in positions).upper()
            if any(token in position_text for token in ("LEFT", "RIGHT")):
                return DuplicateLegitimacy.LEFT_RIGHT_VARIANT, rejected_count == 0, evidence
            if any(token in position_text for token in ("TOP", "BOTTOM")):
                return DuplicateLegitimacy.TOP_BOTTOM_VARIANT, rejected_count == 0, evidence

        if stationing.get("station_variant") or stationing.get("span_variant"):
            evidence.append("Beam station or span coordinates differ materially")
            if rejected_count > 0 and normalized_count == 0:
                return DuplicateLegitimacy.LIKELY_ENGINEERING_BAR, False, evidence
            if rejected_count > 0:
                return DuplicateLegitimacy.SPAN_VARIANT, False, evidence
            if len(shared_bar_ids) > 1:
                return DuplicateLegitimacy.REINFORCEMENT_REGION_VARIANT, True, evidence
            return DuplicateLegitimacy.SPAN_VARIANT, True, evidence

        if region.get("region_variant") or region.get("layer_variant"):
            evidence.append("Engineering region or drawing layer differs")
            if rejected_count > 0:
                return DuplicateLegitimacy.REINFORCEMENT_REGION_VARIANT, False, evidence
            return DuplicateLegitimacy.REINFORCEMENT_REGION_VARIANT, True, evidence

        if len(shared_bar_ids) == 1 and normalized_count > 1 and rejected_count == 0:
            evidence.append("Multiple callouts merged to one normalized bar")
            if graphical.get("any_coordinates_equal"):
                return DuplicateLegitimacy.TRUE_DUPLICATE, True, evidence
            return DuplicateLegitimacy.VALID_MERGE, True, evidence

        if len(shared_bar_ids) > 1:
            evidence.append("Multiple engineering bars share signature")
            return DuplicateLegitimacy.REINFORCEMENT_REGION_VARIANT, True, evidence

        if rejected_count > 0 and normalized_count > 0:
            evidence.append("Accepted and suppressed members share signature")
            if graphical.get("any_coordinates_equal"):
                return DuplicateLegitimacy.TRUE_GRAPHICAL_REPEAT, True, evidence
            evidence.append("Independent coordinates with duplicate suppression")
            return DuplicateLegitimacy.INCORRECT_SUPPRESSION, False, evidence

        if rejected_count > 0 and normalized_count == 0:
            evidence.append("All members rejected with no normalized bar")
            if stationing.get("x_spread", 0) > 0 or stationing.get("y_spread", 0) > 0:
                return DuplicateLegitimacy.POTENTIAL_ENGINEERING_BAR, False, evidence
            return DuplicateLegitimacy.INSUFFICIENT_EVIDENCE, False, evidence

        if graphical.get("graphical_repeat_likely"):
            evidence.append("Partial coordinate overlap suggests graphical repeat")
            return DuplicateLegitimacy.TRUE_DUPLICATE, True, evidence

        comparison = group_context.get("comparison_matrix") or {}
        if comparison and all(item.get("uniform") for item in comparison.values()):
            evidence.append("All engineering comparison fields uniform")
            return DuplicateLegitimacy.TRUE_DUPLICATE, True, evidence

        evidence.append("Insufficient engineering evidence to classify further")
        return DuplicateLegitimacy.INSUFFICIENT_EVIDENCE, False, evidence

    def _classify_members(
        self,
        group_legitimacy: DuplicateLegitimacy,
        contexts: List[dict[str, Any]],
        graphical: dict[str, Any],
        stationing: dict[str, Any],
        region: dict[str, Any],
        leader: dict[str, Any],
    ) -> List[dict[str, Any]]:
        primary_id = sorted(str(item.get("discovery_id")) for item in contexts)[0] if contexts else None
        rows: List[dict[str, Any]] = []
        for item in contexts:
            discovery_id = str(item.get("discovery_id"))
            if not item.get("suppressed"):
                member_class = group_legitimacy.value
            elif group_legitimacy in LEGITIMATE_CLASSES:
                member_class = DuplicateLegitimacy.VALID_MERGE.value
            elif discovery_id == primary_id:
                member_class = group_legitimacy.value
            else:
                member_class = group_legitimacy.value
            rows.append(
                {
                    "discovery_id": discovery_id,
                    "suppressed": item.get("suppressed", False),
                    "legitimacy_class": member_class,
                    "normalized_bar_id": item.get("normalization_result"),
                }
            )
        return rows

    @staticmethod
    def _similarities(group_context: dict[str, Any]) -> List[str]:
        matrix = group_context.get("comparison_matrix") or {}
        return [field for field, data in matrix.items() if data.get("uniform")]

    @staticmethod
    def _differences(
        group_context: dict[str, Any],
        stationing: dict[str, Any],
        region: dict[str, Any],
        leader: dict[str, Any],
    ) -> List[str]:
        differences: List[str] = []
        matrix = group_context.get("comparison_matrix") or {}
        for field, data in matrix.items():
            if not data.get("uniform"):
                differences.append(field)
        if stationing.get("station_variant"):
            differences.append("beam_station")
        if stationing.get("support_variant"):
            differences.append("support")
        if region.get("region_variant"):
            differences.append("engineering_region")
        if leader.get("leader_variant"):
            differences.append("leader")
        return sorted(set(differences))
