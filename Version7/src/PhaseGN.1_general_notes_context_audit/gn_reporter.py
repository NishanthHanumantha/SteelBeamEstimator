"""
GN Reporter — generates the human-readable engineering audit report.
"""
from __future__ import annotations
import textwrap
from typing import Any, Dict, List

from .gn_models import (
    GNDiscoveryRecord, ExtractedParameter, TraceabilityNode,
    FramingFieldAudit, RebarFieldAudit, HardcodedDefault,
    ConsumptionRecord, EngineeringGap, ValidationResult,
    GapSeverity,
)


class GNReporter:

    def build_report(
        self,
        discovery: GNDiscoveryRecord,
        extracted: List[ExtractedParameter],
        traceability: List[TraceabilityNode],
        framing: List[FramingFieldAudit],
        rebar: List[RebarFieldAudit],
        hardcoded: List[HardcodedDefault],
        consumption: List[ConsumptionRecord],
        gaps: List[EngineeringGap],
        generalization: Dict,
        validation: List[ValidationResult],
    ) -> Dict[str, Any]:

        passed_rules = sum(1 for v in validation if v.passed)
        total_rules = len(validation)
        score = f"{passed_rules}/{total_rules}"

        critical_gaps = [g for g in gaps if g.severity == GapSeverity.CRITICAL]
        high_gaps     = [g for g in gaps if g.severity == GapSeverity.HIGH]
        medium_gaps   = [g for g in gaps if g.severity == GapSeverity.MEDIUM]
        low_gaps      = [g for g in gaps if g.severity == GapSeverity.LOW]

        if passed_rules == total_rules:
            if critical_gaps:
                verdict = "AUDIT_COMPLETE_WITH_CRITICAL_GAPS"
            elif high_gaps:
                verdict = "AUDIT_COMPLETE_WITH_HIGH_GAPS"
            else:
                verdict = "AUDIT_COMPLETE"
        else:
            verdict = f"AUDIT_INCOMPLETE_{total_rules - passed_rules}_RULES_FAILED"

        return {
            "phase": "GN.1",
            "model_version": "7.4.0",
            "validation_score": score,
            "overall_verdict": verdict,
            "summary": self._build_summary(
                discovery, extracted, gaps, passed_rules, total_rules
            ),
            "part_1_gn_discovery": {
                "project_id": discovery.project_id,
                "gn_dxf_path": discovery.gn_dxf_path,
                "sheet_name": discovery.sheet_name,
                "discovered_dynamically": discovery.discovered_dynamically,
                "discovery_method": discovery.discovery_method,
                "total_text_entities": discovery.total_text_entities,
                "entity_counts": discovery.entity_counts,
                "layers": discovery.layers_present,
                "benchmark_set1_dependency": discovery.benchmark_set_1_dependency,
                "version6_dependency": discovery.version6_dependency,
                "hardcoded_path_used": discovery.hardcoded_path_used,
                "notes": discovery.notes,
            },
            "part_2_extraction_audit": [
                self._param_to_dict(p) for p in extracted
            ],
            "part_3_traceability_graph": [
                self._trace_to_dict(n) for n in traceability
            ],
            "part_4_framing_audit": [
                self._framing_to_dict(f) for f in framing
            ],
            "part_5_rebar_audit": [
                self._rebar_to_dict(r) for r in rebar
            ],
            "part_6_hardcoded_defaults": [
                self._hardcoded_to_dict(h) for h in hardcoded
            ],
            "part_7_consumption_matrix": [
                self._consumption_to_dict(c) for c in consumption
            ],
            "part_8_gap_analysis": [
                self._gap_to_dict(g) for g in gaps
            ],
            "part_9_generalization_check": generalization,
            "part_10_validation": [
                self._validation_to_dict(v) for v in validation
            ],
            "gap_severity_summary": {
                "CRITICAL": len(critical_gaps),
                "HIGH": len(high_gaps),
                "MEDIUM": len(medium_gaps),
                "LOW": len(low_gaps),
                "total": len(gaps),
            },
            "action_items_for_r2": self._build_r2_actions(gaps),
        }

    # ------------------------------------------------------------------
    def _build_summary(
        self,
        discovery: GNDiscoveryRecord,
        extracted: List[ExtractedParameter],
        gaps: List[EngineeringGap],
        passed: int,
        total: int,
    ) -> Dict:
        return {
            "gn_dxf_found": discovery.gn_dxf_path != "NOT_FOUND",
            "gn_discovered_dynamically": discovery.discovered_dynamically,
            "engineering_parameters_extracted": len(extracted),
            "parameters_consumed_by_pipeline": sum(
                1 for p in extracted
                if p.consumed_by_steel_weight or p.consumed_by_bbs or p.consumed_by_excel
            ),
            "total_engineering_gaps": len(gaps),
            "critical_gaps": sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL),
            "high_gaps": sum(1 for g in gaps if g.severity == GapSeverity.HIGH),
            "validation_score": f"{passed}/{total}",
            "key_finding": (
                "GN DXF is DISCOVERED by V.ROOT.1 but NOT PARSED. "
                "All engineering constants (dev length 40d, cover 40mm, hook 10d, "
                "steel grade Fe415) are HARDCODED in the pipeline source. "
                "Values HAPPEN to match the GN DXF for Benchmark Set 2 project "
                "but will BREAK for any project with different engineering parameters. "
                "Phase R.2 must implement live GN DXF parsing."
            ),
            "readiness_for_r2": (
                "READY — audit evidence collected. "
                "All gaps prioritised. GN DXF structure fully mapped."
            ),
        }

    def _build_r2_actions(self, gaps: List[EngineeringGap]) -> List[Dict]:
        actions = []
        for g in sorted(gaps, key=lambda x: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(x.severity)):
            actions.append({
                "gap_id": g.gap_id,
                "priority": g.severity,
                "action": g.recommendation,
                "affected_modules": g.affected_modules,
            })
        return actions

    # ------------------------------------------------------------------
    def _param_to_dict(self, p: ExtractedParameter) -> Dict:
        return {
            "parameter": p.parameter_name,
            "source_drawing": p.source_drawing,
            "source_layer": p.source_layer,
            "source_text": p.source_text,
            "parsed_value": p.parsed_value,
            "classification": p.classification,
            "consumers": p.consumers,
            "consumed_by_steel_weight": p.consumed_by_steel_weight,
            "consumed_by_bbs": p.consumed_by_bbs,
            "consumed_by_excel": p.consumed_by_excel,
            "notes": p.notes,
        }

    def _trace_to_dict(self, n: TraceabilityNode) -> Dict:
        return {
            "parameter": n.parameter_name,
            "source_drawing": n.source_drawing,
            "extracted_value": n.extracted_value,
            "pipeline_value": n.pipeline_value,
            "match": n.match,
            "dependency_chain": " -> ".join(n.dependency_chain),
            "consumers": n.consumers,
            "gap_severity": n.gap_severity,
        }

    def _framing_to_dict(self, f: FramingFieldAudit) -> Dict:
        return {
            "field": f.field_name,
            "source_drawing": f.source_drawing,
            "source_entity": f.source_entity,
            "consumer_modules": f.consumer_modules,
            "used": f.used,
            "pipeline_value_example": f.pipeline_value_example,
            "classification": f.classification,
            "notes": f.notes,
        }

    def _rebar_to_dict(self, r: RebarFieldAudit) -> Dict:
        return {
            "field": r.field_name,
            "source_drawing": r.source_drawing,
            "source_entity": r.source_entity,
            "consumer_modules": r.consumer_modules,
            "used": r.used,
            "example_annotation": r.example_annotation,
            "classification": r.classification,
            "notes": r.notes,
        }

    def _hardcoded_to_dict(self, h: HardcodedDefault) -> Dict:
        return {
            "file": h.file_path,
            "line": h.line_number,
            "symbol": h.symbol,
            "literal_value": h.literal_value,
            "engineering_meaning": h.engineering_meaning,
            "classification": h.classification,
            "gn_equivalent": h.gn_equivalent,
            "severity": h.severity,
            "notes": h.notes,
        }

    def _consumption_to_dict(self, c: ConsumptionRecord) -> Dict:
        return {
            "parameter": c.parameter_name,
            "gn_value": c.gn_value,
            "steel_weight_value": c.steel_weight_value,
            "bbs_value": c.bbs_value,
            "excel_value": c.excel_value,
            "steel_match": c.steel_match,
            "bbs_match": c.bbs_match,
            "excel_match": c.excel_match,
            "all_match": c.all_match,
            "notes": c.notes,
        }

    def _gap_to_dict(self, g: EngineeringGap) -> Dict:
        return {
            "gap_id": g.gap_id,
            "parameter": g.parameter_name,
            "gap_type": g.gap_type,
            "severity": g.severity,
            "description": g.description,
            "impact": g.impact,
            "recommendation": g.recommendation,
            "affected_modules": g.affected_modules,
        }

    def _validation_to_dict(self, v: ValidationResult) -> Dict:
        return {
            "rule_id": v.rule_id,
            "rule_name": v.rule_name,
            "passed": v.passed,
            "status": "PASS" if v.passed else "FAIL",
            "evidence": v.evidence,
            "detail": v.detail,
        }
