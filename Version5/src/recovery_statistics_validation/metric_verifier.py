"""Verify consistency rules against authoritative metrics."""

from __future__ import annotations

from typing import Any, Dict, List


class MetricVerifier:
    """Apply deterministic consistency rules."""

    def verify(self, snapshot: dict[str, Any], authoritative: dict[str, Any]) -> List[dict[str, Any]]:
        recovery_stats = snapshot.get("recovery_statistics") or {}
        expansion_stats = snapshot.get("expansion_statistics") or {}
        checks = [
            self._check(
                "Rule 1 Recovered Objects Registry Delta",
                authoritative["j1_registry_count"] == recovery_stats.get("recovered_objects"),
            ),
            self._check(
                "Rule 2 J.1 Recovered Bars Match Statistics",
                authoritative["j1_recovered_bars"] == recovery_stats.get("recovered_normalized_bars"),
            ),
            self._check(
                "Rule 2 J.2 Recovered Bars Match Statistics",
                authoritative["j2_recovered_bars"] == expansion_stats.get("recovered"),
            ),
            self._check(
                "Rule 6 Total Coverage Matches Production",
                expansion_stats.get("coverage_after_bars") == authoritative["total_production_bars"],
            ),
            self._check(
                "Rule 6 Total Coverage Percent Matches Production",
                expansion_stats.get("coverage_after_percent") == authoritative["normalization_coverage_percent"],
            ),
            self._check(
                "Rule 6 Expansion Summary Matches Statistics Coverage",
                (snapshot.get("expansion_summary") or {}).get("coverage_after_percent")
                == expansion_stats.get("coverage_after_percent"),
            ),
            self._check(
                "Rule 6 Expansion Summary Matches Statistics Bars",
                (snapshot.get("expansion_summary") or {}).get("coverage_after_bars")
                == expansion_stats.get("coverage_after_bars"),
            ),
            self._check(
                "Native Plus J1 Plus J2 Equals Total",
                authoritative["internal_consistency"]["native_plus_j1_plus_j2_equals_total"],
            ),
            self._check(
                "J.1 Registry Matches Production Bars",
                authoritative["internal_consistency"]["j1_registry_matches_production"],
            ),
            self._check(
                "J.2 Registry Matches Production Bars",
                authoritative["internal_consistency"]["j2_registry_matches_production"],
            ),
            self._check(
                "Recovered Count Is Registry Total Not Coverage Delta",
                expansion_stats.get("recovered") == authoritative["j2_registry_count"]
                and expansion_stats.get("coverage_after_bars") == authoritative["total_production_bars"],
            ),
        ]
        return checks

    @staticmethod
    def _check(name: str, passed: bool) -> dict[str, Any]:
        return {"name": name, "status": "PASS" if passed else "FAIL"}
