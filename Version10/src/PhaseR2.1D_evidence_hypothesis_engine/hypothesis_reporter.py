"""
hypothesis_reporter.py — Generate EngineeringHypothesisReport.md.
MODEL_VERSION: 7.12.1
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from .evidence_models import HypothesisEnrichedFact


class HypothesisReporter:

    MODEL_VERSION = "7.12.1"
    PHASE_ID      = "R.2.1D"

    def generate(
        self,
        facts_by_beam: Dict[str, List[HypothesisEnrichedFact]],
        stats:         Dict[str, Any],
        validation:    Dict[str, Any],
    ) -> str:
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = stats.get("total_facts", 0)
        lines = []

        def h(n, text): lines.append(f"{'#' * n} {text}")
        def p(*args):   lines.extend(args); lines.append("")
        def hr():       lines.append("---"); lines.append("")

        h(1, "Engineering Hypothesis Report")
        p(
            f"**Phase:** {self.PHASE_ID}  |  "
            f"**MODEL_VERSION:** {self.MODEL_VERSION}  |  "
            f"**Generated:** {ts}"
        )
        hr()

        h(2, "1. Architecture Summary")
        p(
            "Phase R.2.1D upgrades each EngineeringFact from R.2.1C with:",
            "",
            "- **ObservableEvidence** — structured capture of all drawing-observable facts.",
            "  Contains zero engineering inference or assumption.",
            "- **IntentHypotheses** — replaces unordered `intent_candidates` with a",
            "  deterministically ranked list of IntentHypothesis objects.",
            "",
            "Three strict separations are maintained:",
            "```",
            "Observable  → Role, Placement, Diameter, Modifiers, Quantity, Zone",
            "Hypothesis  → TOP_MAIN, TOP_EXTRA, CONTINUOUS_TOP, ... (ranked, not resolved)",
            "Resolution  → Belongs ONLY to Phase R.3 Geometry Context Engine",
            "```",
        )
        hr()

        h(2, "2. Hypothesis Pipeline")
        p(
            "```",
            "R.2.1C EngineeringFact",
            "  ↓",
            "EvidenceBuilder       (build ObservableEvidence — zero inference)",
            "  ↓",
            "HypothesisRanker",
            "  Stage 1: Base ranking from (role, placement) → BASE_RANKINGS table",
            "  Stage 2: Apply deterministic REORDER_RULES (RR-1 through RR-8)",
            "  ↓",
            "HypothesisEnrichedFact  (upgraded fact with evidence + ranked hypotheses)",
            "  ↓",
            "R.3 Geometry Context Engine (future)",
            "```",
        )
        hr()

        h(2, "3. Statistics")
        p(f"- **Total Facts:** {total}")
        p(f"- **Total Hypotheses:** {stats.get('total_hypotheses', 0)}")
        p(f"- **Avg Hypotheses/Fact:** {stats.get('avg_hypotheses_per_fact', 0)}")
        p(f"- **Beams:** {stats.get('beam_count', 0)}")

        h(3, "3.1 Hypothesis Frequency")
        lines.append("| Intent | Appearances |")
        lines.append("|--------|-------------|")
        for intent, cnt in sorted(
            stats.get("hypothesis_frequency", {}).items(), key=lambda x: -x[1]
        ):
            lines.append(f"| {intent:<30} | {cnt:>5} |")
        lines.append("")

        h(3, "3.2 Most Common Priority per Intent")
        lines.append("| Intent | Most Common Priority |")
        lines.append("|--------|---------------------|")
        for intent, prio in sorted(stats.get("top_priority_per_intent", {}).items()):
            lines.append(f"| {intent:<30} | {prio:>5} |")
        lines.append("")

        h(3, "3.3 Evidence Zone Distribution")
        for zone, cnt in sorted(
            stats.get("evidence_zone_distribution", {}).items(), key=lambda x: -x[1]
        ):
            pct = cnt / total * 100 if total else 0
            lines.append(f"| {zone:<20} | {cnt:>5} | {pct:>5.1f}% |")
        lines.append("")

        h(3, "3.4 Reorder Rules Applied")
        rr = stats.get("reorder_rule_fire_counts", {})
        if rr:
            for rule_id, cnt in sorted(rr.items(), key=lambda x: -x[1]):
                lines.append(f"| {rule_id} | {cnt:>5} |")
        else:
            lines.append("_(no reorder rules applied — base ranking used for all facts)_")
        lines.append("")
        hr()

        h(2, "4. Validation Summary")
        p(f"**Result:** {validation.get('summary', 'N/A')}")
        for rule_id, result in validation.get("rules", {}).items():
            icon = "✔" if result["passed"] else "✘"
            lines.append(f"- {icon} **{rule_id}** — {result['detail']}")
        lines.append("")
        hr()

        h(2, "5. Ranking Rules")
        p(
            "### Base Ranking Table",
            "",
            "| Role | Placement | Default Priority-1 Intent |",
            "|------|-----------|--------------------------|",
            "| MAIN_BAR | TOP | TOP_MAIN |",
            "| MAIN_BAR | BOTTOM | BOTTOM_MAIN |",
            "| EXTRA_BAR | TOP | TOP_EXTRA |",
            "| EXTRA_BAR | BOTTOM | BOTTOM_EXTRA |",
            "| STIRRUP | * | STIRRUP |",
            "| SIDE_FACE | * | SIDE_FACE_REINFORCEMENT |",
            "| SPACER_BAR | * | SPACER_BAR |",
            "",
            "### Deterministic Reorder Rules",
            "",
            "| Rule | Trigger | Action |",
            "|------|---------|--------|",
            "| RR-1 | R.1 original role = TOP_EXTRA | Promote TOP_EXTRA to priority 1 |",
            "| RR-2 | R.1 original role = BOTTOM_EXTRA | Promote BOTTOM_EXTRA to priority 1 |",
            "| RR-3 | R.1 original role = TOP_MAIN | Confirm TOP_MAIN at priority 1 |",
            "| RR-4 | R.1 original role = BOTTOM_MAIN | Promote BOTTOM_MAIN to priority 1 |",
            "| RR-5 | Modifier = U_BAR | Promote SIDE_FACE_REINFORCEMENT |",
            "| RR-6 | diameter >= 20mm | Promote contextual MAIN candidate |",
            "| RR-7 | semantic_flag = CONTINUOUS | Promote CONTINUOUS candidate |",
            "| RR-8 | semantic_flag = SUPPORT | Promote SUPPORT candidate |",
        )
        hr()

        h(2, "6. Engineering Philosophy")
        p(
            "Priority is **deterministic ordering**, not probability or confidence.",
            "",
            "Example: `2-Y20` at TOP",
            "```json",
            '{"intent": "TOP_MAIN",    "priority": 1, "reason": "Promoted from R.1: TOP_MAIN + diameter >=20mm"}',
            '{"intent": "TOP_EXTRA",   "priority": 2, "reason": "Possible support reinforcement"}',
            '{"intent": "CONTINUOUS_TOP","priority": 3, "reason": "Possible continuous reinforcement"}',
            '{"intent": "SUPPORT_TOP", "priority": 4, "reason": "Requires support geometry"}',
            "```",
            "",
            "All intent resolution deferred to **Phase R.3 — Geometry Context Engine**.",
        )
        hr()

        h(2, "7. Remaining Engineering Limitations")
        p(
            "- **Intent unresolved:** R.3 Geometry Context Engine required for all non-settled facts.",
            "- **Bar extent unknown:** Hypotheses cannot distinguish full-span vs short bars.",
            "- **Support location unknown:** SUPPORT vs MAIN distinction unavailable.",
            "- **Span continuity unknown:** CONTINUOUS determination requires member topology.",
            "- **Curtailment point unknown:** Development length and offset require geometry.",
            "- **Priority is not a guarantee:** Priority-1 hypothesis may be incorrect for any given bar.",
            "  R.3 must validate against actual geometry.",
        )
        hr()

        h(2, "8. Model Version and Pipeline")
        p(
            f"- **MODEL_VERSION:** {self.MODEL_VERSION}",
            f"- **PHASE_ID:** {self.PHASE_ID}",
            "- **Input:** `PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json`",
            "- **Output:** `PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json`",
            "- **Next Phase:** R.3 Geometry Context Engine (future)",
            "- **Read-only:** No existing production module modified.",
        )

        return "\n".join(lines)
