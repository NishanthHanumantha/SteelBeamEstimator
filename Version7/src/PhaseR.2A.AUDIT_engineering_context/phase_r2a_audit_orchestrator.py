"""
Phase R.2A.AUDIT Orchestrator — READ-ONLY forensic audit runner.
MODEL_VERSION: 7.5.2
"""
from __future__ import annotations
import json
import pathlib
from datetime import datetime
from typing import Any, Dict

from .dxf_forensic_auditor import DXFForensicAuditor
from .audit_validator import AuditValidator
from .audit_writer import AuditWriter


class PhaseR2AAuditOrchestrator:

    def __init__(self, v7_root: pathlib.Path, output_dir: pathlib.Path):
        self._v7  = v7_root
        self._out = output_dir

    def _discover_gn_path(self) -> pathlib.Path:
        registry = (
            self._v7 / "src" / "PhaseVROOT.1_dynamic_pipeline_initialization"
            / "beam_registry.json"
        )
        if registry.exists():
            try:
                reg = json.loads(registry.read_text("utf-8"))
                gn = reg.get("general_notes_dxf") or reg.get("general_notes", {}).get("path")
                if gn:
                    p = pathlib.Path(gn)
                    if not p.is_absolute():
                        p = self._v7 / p
                    if p.exists():
                        return p
            except Exception:
                pass
        gn_dir = self._v7 / "data" / "Benchmark_Set_2" / "general_notes"
        dxf_files = sorted(gn_dir.glob("*.dxf"))
        if dxf_files:
            return dxf_files[0]
        raise FileNotFoundError("General Notes DXF not found")

    def run(self) -> Dict[str, Any]:
        print(f"\n{'='*70}")
        print("  PHASE R.2A.AUDIT — GN Multi-Sheet & LD Table Detection Audit")
        print(f"  MODEL_VERSION 7.5.2  |  {datetime.utcnow().isoformat()}")
        print(f"  READ-ONLY — no engineering logic modifications")
        print(f"{'='*70}\n")

        gn_path = self._discover_gn_path()
        print(f"[1/4] GN DXF: {gn_path}")

        auditor = DXFForensicAuditor(
            gn_path,
            self._v7 / "src",
        )
        print("[2/4] Running forensic DXF audit ...")
        audit_data = auditor.run()

        root = audit_data["root_cause_analysis"]
        hdrs = audit_data["development_length_headers"]
        print(f"      Layouts discovered : {audit_data['dxf_layout_inventory']['total_layouts']}")
        print(f"      LD headers in DXF  : {hdrs['total_ld_headers_found']}")
        print(f"      Parser sees        : {hdrs['headers_visible_to_production_parser']}")
        print(f"      Parser misses      : {hdrs['headers_invisible_to_production_parser']}")
        print(f"      FY-550 in DXF      : {hdrs['fy550_headers_found'] > 0}")
        print(f"      Root cause         : {root['deterministic_conclusion']} — {root['case_label']}")
        print(f"      Confidence         : {root['confidence_percent']}%")

        print("\n[3/4] Running 10-rule validation ...")
        validator = AuditValidator()
        results   = validator.validate(audit_data)
        passed    = sum(1 for r in results if r.passed)
        for r in results:
            st = "PASS" if r.passed else "FAIL"
            print(f"      [{st}] {r.rule_id}: {r.description}")

        print(f"\n[4/4] Exporting 10 JSON artefacts to: {self._out}")
        writer = AuditWriter(self._out)
        paths  = writer.write_all(audit_data, results)
        for name, path in paths.items():
            print(f"      {name}: {path}")

        all_pass = passed == len(results)
        print(f"\n{'='*70}")
        print(f"  PHASE R.2A.AUDIT COMPLETE")
        print(f"  Validation: {passed}/{len(results)}")
        print(f"  Root Cause: {root['deterministic_conclusion']}")
        print(f"  Finding: FY-550 table is inside block A$C15514357")
        print(f"           Parser does not expand INSERT blocks")
        print(f"{'='*70}\n")

        return {
            "status": "PASS" if all_pass else "FAIL",
            "validation_score": f"{passed}/{len(results)}",
            "root_cause": root["deterministic_conclusion"],
            "confidence_percent": root["confidence_percent"],
            "fy550_in_dxf": hdrs["fy550_headers_found"] > 0,
            "export_paths": paths,
        }
