"""Rank every gap CRITICAL / HIGH / MEDIUM / LOW."""

from __future__ import annotations

from typing import Any, Dict, List

PRIORITY_RULES: List[Dict[str, Any]] = [
    {"category": "RULE_GAP", "role": "BOTTOM_MAIN", "priority": "CRITICAL", "reason": "All 18 beams missing bottom main; largest single steel contributor"},
    {"category": "RULE_GAP", "role": "TOP_EXTRA",   "priority": "CRITICAL", "reason": "All 18 beams missing top extra; high steel count"},
    {"category": "RULE_GAP", "role": "BOTTOM_EXTRA","priority": "CRITICAL", "reason": "All 18 beams missing bottom extra"},
    {"category": "RULE_GAP", "role": "STIRRUP",     "priority": "CRITICAL", "reason": "Stirrups absent from all beams; significant steel weight"},
    {"category": "CALCULATION_GAP", "role": None,   "priority": "CRITICAL", "reason": "Phase I pipeline not run; no steel weights in V6"},
    {"category": "RULE_GAP", "role": "NEGATIVE_MOMENT","priority": "HIGH",  "reason": "Negative moment reinforcement at supports missing"},
    {"category": "INTENT_GAP", "role": "TOP_MAIN",  "priority": "HIGH",    "reason": "Top main partial coverage — some beams missing intent"},
    {"category": "DECISION_GAP", "role": None,      "priority": "HIGH",    "reason": "Decision vocabulary missing critical reinforcement categories"},
    {"category": "RULE_GAP", "role": "SIDE_FACE",   "priority": "HIGH",    "reason": "Side face reinforcement for deep beams"},
    {"category": "GEOMETRY_GAP", "role": None,      "priority": "HIGH",    "reason": "Geometry inaccuracy propagates to cut length"},
    {"category": "SPECIFICATION_GAP", "role": None, "priority": "MEDIUM",  "reason": "Spec mismatch propagates to dev length"},
    {"category": "RULE_GAP", "role": "LAP_SPLICE",  "priority": "MEDIUM",  "reason": "Lap lengths affect total bar length"},
    {"category": "RULE_GAP", "role": "CURTAILMENT", "priority": "MEDIUM",  "reason": "Curtailment affects bar count per zone"},
    {"category": "RULE_GAP", "role": "SPACER_BAR",  "priority": "MEDIUM",  "reason": "Spacer bars missing from schedule"},
    {"category": "RULE_GAP", "role": "CHAIR_BAR",   "priority": "MEDIUM",  "reason": "Chair bars missing from schedule"},
    {"category": "REPORTING_GAP", "role": None,     "priority": "LOW",     "reason": "Schedule builder accuracy"},
    {"category": "EXCEL_PRESENTATION_GAP", "role": None, "priority": "LOW","reason": "Format cosmetic — does not affect engineering accuracy"},
    {"category": "PARSER_GAP", "role": None,        "priority": "HIGH",    "reason": "Parser gaps prevent bar detection"},
]

_PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


class PriorityRanker:
    """Assign priority to every gap."""

    def rank(
        self,
        gaps: List[Dict[str, Any]],
        statistics: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        ranked = []
        for gap in gaps:
            category = str(gap.get("gap_category") or "UNKNOWN")
            roles = gap.get("affected_roles") or []
            priority, reason = self._resolve_priority(category, roles)
            steel_impact = float(gap.get("estimated_steel_impact_kg") or 0.0)
            freq = max(len(gap.get("affected_beams") or []), 1)

            gap_out = dict(gap)
            gap_out["priority"] = priority
            gap_out["priority_reason"] = reason
            gap_out["priority_score"] = self._score(priority, steel_impact, freq)
            ranked.append(gap_out)

        ranked.sort(key=lambda g: (_PRIORITY_ORDER.get(g["priority"], 9), -g["priority_score"]))
        for i, g in enumerate(ranked, start=1):
            g["priority_rank"] = i
        return ranked

    @staticmethod
    def _resolve_priority(category: str, roles: List[str]) -> tuple[str, str]:
        for rule in PRIORITY_RULES:
            if rule["category"] == category:
                if rule.get("role") is None:
                    return str(rule["priority"]), str(rule["reason"])
                for r in roles:
                    if rule["role"] in r.upper():
                        return str(rule["priority"]), str(rule["reason"])
        return "MEDIUM", "Default priority — no specific rule matched"

    @staticmethod
    def _score(priority: str, steel_kg: float, frequency: int) -> float:
        base = {"CRITICAL": 1000, "HIGH": 500, "MEDIUM": 100, "LOW": 10}.get(priority, 0)
        return base + steel_kg * 0.5 + frequency * 2
