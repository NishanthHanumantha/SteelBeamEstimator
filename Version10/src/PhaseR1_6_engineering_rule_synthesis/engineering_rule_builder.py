"""
Build EngineeringRule objects from patterns + issues.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from engineering_rule_model import EngineeringRule
from expected_gain_engine import ExpectedGainEngine
from rule_family_classifier import RuleFamilyClassifier
from rule_gap_detector import RuleGapDetector
from rule_synthesis_engine import template_for

MODEL_VERSION = "8.8.0"


class EngineeringRuleBuilder:
    def __init__(self):
        self._clf = RuleFamilyClassifier()
        self._gap = RuleGapDetector()
        self._gain = ExpectedGainEngine()

    def build_library(
        self,
        issues: List[Dict[str, Any]],
        pattern_analysis: Dict[str, Any],
    ) -> List[EngineeringRule]:
        groups = pattern_analysis.get("groups") or {}
        issue_by_id = {i["issue_id"]: i for i in issues}
        rules: List[EngineeringRule] = []
        idx = 1
        # Stable order: by total finding count desc then family name
        ordered_keys = []
        for p in pattern_analysis.get("patterns") or []:
            ordered_keys.append(p["pattern_id"])

        for key in ordered_keys:
            issue_ids = groups.get(key) or []
            cluster = [issue_by_id[i] for i in issue_ids if i in issue_by_id]
            if not cluster:
                continue
            family = key.split("::")[0]
            rules.append(self._build_one(idx, family, key, cluster))
            idx += 1
        return rules

    def _build_one(
        self,
        idx: int,
        family: str,
        pattern_id: str,
        issues: List[Dict[str, Any]],
    ) -> EngineeringRule:
        tpl = template_for(family)
        primary = max(issues, key=lambda i: (
            float(i.get("engineering_impact") or 0),
            int(i.get("frequency") or 0),
        ))
        gap = self._gap.detect(family, primary)
        gains = self._gain.for_pattern(issues)

        beams: List[str] = []
        roles: List[str] = []
        dias: List[int] = []
        evidence: List[str] = []
        findings: List[str] = []
        for i in issues:
            beams.extend(i.get("affected_beams") or [])
            roles.extend(i.get("affected_roles") or [])
            dias.extend(i.get("affected_diameters") or [])
            evidence.extend(i.get("supporting_evidence") or [])
            findings.extend(i.get("finding_ids") or [])

        phases = [i.get("originating_phase") or i.get("recommended_phase") or "" for i in issues]
        # single implementation phase from template (authoritative for correction target)
        impl_phase = str(tpl["impl_phase"])
        # originating_phase: majority from issues, else template
        from collections import Counter
        phase_votes = Counter(p for p in phases if p)
        originating_phase = phase_votes.most_common(1)[0][0] if phase_votes else impl_phase

        effort = "H" if gains["expected_accuracy_gain"] >= 8 or family in (
            "Stirrup Interpretation", "Steel Aggregation", "Role Resolution"
        ) else ("M" if gains["expected_accuracy_gain"] >= 3 else "L")
        risk = "High" if family in ("Steel Aggregation", "Stirrup Interpretation") else (
            "Medium" if effort in ("H", "M") else "Low"
        )

        flags = []
        if not issues:
            flags.append("NO_ISSUES")
        if gap["status"] == "Missing":
            flags.append("RULE_MISSING_IN_PRODUCTION")

        return EngineeringRule(
            rule_id=f"RULE-{idx:03d}",
            rule_name=str(tpl["name"]),
            rule_family=family,
            rule_category=primary.get("category") or family,
            originating_issue=primary.get("issue_id") or "",
            originating_phase=originating_phase,
            engineering_domain=str(tpl["domain"]),
            engineering_intent=str(tpl["intent"]),
            rule_description=self._description(family, issues, tpl),
            engineering_rationale=primary.get("root_cause") or str(tpl["intent"]),
            trigger_conditions=tuple(tpl["triggers"]),  # type: ignore
            required_inputs=tuple(tpl["inputs"]),  # type: ignore
            decision_logic=tuple(tpl["logic"]),  # type: ignore
            expected_outputs=tuple(tpl["outputs"]),  # type: ignore
            validation_criteria=tuple(tpl["validation"]),  # type: ignore
            priority=0,  # filled later
            confidence=float(gains["confidence"]),
            expected_accuracy_gain=float(gains["expected_accuracy_gain"]),
            estimated_steel_gain_kg=float(gains["estimated_steel_gain_kg"]),
            affected_roles=tuple(sorted(set(roles))),
            affected_diameters=tuple(sorted(set(int(d) for d in dias))),
            affected_beams=tuple(sorted(set(beams))),
            dependencies=tuple(),  # filled by dependency engine
            conflicting_rules=tuple(),
            implementation_phase=impl_phase,
            status=str(gap["status"]),
            source_phase="R.1.5",
            supporting_evidence=tuple(sorted(set(evidence))[:30]),
            validation_flags=tuple(flags),
            originating_issues=tuple(i.get("issue_id") for i in issues),
            finding_ids=tuple(sorted(set(findings))),
            gap_type=str(gap["gap_type"]),
            pattern_id=pattern_id,
            estimated_effort=effort,
            engineering_risk=risk,
        )

    @staticmethod
    def _description(family: str, issues: List[Dict[str, Any]], tpl: Dict[str, object]) -> str:
        n_findings = sum(int(i.get("frequency") or 0) for i in issues)
        n_issues = len(issues)
        return (
            f"{tpl['name']}: synthesized from {n_issues} engineering issue(s) "
            f"covering {n_findings} benchmark finding(s). "
            f"Deterministic decision logic applies whenever trigger conditions are met."
        )
