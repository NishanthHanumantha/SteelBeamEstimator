"""
Build immutable EngineeringIssue objects from clustered findings.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple

from confidence_engine import ConfidenceEngine
from engineering_impact_engine import EngineeringImpactEngine
from engineering_issue_model import EngineeringIssue, RawFinding
from phase_attribution_engine import PhaseAttributionEngine
from priority_engine import PriorityEngine
from recommendation_engine import RecommendationEngine
from severity_engine import SeverityEngine

MODEL_VERSION = "8.7.0"


class EngineeringIssueBuilder:
    def __init__(self):
        self.phase_engine = PhaseAttributionEngine()
        self.impact_engine = EngineeringImpactEngine()
        self.severity_engine = SeverityEngine()
        self.confidence_engine = ConfidenceEngine()
        self.priority_engine = PriorityEngine()
        self.recommendation_engine = RecommendationEngine()

    def build_all(
        self,
        clusters: Dict[Tuple[str, str], List[RawFinding]],
        official_total_kg: float,
        steel_gap_kg: float,
        kpi_loss: float,
    ) -> List[EngineeringIssue]:
        total_findings = sum(len(v) for v in clusters.values())
        issues: List[EngineeringIssue] = []
        for idx, ((category, subcategory), findings) in enumerate(clusters.items(), start=1):
            issues.append(
                self._build_one(
                    idx, category, subcategory, findings,
                    official_total_kg, steel_gap_kg, total_findings, kpi_loss,
                )
            )
        # normalize steel impacts so sum does not wildly exceed gap
        issues = self._normalize_steel(issues, abs(steel_gap_kg))
        return issues

    def _build_one(
        self,
        idx: int,
        category: str,
        subcategory: str,
        findings: List[RawFinding],
        official_total_kg: float,
        steel_gap_kg: float,
        total_findings: int,
        kpi_loss: float,
    ) -> EngineeringIssue:
        phase = self.phase_engine.attribute(category, findings)
        impact = self.impact_engine.estimate(
            category, findings, official_total_kg, steel_gap_kg, total_findings, kpi_loss,
        )
        severity = self.severity_engine.severity(
            category, findings, impact["steel_impact_kg"], impact["engineering_impact"],
        )
        # phase certainty = vote dominance
        phase_votes = Counter(
            self.phase_engine.default_phase(category) if not f.originating_phase else f.originating_phase
            for f in findings
        )
        top = phase_votes.most_common(1)[0][1] if phase_votes else 1
        phase_certainty = top / max(1, len(findings))
        category_consistency = 1.0  # clustered by category already
        confidence = self.confidence_engine.score(findings, phase_certainty, category_consistency)
        priority = self.priority_engine.priority(severity, impact["engineering_impact"], len(findings))
        hints = tuple(sorted({f.suggested_fix for f in findings if f.suggested_fix}))
        rec = self.recommendation_engine.recommend(
            category, subcategory, phase,
            impact["production_accuracy_loss"], priority, confidence, hints,
        )

        beams = tuple(sorted({
            f.entity for f in findings
            if f.entity and f.entity not in ("*", "PROJECT") and not str(f.entity).startswith("DIA_")
        }))
        entities = tuple(sorted({f.entity for f in findings if f.entity}))
        roles = tuple(sorted({f.role for f in findings if f.role}))
        dias = tuple(sorted({f.diameter for f in findings if f.diameter}))
        evidence = tuple(sorted({f.message for f in findings if f.message})[:20])
        finding_ids = tuple(f.finding_id for f in findings)

        flags = []
        if not findings:
            flags.append("EMPTY_CLUSTER")
        if phase not in ("Annotation", "Fact", "Intent", "Detail", "Piece", "EngineeringBar", "Steel", "Workbook"):
            flags.append("INVALID_PHASE")
        if confidence <= 0:
            flags.append("ZERO_CONFIDENCE")

        return EngineeringIssue(
            issue_id=f"ISSUE-{idx:03d}",
            category=category,
            subcategory=subcategory,
            originating_phase=phase,
            affected_entities=entities,
            affected_beams=beams,
            affected_roles=roles,
            affected_diameters=dias,
            frequency=len(findings),
            severity=severity,
            engineering_impact=impact["engineering_impact"],
            steel_impact_kg=impact["steel_impact_kg"],
            weight_percentage=impact["weight_percentage"],
            production_accuracy_loss=impact["production_accuracy_loss"],
            root_cause=str(rec["root_cause"]),
            confidence=confidence,
            recommended_fix=str(rec["recommended_fix"]),
            recommended_phase=str(rec["recommended_phase"]),
            supporting_evidence=evidence,
            validation_flags=tuple(flags),
            source_phase="R.1.4",
            finding_ids=finding_ids,
            expected_accuracy_gain=float(rec["expected_accuracy_gain"]),
            priority=str(rec["priority"]),
        )

    @staticmethod
    def _normalize_steel(issues: List[EngineeringIssue], steel_gap_kg: float) -> List[EngineeringIssue]:
        if steel_gap_kg <= 0 or not issues:
            return issues
        total = sum(i.steel_impact_kg for i in issues)
        if total <= 0 or total <= steel_gap_kg * 1.05:
            return issues
        scale = steel_gap_kg / total
        out = []
        for i in issues:
            steel = round(i.steel_impact_kg * scale, 3)
            weight = round((steel / (steel_gap_kg / (i.weight_percentage / 100.0))) * 100.0, 3) if i.weight_percentage else 0.0
            # simpler weight recalc if we know official from weight_percentage
            # keep original weight scaled
            new_weight = round(i.weight_percentage * scale, 3)
            out.append(EngineeringIssue(
                issue_id=i.issue_id,
                category=i.category,
                subcategory=i.subcategory,
                originating_phase=i.originating_phase,
                affected_entities=i.affected_entities,
                affected_beams=i.affected_beams,
                affected_roles=i.affected_roles,
                affected_diameters=i.affected_diameters,
                frequency=i.frequency,
                severity=i.severity,
                engineering_impact=i.engineering_impact,
                steel_impact_kg=steel,
                weight_percentage=new_weight,
                production_accuracy_loss=i.production_accuracy_loss,
                root_cause=i.root_cause,
                confidence=i.confidence,
                recommended_fix=i.recommended_fix,
                recommended_phase=i.recommended_phase,
                supporting_evidence=i.supporting_evidence,
                validation_flags=i.validation_flags,
                source_phase=i.source_phase,
                finding_ids=i.finding_ids,
                expected_accuracy_gain=i.expected_accuracy_gain,
                priority=i.priority,
            ))
        return out
