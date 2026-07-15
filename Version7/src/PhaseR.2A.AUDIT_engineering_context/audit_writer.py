"""
Audit Writer — exports 10 JSON artefacts for Phase R.2A.AUDIT
"""
from __future__ import annotations
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List


def _save(out: pathlib.Path, name: str, data: Any) -> str:
    p = out / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(p)


class AuditWriter:
    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def write_all(
        self,
        audit_data: Dict[str, Any],
        validation_results: List,
    ) -> Dict[str, str]:
        ts = datetime.utcnow().isoformat()
        paths: Dict[str, str] = {}

        # Slim layout_text_inventory for export (full data can be large)
        text_inv = audit_data["layout_text_inventory"]
        text_export = {
            "generated": ts,
            "production_parser_scope": text_inv["production_parser_scope"],
            "production_parser_item_count": text_inv["production_parser_item_count"],
            "call_trace": text_inv["call_trace"],
            "layouts": [],
        }
        for layout in text_inv["layouts"]:
            text_export["layouts"].append({
                "layout_name": layout["layout_name"],
                "text_entities_extracted": layout["text_entities_extracted"],
                "mtext_entities_extracted": layout["mtext_entities_extracted"],
                "virtual_text_from_inserts": layout["virtual_text_from_inserts"],
                "rejected_entities": layout["rejected_entities"],
                "skipped_entities": layout["skipped_entities"],
                "production_parser_reads_this_layout": layout["production_parser_reads_this_layout"],
                "ld_headers_in_layout": [
                    e for e in layout.get("extracted_entities", [])
                    + layout.get("virtual_insert_entities", [])
                    if "LD FOR" in e.get("text", "").upper()
                ],
                "skipped_entity_details": layout.get("skipped_entity_details", [])[:20],
            })

        exports = [
            ("dxf_layout_inventory.json", {
                "generated": ts,
                **audit_data["dxf_layout_inventory"],
            }),
            ("layout_text_inventory.json", text_export),
            ("development_length_headers.json", {
                "generated": ts,
                **audit_data["development_length_headers"],
            }),
            ("table_detection_trace.json", {
                "generated": ts,
                **audit_data["table_detection_trace"],
            }),
            ("parser_execution_trace.json", {
                "generated": ts,
                **audit_data["parser_execution_trace"],
            }),
            ("regex_audit.json", {
                "generated": ts,
                **audit_data["regex_audit"],
            }),
            ("bounding_box_audit.json", {
                "generated": ts,
                **audit_data["bounding_box_audit"],
            }),
            ("root_cause_analysis.json", {
                "generated": ts,
                **audit_data["root_cause_analysis"],
            }),
            ("engineering_audit_report.json", {
                "generated": ts,
                **audit_data["engineering_audit_report"],
            }),
            ("validation_report.json", {
                "generated": ts,
                "phase": "R.2A.AUDIT",
                "model_version": "7.5.2",
                "validation_score": (
                    f"{sum(1 for r in validation_results if r.passed)}"
                    f"/{len(validation_results)}"
                ),
                "all_pass": all(r.passed for r in validation_results),
                "rules": [r.to_dict() for r in validation_results],
            }),
        ]

        for filename, data in exports:
            key = filename.replace(".json", "")
            paths[key] = _save(self._out, filename, data)

        return paths
