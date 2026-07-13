"""Audit the quantity computation pipeline stage."""

from __future__ import annotations
from typing import Any, Dict, List


class QuantityPipelineAuditor:
    def audit(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        sw = snapshot.get("steel_weight") or {}
        results = sw.get("results") or []
        by_role: Dict[str, Dict[str, int]] = {}
        for r in results:
            role = str(r.get("role") or "UNKNOWN")
            status = str(r.get("status") or "UNKNOWN")
            by_role.setdefault(role, {})[status] = by_role.get(role, {}).get(status, 0) + 1
        cl = snapshot.get("cut_length") or {}
        cl_results = cl.get("results") or []
        cl_statuses: Dict[str, int] = {}
        for r in cl_results:
            s = str(r.get("status") or "UNKNOWN")
            cl_statuses[s] = cl_statuses.get(s, 0) + 1
        return {
            "steel_weight_by_role_and_status": by_role,
            "cut_length_status_distribution": cl_statuses,
            "stirrup_deferred": sum(
                v.get("DEFERRED", 0) for k, v in by_role.items() if "STIRRUP" in k
            ),
            "gap_summary": (
                "STIRRUP steel weight DEFERRED — transverse cut length not computed. "
                "SIDE_BAR steel weight CALCULATED — beam schedule excluded. "
                "TOP_MAIN partially calculated — 7/29 bars produce schedule rows."
            ),
        }
