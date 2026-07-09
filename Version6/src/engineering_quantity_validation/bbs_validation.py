"""BBS integration validation for recovered bars."""

from __future__ import annotations

from typing import Any, List


class BbsValidator:
    """Inspect BBS export eligibility and presence for recovered bars."""

    def validate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recovery_index = snapshot.get("recovery_index") or {}
        recovered_bar_ids = recovery_index.get("recovered_bar_ids") or []
        records: List[dict[str, Any]] = []

        for bar_id in recovered_bar_ids:
            bar = snapshot.get("bar_by_id", {}).get(bar_id, {})
            bbs = snapshot.get("bbs_by_bar", {}).get(bar_id)
            registry_entry = (recovery_index.get("registry_by_bar") or {}).get(bar_id, {})
            beam_id = str(bar.get("beam_id") or registry_entry.get("beam_id") or "")
            report = self._beam_report(snapshot, beam_id)
            schedule = self._beam_schedule(snapshot, beam_id)
            steel = snapshot.get("steel_weight_by_bar", {}).get(bar_id, {})

            exists_in_report = report is not None
            exists_in_schedule = schedule is not None
            exists_in_bbs = bbs is not None
            eligible = steel.get("weight_kg") is not None or bbs is not None

            absence_reasons = []
            if not exists_in_bbs:
                absence_reasons.append("Recovered bar absent from BBS results")
            if steel.get("status") == "DEFERRED":
                absence_reasons.append("Steel weight deferred prevents BBS fabrication")
            if not exists_in_report:
                absence_reasons.append(f"No engineering report integration for beam {beam_id}")
            if bbs and str(bbs.get("fabrication_state") or "").upper() == "FABRICATION_DEFERRED":
                absence_reasons.append("BBS fabrication deferred")

            records.append(
                {
                    "recovery_id": registry_entry.get("recovery_id"),
                    "bar_id": bar_id,
                    "beam_id": beam_id,
                    "exists_in_engineering_report": exists_in_report,
                    "exists_in_beam_schedule": exists_in_schedule,
                    "exists_in_bbs_export": exists_in_bbs,
                    "bbs_eligible": eligible,
                    "bbs_id": (bbs or {}).get("bbs_id"),
                    "fabrication_state": (bbs or {}).get("fabrication_state"),
                    "determination_state": (bbs or {}).get("determination_state"),
                    "contributes_bbs": exists_in_bbs and str((bbs or {}).get("result_status") or "") != "PRESERVED_DEFERRED",
                    "absence_reasons": absence_reasons,
                    "primary_absence_reason": absence_reasons[0] if absence_reasons else None,
                }
            )

        return {
            "recovered_count": len(records),
            "bbs_contributors": sum(1 for item in records if item["contributes_bbs"]),
            "records": records,
        }

    @staticmethod
    def _beam_report(snapshot: dict[str, Any], beam_id: str) -> dict[str, Any] | None:
        for item in snapshot.get("engineering_reports") or []:
            if str(item.get("beam_id") or item.get("beam_mark") or "") == beam_id:
                return item
        return None

    @staticmethod
    def _beam_schedule(snapshot: dict[str, Any], beam_id: str) -> dict[str, Any] | None:
        for item in snapshot.get("beam_schedules") or []:
            if str(item.get("beam_id") or item.get("beam_mark") or "") == beam_id:
                return item
        return None
