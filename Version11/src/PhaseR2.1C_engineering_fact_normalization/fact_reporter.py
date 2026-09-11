"""
fact_reporter.py — Generate EngineeringFactReport.md for Phase R.2.1C.
MODEL_VERSION: 7.12.0
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from .fact_models import EngineeringFact


class FactReporter:

    MODEL_VERSION = "7.12.0"
    PHASE_ID      = "R.2.1C"

    def generate(
        self,
        facts_by_beam: Dict[str, List[EngineeringFact]],
        stats: Dict[str, Any],
        validation: Dict[str, Any],
    ) -> str:
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = stats.get("total_facts", 0)
        lines = []

        def h(n, text): lines.append(f"{'#' * n} {text}")
        def p(*args):   lines.extend(args); lines.append("")
        def hr():       lines.append("---"); lines.append("")

        h(1, f"Engineering Fact Normalization Report")
        p(f"**Phase:** {self.PHASE_ID}  |  **MODEL_VERSION:** {self.MODEL_VERSION}  |  **Generated:** {ts}")
        hr()

        h(2, "1. Architecture Summary")
        p(
            "Phase R.2.1C removes premature engineering intent from R.2.1B Semantic Objects.",
            "It produces geometry-independent `EngineeringFact` records — the clean contract",
            "between the annotation parsing pipeline and the future R.3 Geometry Context Engine.",
            "",
            "Three independent engineering concepts are separated:",
            "- **Role** — observable from annotation text (MAIN_BAR, EXTRA_BAR, STIRRUP, ...)",
            "- **Placement** — observable from position zone (TOP, BOTTOM, SIDE, BOTH_FACE)",
            "- **Intent** — `UNKNOWN` until geometry proves otherwise (TOP_MAIN, BOTTOM_EXTRA, ...)",
        )
        hr()

        h(2, "2. Normalization Pipeline")
        p(
            "```",
            "R.2.1B Engineering Semantic Object",
            "  ↓",
            "RoleNormalizer            (map ESO.engineering_role → canonical role)",
            "  ↓",
            "PlacementNormalizer       (map ESO.placement → canonical placement)",
            "  ↓",
            "IntentNormalizer          (remove premature intent → UNKNOWN + generate candidates)",
            "  ↓",
            "SemanticCandidateBuilder  (refine candidates with modifiers + diameter signals)",
            "  ↓",
            "ConfidenceNormalizer      (confidence scoped to role + placement only)",
            "  ↓",
            "EngineeringFact           (immutable dataclass)",
            "  ↓",
            "R.3 Geometry Context Engine (future)",
            "```",
        )
        hr()

        h(2, "3. Statistics")
        p(f"- **Total Facts:** {total}")
        p(f"- **Beams Processed:** {stats.get('beam_count', 0)}")
        p(f"- **Intent UNKNOWN:** {stats.get('intent_unknown_count', 0)} ({stats.get('intent_unknown_pct', 0)}%)")
        p(f"- **Geometry Required:** {stats.get('geometry_required_count', 0)} ({stats.get('geometry_required_pct', 0)}%)")
        p(f"- **Role Coverage:** {stats.get('role_coverage_pct', 0)}%")
        p(f"- **Placement Coverage:** {stats.get('placement_coverage_pct', 0)}%")

        h(3, "3.1 Role Distribution")
        for role, cnt in sorted(stats.get("role_distribution", {}).items(), key=lambda x: -x[1]):
            pct = cnt / total * 100 if total else 0
            lines.append(f"| {role:<22} | {cnt:>5} | {pct:>6.1f}% |")
        lines.append("")

        h(3, "3.2 Placement Distribution")
        for pl, cnt in sorted(stats.get("placement_distribution", {}).items(), key=lambda x: -x[1]):
            pct = cnt / total * 100 if total else 0
            lines.append(f"| {pl:<22} | {cnt:>5} | {pct:>6.1f}% |")
        lines.append("")

        h(3, "3.3 Candidate Distribution")
        for cand, cnt in sorted(stats.get("candidate_distribution", {}).items(), key=lambda x: -x[1]):
            lines.append(f"| {cand:<30} | {cnt:>5} |")
        lines.append("")

        h(3, "3.4 Modifier Distribution")
        mod_dist = stats.get("modifier_distribution", {})
        if mod_dist:
            for mod, cnt in sorted(mod_dist.items(), key=lambda x: -x[1]):
                lines.append(f"| {mod:<30} | {cnt:>5} |")
        else:
            lines.append("_(no modifiers detected)_")
        lines.append("")
        hr()

        h(2, "4. Validation Summary")
        vr    = validation.get("rules", {})
        p(f"**Result:** {validation.get('summary', 'N/A')}")
        for rule_id, rule_result in vr.items():
            status = "✔" if rule_result["passed"] else "✘"
            lines.append(f"- {status} **{rule_id}** — {rule_result['detail']}")
        lines.append("")
        hr()

        h(2, "5. Intent Normalization Strategy")
        p(
            "Engineering intent is UNKNOWN for all non-settled annotations.",
            "Two roles are considered settled (no geometry needed):",
            "- **STIRRUP** — transverse bar, unaffected by span geometry",
            "- **SIDE_FACE** — explicitly annotated with S.F.R. modifier",
            "",
            "All longitudinal bars require geometry to resolve intent:",
            "- A 2-Y16 at TOP could be TOP_MAIN, TOP_EXTRA, CONTINUOUS_TOP, or SUPPORT_TOP.",
            "- Only bar extent (start offset, end offset) and support location can distinguish.",
            "- Reference drawings B1 and B2 demonstrate this clearly:",
            "  - B1: Both 2-Y16 'Top Bar Extra' and 'Top Bar' appear at TOP",
            "  - B2: 2-Y20 'Bottom Bar Extra' at supports vs 2-Y12 'Bottom Bar' mid-span",
        )
        hr()

        h(2, "6. Candidate Generation Strategy")
        p(
            "Candidates are generated from a deterministic table indexed by (role, placement).",
            "Derived from reference drawing engineering rules (B1, B2, B8-B10):",
            "",
            "| Role       | Placement | Candidates                                               |",
            "|------------|-----------|----------------------------------------------------------|",
            "| MAIN_BAR   | TOP       | TOP_MAIN, TOP_EXTRA, CONTINUOUS_TOP, SUPPORT_TOP         |",
            "| MAIN_BAR   | BOTTOM    | BOTTOM_MAIN, BOTTOM_EXTRA, CONTINUOUS_BOTTOM, SUPPORT_BOTTOM |",
            "| EXTRA_BAR  | TOP       | TOP_EXTRA, CURTAILMENT_TOP, SUPPORT_TOP                  |",
            "| EXTRA_BAR  | BOTTOM    | BOTTOM_EXTRA, CURTAILMENT_BOTTOM, SUPPORT_BOTTOM          |",
            "| STIRRUP    | *         | STIRRUP                                                  |",
            "| SIDE_FACE  | *         | SIDE_FACE_REINFORCEMENT                                  |",
            "| SPACER_BAR | *         | SPACER_BAR, CHAIR_BAR                                    |",
            "",
            "Candidates are further refined by semantic signals: modifier type, original R.1 role,",
            "and diameter magnitude (large-diameter bars promoted to MAIN candidates).",
        )
        hr()

        h(2, "7. Remaining Engineering Limitations")
        p(
            "- **Intent unresolved:** R.3 Geometry Context Engine is required to resolve all non-settled intents.",
            "- **Bar extent unknown:** Start/end offsets of bars are not available from annotations alone.",
            "- **Support location unknown:** Which end is near column or wall cannot be inferred from text.",
            "- **Span continuity unknown:** Multi-span continuous bars cannot be detected without geometry.",
            "- **Curtailment point unknown:** Development length and curtailment offset require drawing geometry.",
            "- **Quantity multiplier deferred:** `ONE_EACH_FACE` modifiers do not multiply quantity here.",
            "  The final quantity per face is deferred to the geometry-aware production stage.",
        )
        hr()

        h(2, "8. Model Version and Pipeline")
        p(
            f"- **MODEL_VERSION:** {self.MODEL_VERSION}",
            f"- **PHASE_ID:** {self.PHASE_ID}",
            "- **Input:** `PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json`",
            "- **Output:** `PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json`",
            "- **Next Phase:** R.3 Geometry Context Engine (future)",
            "- **Read-only:** No existing production module modified.",
        )

        return "\n".join(lines)
