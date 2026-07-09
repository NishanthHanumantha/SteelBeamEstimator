"""Per-recovery candidate engineering contribution analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Set


class RecoveryContributionAnalyzer:
    """Quantify engineering impact for every recovered object."""

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        registry_entries = snapshot.get("registry_entries") or []
        recovered_objects = snapshot.get("recovered_objects") or []
        bars = snapshot.get("bars") or []
        bbs_records = snapshot.get("bbs_records") or []
        steel_weights = snapshot.get("steel_weights") or []
        excel_validation = snapshot.get("excel_validation") or {}

        recovered_bar_ids = set(recovery_index.get("recovered_bar_ids") or [])
        bar_by_id = {str(bar.get("bar_id")): bar for bar in bars if bar.get("bar_id")}
        steel_by_bar = {str(item.get("bar_id")): item for item in steel_weights if item.get("bar_id")}
        bbs_bar_ids = self._bbs_bar_ids(bbs_records)
        excel_bar_ids = self._excel_bar_ids(excel_validation)

        object_by_discovery = {
            str(obj.get("source_discovery_id") or obj.get("discovery_id") or ""): obj
            for obj in recovered_objects
        }

        contributions: List[dict[str, Any]] = []
        for entry in registry_entries:
            discovery_id = str(entry.get("discovery_id") or "")
            recovery_id = str(entry.get("recovery_id") or "")
            bar_id = str(entry.get("normalized_bar_id") or "")
            bar = bar_by_id.get(bar_id, {})
            obj = object_by_discovery.get(discovery_id, {})

            added_to_bbs = bar_id in bbs_bar_ids
            steel_record = steel_by_bar.get(bar_id, {})
            weight = steel_record.get("weight_kg")
            added_steel = weight is not None and float(weight) > 0
            added_diameter = bar.get("diameter_mm") or obj.get("diameter_mm")
            excel_row = bar_id in excel_bar_ids or str(entry.get("beam_id") or "") in self._excel_beam_ids(excel_validation)

            impact_flags = [
                added_to_bbs,
                added_steel,
                bool(added_diameter),
                excel_row,
                bar.get("status") == "NORMALIZED",
            ]
            score = sum(1 for flag in impact_flags if flag)
            contribution = self._contribution_band(score, added_steel, added_to_bbs, bar.get("status") == "NORMALIZED")

            contributions.append(
                {
                    "recovery_id": recovery_id,
                    "discovery_id": discovery_id,
                    "bar_id": bar_id,
                    "beam_id": entry.get("beam_id") or bar.get("beam_id") or obj.get("beam"),
                    "role": bar.get("role") or obj.get("role"),
                    "added_to_bbs": added_to_bbs,
                    "added_steel": added_steel,
                    "added_diameter_mm": added_diameter,
                    "excel_row": excel_row,
                    "normalized": bar.get("status") == "NORMALIZED",
                    "engineering_contribution": contribution,
                    "impact_score": score,
                    "confidence": entry.get("confidence"),
                    "legitimacy_class": entry.get("legitimacy_class"),
                }
            )

        return {
            "contribution_count": len(contributions),
            "contributions": contributions,
            "high_contribution_count": len([item for item in contributions if item["engineering_contribution"] == "HIGH"]),
            "medium_contribution_count": len([item for item in contributions if item["engineering_contribution"] == "MEDIUM"]),
            "low_contribution_count": len([item for item in contributions if item["engineering_contribution"] == "LOW"]),
        }

    @staticmethod
    def _contribution_band(score: int, added_steel: bool, added_to_bbs: bool, normalized: bool) -> str:
        if added_steel and (added_to_bbs or normalized):
            return "HIGH"
        if normalized or added_to_bbs or score >= 3:
            return "HIGH" if normalized and score >= 3 else "MEDIUM"
        if score >= 2:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _bbs_bar_ids(bbs_records: List[dict[str, Any]]) -> Set[str]:
        bar_ids: Set[str] = set()
        for item in bbs_records:
            bar_id = str(item.get("bar_id") or "")
            if bar_id:
                bar_ids.add(bar_id)
            for member_id in item.get("member_bar_ids") or []:
                bar_ids.add(str(member_id))
        return bar_ids

    @staticmethod
    def _excel_bar_ids(excel_validation: dict[str, Any]) -> Set[str]:
        bar_ids: Set[str] = set()
        for row in excel_validation.get("rows") or []:
            if row.get("bar_id"):
                bar_ids.add(str(row["bar_id"]))
        return bar_ids

    @staticmethod
    def _excel_beam_ids(excel_validation: dict[str, Any]) -> Set[str]:
        beam_ids: Set[str] = set()
        for row in excel_validation.get("rows") or []:
            if row.get("beam_id") or row.get("beam_mark"):
                beam_ids.add(str(row.get("beam_id") or row.get("beam_mark")))
        return beam_ids
