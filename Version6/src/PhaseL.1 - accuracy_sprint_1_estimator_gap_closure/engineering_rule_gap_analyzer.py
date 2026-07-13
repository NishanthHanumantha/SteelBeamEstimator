"""Identify missing engineering rules from gap evidence."""

from __future__ import annotations

from typing import Any, Dict, List


RULE_CATALOG: List[Dict[str, Any]] = [
    {
        "rule_id": "RULE::L.1::001",
        "rule_name": "Bottom Main Reinforcement",
        "rule_description": "Detect, reconstruct intent and calculate bottom main (positive moment) "
                             "reinforcement for all beams.",
        "rule_category": "BOTTOM_MAIN",
        "engineering_domains": ["Positive Moment Reinforcement", "Bar Detection", "Intent Reconstruction"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "CRITICAL",
        "estimated_impact": "Very High",
        "estimated_steel_impact_percent": 35.0,
        "affected_beams": "ALL",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::002",
        "rule_name": "Top Extra (Negative Moment Extra) Reinforcement",
        "rule_description": "Detect and calculate top extra bars provided at supports for negative "
                             "moment redistribution.",
        "rule_category": "TOP_EXTRA",
        "engineering_domains": ["Negative Moment Reinforcement", "Support Reinforcement"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "CRITICAL",
        "estimated_impact": "High",
        "estimated_steel_impact_percent": 15.0,
        "affected_beams": "ALL",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::003",
        "rule_name": "Bottom Extra (Positive Moment Extra) Reinforcement",
        "rule_description": "Detect and calculate bottom extra bars at spans where additional "
                             "positive moment capacity is required.",
        "rule_category": "BOTTOM_EXTRA",
        "engineering_domains": ["Positive Moment Reinforcement", "Extra Bar Detailing"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "CRITICAL",
        "estimated_impact": "High",
        "estimated_steel_impact_percent": 12.0,
        "affected_beams": "ALL",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::004",
        "rule_name": "Stirrup / Shear Link Reinforcement",
        "rule_description": "Detect stirrup diameter, spacing and extent from drawing. "
                             "Calculate cut length including bends, hooks and clear span. "
                             "Generate schedule rows for all beams.",
        "rule_category": "STIRRUP",
        "engineering_domains": ["Shear Reinforcement", "Link Detailing", "Stirrup Cut Length"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "CRITICAL",
        "estimated_impact": "High",
        "estimated_steel_impact_percent": 20.0,
        "affected_beams": "ALL",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::005",
        "rule_name": "Development Length Rule — All Diameters",
        "rule_description": "Apply correct development length from General Note table for each "
                             "diameter/concrete grade combination. Currently implemented in Phase I.3 "
                             "but Version6 pipeline not fully executed.",
        "rule_category": "DEVELOPMENT_LENGTH",
        "engineering_domains": ["Development Length", "Anchorage", "Bar Extension"],
        "gap_category": "CALCULATION_GAP",
        "status": "PARTIAL",
        "priority": "HIGH",
        "estimated_impact": "High",
        "estimated_steel_impact_percent": 10.0,
        "affected_beams": "ALL",
        "future_phase": "Phase L.2 — run full pipeline",
    },
    {
        "rule_id": "RULE::L.1::006",
        "rule_name": "Hook Length Rule",
        "rule_description": "Calculate hook length for bars requiring hooks at supports and ends. "
                             "Affects cut length and total steel weight.",
        "rule_category": "HOOK",
        "engineering_domains": ["Hook Length", "Bar End Detailing"],
        "gap_category": "CALCULATION_GAP",
        "status": "PARTIAL",
        "priority": "HIGH",
        "estimated_impact": "Medium",
        "estimated_steel_impact_percent": 5.0,
        "affected_beams": "ALL",
        "future_phase": "Phase L.2 — run full pipeline",
    },
    {
        "rule_id": "RULE::L.1::007",
        "rule_name": "Lap Splice Rule",
        "rule_description": "Calculate lap splice length for bars that need splicing. "
                             "Affects total bar length and steel weight.",
        "rule_category": "LAP_SPLICE",
        "engineering_domains": ["Lap Splice", "Bar Continuity"],
        "gap_category": "RULE_GAP",
        "status": "PARTIAL",
        "priority": "MEDIUM",
        "estimated_impact": "Medium",
        "estimated_steel_impact_percent": 5.0,
        "affected_beams": "SOME",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::008",
        "rule_name": "Curtailment Rule",
        "rule_description": "Determine where top and bottom bars are curtailed based on moment "
                             "envelope. Affects number of bars per zone.",
        "rule_category": "CURTAILMENT",
        "engineering_domains": ["Bar Curtailment", "Moment Distribution"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "MEDIUM",
        "estimated_impact": "Medium",
        "estimated_steel_impact_percent": 3.0,
        "affected_beams": "SOME",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::009",
        "rule_name": "Side Face Reinforcement Rule",
        "rule_description": "For deep beams (depth > 750mm), add side face bars at specified "
                             "spacing. Detect from drawing or apply minimum reinforcement rule.",
        "rule_category": "SIDE_FACE",
        "engineering_domains": ["Side Face Reinforcement", "Minimum Reinforcement"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "MEDIUM",
        "estimated_impact": "Medium",
        "estimated_steel_impact_percent": 3.0,
        "affected_beams": "SOME",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::010",
        "rule_name": "Spacer Bar Rule",
        "rule_description": "Apply spacer bar (25mm @ 1m) wherever 2+ bars are alongside. "
                             "Specification reads: 25mm dia, 1m spacing. Currently in specs but "
                             "not generating schedule rows.",
        "rule_category": "SPACER_BAR",
        "engineering_domains": ["Bar Spacer", "Detailing Rules"],
        "gap_category": "RULE_GAP",
        "status": "PARTIAL",
        "priority": "MEDIUM",
        "estimated_impact": "Low",
        "estimated_steel_impact_percent": 1.0,
        "affected_beams": "ALL",
        "future_phase": "Phase L.2",
    },
    {
        "rule_id": "RULE::L.1::011",
        "rule_name": "Minimum / Maximum Reinforcement Rule",
        "rule_description": "Verify minimum steel area (IS 456) and flag beams where estimator "
                             "provides reinforcement below or above code minimum/maximum.",
        "rule_category": "MIN_MAX_REINFORCEMENT",
        "engineering_domains": ["Minimum Reinforcement", "Code Compliance"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "LOW",
        "estimated_impact": "Low",
        "estimated_steel_impact_percent": 1.0,
        "affected_beams": "SOME",
        "future_phase": "Phase L.3",
    },
    {
        "rule_id": "RULE::L.1::012",
        "rule_name": "Negative Moment Reinforcement (Continuous Beam)",
        "rule_description": "Calculate negative moment reinforcement at interior supports for "
                             "continuous beams. Requires framing continuity analysis.",
        "rule_category": "NEGATIVE_MOMENT",
        "engineering_domains": ["Negative Moment", "Continuous Beam", "Support Reinforcement"],
        "gap_category": "RULE_GAP",
        "status": "MISSING",
        "priority": "HIGH",
        "estimated_impact": "High",
        "estimated_steel_impact_percent": 8.0,
        "affected_beams": "SOME",
        "future_phase": "Phase L.2",
    },
]


class EngineeringRuleGapAnalyzer:
    """Identify and catalogue missing engineering rules."""

    def analyze(
        self,
        gaps: List[Dict[str, Any]],
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        # Enrich catalog with gap evidence
        gap_categories = {g.get("gap_category") for g in gaps}
        for rule in RULE_CATALOG:
            rule["has_gap_evidence"] = rule.get("gap_category") in gap_categories

        missing = [r for r in RULE_CATALOG if r.get("status") == "MISSING"]
        partial = [r for r in RULE_CATALOG if r.get("status") == "PARTIAL"]
        total_steel_impact = sum(r.get("estimated_steel_impact_percent", 0.0) for r in missing + partial)

        return {
            "rule_count": len(RULE_CATALOG),
            "missing_rules": len(missing),
            "partial_rules": len(partial),
            "estimated_total_steel_impact_percent": round(min(total_steel_impact, 100.0), 1),
            "rules": RULE_CATALOG,
        }
