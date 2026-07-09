"""Calculation readiness and result state analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List

from src.engineering_analysis.coverage_collector import CALCULATION_STATES, category_for_role, round_pct


class CalculationStateAnalyzer:
    """Analyse calculation readiness states, deferred reasons, and blocking causes."""

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        bars = snapshot.get("bars") or []
        calc_results = snapshot.get("calculation_results") or []
        readiness_states = self._readiness_states(bars)
        result_states = self._result_states(calc_results)
        combined_states = self._combine_states(readiness_states, result_states, len(bars))
        deferred_analysis = self._deferred_analysis(bars)
        blocked_analysis = self._blocked_analysis(bars, calc_results)
        return {
            "calculation_states": combined_states,
            "readiness_states": readiness_states,
            "result_states": result_states,
            "deferred_analysis": deferred_analysis,
            "blocked_analysis": blocked_analysis,
        }

    def _readiness_states(self, bars: List[dict[str, Any]]) -> dict[str, Any]:
        counts: Counter[str] = Counter()
        beams: Dict[str, set[str]] = defaultdict(set)
        bar_types: Dict[str, set[str]] = defaultdict(set)
        for bar in bars:
            readiness = bar.get("calculation_readiness") or {}
            state = str(readiness.get("calculation_state") or "UNKNOWN").upper()
            if state not in CALCULATION_STATES:
                state = "UNKNOWN"
            counts[state] += 1
            beam_id = str(bar.get("beam_id"))
            beams[state].add(beam_id)
            bar_types[state].add(category_for_role(bar.get("role")))
        total = sum(counts.values()) or 1
        return self._present_state_counts(counts, beams, bar_types, total)

    def _result_states(self, calc_results: List[dict[str, Any]]) -> dict[str, Any]:
        counts: Counter[str] = Counter()
        beams: Dict[str, set[str]] = defaultdict(set)
        bar_types: Dict[str, set[str]] = defaultdict(set)
        for result in calc_results:
            state = str(result.get("calculation_state") or "UNKNOWN").upper()
            if state == "CALCULATED":
                state = "COMPLETED"
            if state not in CALCULATION_STATES:
                state = "UNKNOWN"
            counts[state] += 1
            beam_id = str(result.get("input_beam_id") or "")
            if beam_id:
                beams[state].add(beam_id)
        total = sum(counts.values()) or 1
        return self._present_state_counts(counts, beams, bar_types, total)

    def _combine_states(
        self,
        readiness_states: dict[str, Any],
        result_states: dict[str, Any],
        bar_count: int,
    ) -> dict[str, Any]:
        combined_counts: Counter[str] = Counter()
        for item in readiness_states.get("states", []):
            combined_counts[item["state"]] += item["count"]
        rows: List[dict[str, Any]] = []
        total = bar_count or sum(combined_counts.values()) or 1
        for state in CALCULATION_STATES:
            count = combined_counts.get(state, 0)
            rows.append(
                {
                    "state": state,
                    "count": count,
                    "percentage": round_pct(count, total),
                    "affected_beams": sorted(
                        {
                            beam
                            for item in readiness_states.get("states", [])
                            if item["state"] == state
                            for beam in item.get("affected_beams", [])
                        }
                    ),
                    "affected_bar_types": sorted(
                        {
                            bar_type
                            for item in readiness_states.get("states", [])
                            if item["state"] == state
                            for bar_type in item.get("affected_bar_types", [])
                        }
                    ),
                }
            )
        return {
            "total_bars": bar_count,
            "total_results": result_states.get("total", 0),
            "states": rows,
        }

    def _deferred_analysis(self, bars: List[dict[str, Any]]) -> dict[str, Any]:
        reasons: Counter[str] = Counter()
        examples: Dict[str, List[dict[str, Any]]] = defaultdict(list)
        for bar in bars:
            readiness = bar.get("calculation_readiness") or {}
            state = str(readiness.get("calculation_state") or "").upper()
            if state != "DEFERRED":
                continue
            reason = self._normalize_reason(readiness.get("defer_reason"))
            reasons[reason] += 1
            if len(examples[reason]) < 5:
                examples[reason].append(
                    {
                        "bar_id": bar.get("bar_id"),
                        "beam_id": bar.get("beam_id"),
                        "role": bar.get("role"),
                        "diameter_mm": bar.get("diameter_mm"),
                    }
                )
        ranked = [
            {"reason": reason, "count": count, "examples": examples.get(reason, [])}
            for reason, count in reasons.most_common()
        ]
        return {"total_deferred": sum(reasons.values()), "reasons": ranked}

    def _blocked_analysis(
        self,
        bars: List[dict[str, Any]],
        calc_results: List[dict[str, Any]],
    ) -> dict[str, Any]:
        reasons: Counter[str] = Counter()
        for bar in bars:
            readiness = bar.get("calculation_readiness") or {}
            if str(readiness.get("calculation_state") or "").upper() != "BLOCKED":
                continue
            reasons[self._normalize_reason(readiness.get("defer_reason") or readiness.get("block_reason"))] += 1
        for result in calc_results:
            if str(result.get("calculation_state") or "").upper() != "BLOCKED":
                continue
            metadata = result.get("result_metadata") or {}
            reasons[
                self._normalize_reason(
                    metadata.get("defer_reason")
                    or metadata.get("block_reason")
                    or result.get("calculation_notes")
                )
            ] += 1
        ranked = [{"reason": reason, "count": count} for reason, count in reasons.most_common(20)]
        return {"total_blocked": sum(reasons.values()), "top_blocking_reasons": ranked}

    @staticmethod
    def _present_state_counts(
        counts: Counter[str],
        beams: Dict[str, set[str]],
        bar_types: Dict[str, set[str]],
        total: int,
    ) -> dict[str, Any]:
        rows = []
        for state in CALCULATION_STATES:
            count = counts.get(state, 0)
            rows.append(
                {
                    "state": state,
                    "count": count,
                    "percentage": round_pct(count, total),
                    "affected_beams": sorted(beams.get(state, set())),
                    "affected_bar_types": sorted(bar_types.get(state, set())),
                }
            )
        return {"total": total, "states": rows}

    @staticmethod
    def _normalize_reason(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return "Unknown engineering rule"
        lowered = text.lower()
        mapping = {
            "partial calculation context": "Missing specification",
            "missing geometry": "Missing geometry",
            "missing support": "Missing support",
            "missing cover": "Missing cover",
            "missing bar type": "Missing bar type",
            "development length": "Missing development length",
            "missing specification": "Missing specification",
            "unknown callout": "Unknown callout",
            "unknown diameter": "Unknown diameter",
        }
        for key, label in mapping.items():
            if key in lowered:
                return label
        return text.rstrip(".")
