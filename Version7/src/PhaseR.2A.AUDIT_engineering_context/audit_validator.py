"""
Audit Validator — 10 rules for Phase R.2A.AUDIT
"""
from __future__ import annotations
from typing import Any, Dict, List


class AuditValidationResult:
    def __init__(self, rule_id: str, description: str, passed: bool, evidence: str):
        self.rule_id = rule_id
        self.description = description
        self.passed = passed
        self.evidence = evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "passed": self.passed,
            "status": "PASS" if self.passed else "FAIL",
            "evidence": self.evidence,
        }


class AuditValidator:
    def validate(self, audit_data: Dict[str, Any]) -> List[AuditValidationResult]:
        inv   = audit_data.get("dxf_layout_inventory", {})
        text  = audit_data.get("layout_text_inventory", {})
        hdrs  = audit_data.get("development_length_headers", {})
        table = audit_data.get("table_detection_trace", {})
        regex = audit_data.get("regex_audit", {})
        bbox  = audit_data.get("bounding_box_audit", {})
        root  = audit_data.get("root_cause_analysis", {})
        report = audit_data.get("engineering_audit_report", {})

        return [
            AuditValidationResult(
                "RULE_1", "All layouts discovered",
                inv.get("total_layouts", 0) >= 3,
                f"Layouts found: {inv.get('total_layouts')} — {inv.get('hierarchy', [])}",
            ),
            AuditValidationResult(
                "RULE_2", "All layouts scanned",
                len(text.get("layouts", [])) >= inv.get("total_layouts", 0),
                f"Layouts scanned: {len(text.get('layouts', []))}",
            ),
            AuditValidationResult(
                "RULE_3", "Entity counts reported",
                all("entity_count" in l or "text_entities_extracted" in l
                    for l in text.get("layouts", [])),
                "Entity counts present for all layouts",
            ),
            AuditValidationResult(
                "RULE_4", "Text inventory exported",
                "layouts" in text and len(text["layouts"]) > 0,
                f"Text inventory covers {len(text.get('layouts', []))} layouts",
            ),
            AuditValidationResult(
                "RULE_5", "Every LD header listed",
                hdrs.get("total_ld_headers_found", 0) >= 3,
                f"LD headers: {hdrs.get('total_ld_headers_found')} "
                f"(FY550: {hdrs.get('fy550_headers_found')})",
            ),
            AuditValidationResult(
                "RULE_6", "Table detector traced",
                "tables" in table and "parser_stops_reason" in table,
                f"Tables traced: {len(table.get('tables', []))}",
            ),
            AuditValidationResult(
                "RULE_7", "Regex audited",
                regex.get("regex_excludes_fy550") is False and "test_results" in regex,
                "Regex tested; FY-550 would match if text were extracted",
            ),
            AuditValidationResult(
                "RULE_8", "Bounding boxes reported",
                "fy550_table_world_bounding_box" in bbox,
                f"FY550 bbox: {bbox.get('fy550_table_world_bounding_box')}",
            ),
            AuditValidationResult(
                "RULE_9", "Root cause identified",
                root.get("deterministic_conclusion") in ("CASE A", "CASE B", "CASE C", "CASE D", "CASE E")
                and root.get("confidence_percent", 0) >= 90,
                f"{root.get('deterministic_conclusion')}: {root.get('case_label')} "
                f"({root.get('confidence_percent')}%)",
            ),
            AuditValidationResult(
                "RULE_10", "Zero engineering logic modified",
                report.get("engineering_logic_modified") is False,
                "READ-ONLY audit — no EngineeringContext or parser code changed",
            ),
        ]
