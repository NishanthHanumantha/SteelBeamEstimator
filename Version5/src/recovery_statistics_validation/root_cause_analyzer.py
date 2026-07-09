"""Root cause analysis for statistics mismatches."""

from __future__ import annotations

from typing import Any, Dict, List


class RootCauseAnalyzer:
    """Identify evidence-based root causes for metric mismatches."""

    def analyze(
        self,
        reconciliation: dict[str, Any],
        snapshot: dict[str, Any],
        authoritative: dict[str, Any],
    ) -> List[dict[str, Any]]:
        causes: List[dict[str, Any]] = []
        for row in reconciliation.get("top_mismatches") or []:
            causes.append(self._cause_from_row(row))

        expansion_stats = snapshot.get("expansion_statistics") or {}
        if self._semantic_coverage_confusion(expansion_stats, authoritative):
            causes.append(
                {
                    "issue": "Coverage semantic ambiguity",
                    "source_artifact": "expansion_statistics.json",
                    "incorrect_consumer": "Console interpretation",
                    "root_cause": "WRONG_BASELINE",
                    "evidence": (
                        f"recovered={expansion_stats.get('recovered')} is cumulative registry count, "
                        f"coverage_before/after bars={expansion_stats.get('coverage_before_bars')}→"
                        f"{expansion_stats.get('coverage_after_bars')} are production totals; "
                        "adding recovered to coverage_before is invalid"
                    ),
                    "resolution": (
                        "Use authoritative total_production_bars and normalization_coverage_percent "
                        "from production_snapshot.json"
                    ),
                }
            )

        j1_after = (snapshot.get("recovery_summary") or {}).get("steel_coverage_after_percent")
        total_cov = authoritative.get("normalization_coverage_percent")
        if j1_after is not None and j1_after != total_cov:
            causes.append(
                {
                    "issue": "Scoped coverage metric divergence",
                    "source_artifact": "recovery_summary.json",
                    "incorrect_consumer": "Cross-phase comparison without scope",
                    "root_cause": "INCORRECT_AGGREGATION",
                    "evidence": (
                        f"J.1 scoped coverage after={j1_after}% differs from total normalization "
                        f"coverage={total_cov}% because J.1 reports native+J.1 only"
                    ),
                    "resolution": "Label J.1 coverage as post_j1_coverage_percent; use total normalization coverage for all-recovery state",
                }
            )
        return causes

    @staticmethod
    def _cause_from_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "issue": row.get("metric"),
            "source_artifact": row.get("authoritative_source"),
            "incorrect_consumer": ", ".join(row.get("mismatched_consumers") or []),
            "root_cause": RootCauseAnalyzer._classify_root_cause(row),
            "evidence": row.get("mismatch_reason"),
            "resolution": row.get("resolution"),
        }

    @staticmethod
    def _classify_root_cause(row: dict[str, Any]) -> str:
        metric = str(row.get("metric") or "")
        if "Coverage" in metric:
            return "WRONG_BASELINE"
        if "Registry" in metric or "Recovered" in metric:
            return "INCORRECT_AGGREGATION"
        return "STALE_CACHE"

    @staticmethod
    def _semantic_coverage_confusion(expansion_stats: dict[str, Any], authoritative: dict[str, Any]) -> bool:
        before = expansion_stats.get("coverage_before_bars")
        after = expansion_stats.get("coverage_after_bars")
        recovered = expansion_stats.get("recovered", 0)
        return (
            before == after == authoritative.get("total_production_bars")
            and recovered > 0
        )
