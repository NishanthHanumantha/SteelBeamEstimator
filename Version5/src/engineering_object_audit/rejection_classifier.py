"""Deterministic engineering object rejection classification."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.engineering_object_audit.audit_collector import AuditCollector, REJECTION_CODES


class RejectionClassifier:
    """Evaluate the engineering object creation decision tree."""

    MAIN_BAR_ROLES = {"TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA", "SIDE_BAR", "STARTER"}

    def classify(
        self,
        item: dict[str, Any],
        indexes: dict[str, Any],
        dependencies: dict[str, Any],
        readiness: dict[str, Any],
        duplicate_info: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if item.get("normalized_bar_id"):
            return {
                "engineering_object_created": True,
                "primary_rejection_code": None,
                "secondary_codes": [],
                "blocking_stage": None,
            }

        primary, secondary, blocking_stage = self._evaluate(item, indexes, dependencies, readiness, duplicate_info)
        if primary not in REJECTION_CODES:
            primary = "UNKNOWN"
        secondary = [code for code in secondary if code in REJECTION_CODES and code != primary]
        return {
            "engineering_object_created": False,
            "primary_rejection_code": primary,
            "secondary_codes": secondary,
            "blocking_stage": blocking_stage,
        }

    def _evaluate(
        self,
        item: dict[str, Any],
        indexes: dict[str, Any],
        dependencies: dict[str, Any],
        readiness: dict[str, Any],
        duplicate_info: Optional[dict[str, Any]],
    ) -> Tuple[str, List[str], str]:
        secondary: List[str] = []

        if not item.get("classified"):
            if item.get("unknown"):
                return "UNSUPPORTED_NOTATION", secondary, "classification"
            return "NOT_REINFORCEMENT", secondary, "classification"

        if item.get("ambiguous") or item.get("multiple_interpretations"):
            secondary.append("AMBIGUOUS_CALLOUT")
            return "AMBIGUOUS_CALLOUT", secondary, "classification"

        if not item.get("associated") or not item.get("beam_association"):
            return "BEAM_NOT_ASSOCIATED", secondary, "association"

        if str(item.get("association_source") or "").upper() in {
            "MULTIPLE_CANDIDATES",
            "MULTIPLE_BEAM_CANDIDATES",
        }:
            return "MULTIPLE_BEAM_CANDIDATES", secondary, "association"

        if item.get("diameter_mm") is None:
            return "MISSING_DIAMETER", secondary, "specification"

        if item.get("role") in (None, "", "UNKNOWN"):
            return "MISSING_BAR_ROLE", secondary, "specification"

        if item.get("role") in self.MAIN_BAR_ROLES and item.get("quantity") is None:
            return "MISSING_QUANTITY", secondary, "specification"

        if item.get("spacing_mm") is not None and item.get("role") not in {"STIRRUP", "SPACER_BAR", "LINK_BAR"}:
            return "INVALID_SPACING", secondary, "specification"

        matching_bar = AuditCollector.matching_bar_id(item, indexes)
        signature = AuditCollector._inventory_signature(item)
        signature_claimants = sorted((indexes.get("claimants_by_signature") or {}).get(signature) or [])
        if signature_claimants and str(item.get("discovery_id")) != signature_claimants[0]:
            return "DUPLICATE_SUPPRESSED", secondary, "duplicate_resolution"

        if matching_bar:
            claimants = sorted((indexes.get("claimants_by_bar") or {}).get(matching_bar) or [])
            if claimants and str(item.get("discovery_id")) != claimants[0]:
                return "DUPLICATE_SUPPRESSED", secondary, "duplicate_resolution"

        if duplicate_info and duplicate_info.get("duplicate_type") == "SUSPICIOUS_DUPLICATE":
            return "DUPLICATE_SUPPRESSED", secondary, "duplicate_resolution"

        if not dependencies.get("geometry", {}).get("present"):
            return "MISSING_GEOMETRY", secondary, "dependency"

        if not dependencies.get("section", {}).get("present"):
            return "MISSING_SECTION", secondary, "dependency"

        if not dependencies.get("position", {}).get("present"):
            return "MISSING_POSITION", secondary, "dependency"

        if not dependencies.get("specification", {}).get("present"):
            return "MISSING_SPECIFICATION", secondary, "dependency"

        text_object = (indexes.get("text_by_geometry") or {}).get(str(item.get("geometry_id") or ""))
        if text_object and str(text_object.get("engineering_status") or "") == "GEOMETRY_ONLY":
            if not item.get("engineering_object_id"):
                return "MISSING_SPECIFICATION", secondary, "engineering_object"

        if item.get("engineering_object_id"):
            return "NORMALIZATION_FAILED", secondary, "normalization"

        if readiness.get("readiness_score", 0) >= 80:
            return "ENGINEERING_RULE_CONFLICT", secondary, "engineering_object"

        return "UNKNOWN", secondary, "engineering_object"
