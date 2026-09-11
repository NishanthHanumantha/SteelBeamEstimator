"""Export all Phase R.1.2A artefacts."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Optional


class GeometryReportExporter:

    def __init__(
        self,
        v7_root: Optional[pathlib.Path] = None,
        output_root: Optional[pathlib.Path] = None,
        run_root: Optional[pathlib.Path] = None,
    ):
        if output_root is not None:
            out_base = pathlib.Path(output_root)
        elif run_root is not None:
            out_base = pathlib.Path(run_root) / "data" / "output"
        elif v7_root is not None:
            out_base = pathlib.Path(v7_root) / "data" / "output"
        else:
            raise ValueError("output_root, run_root, or v7_root required")
        self._out = out_base / "PhaseR1_2A_geometry_accuracy"
        self._out.mkdir(parents=True, exist_ok=True)

    @property
    def output_dir(self) -> pathlib.Path:
        return self._out

    def export_all(self, result: Dict[str, Any], report_md: str) -> Dict[str, str]:
        written = {}
        payloads = {
            "geometry_trace.json": result.get("trace", {}),
            "geometry_provider_summary.json": result.get("provider_summary", {}),
            "geometry_source_validation.json": result.get("source_validation", {}),
            "geometry_propagation_audit.json": result.get("propagation_audit", {}),
            "geometry_consistency_report.json": result.get("consistency", {}),
            "span_validation.json": result.get("span_validation", {}),
            "cut_length_validation.json": result.get("cut_validation", {}),
            "bbs_geometry_validation.json": result.get("bbs_validation", {}),
            "benchmark_regression_geometry.json": result.get("regression", {}),
        }
        for name, data in payloads.items():
            path = self._out / name
            path.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
            written[name] = str(path)

        md_path = self._out / "geometry_accuracy_report.md"
        md_path.write_text(report_md, encoding="utf-8")
        written["geometry_accuracy_report.md"] = str(md_path)
        return written

    def export_stubs(self, provider_summary: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Minimal artefacts for catalog-only production path."""
        stub_result: Dict[str, Any] = {
            "trace": {},
            "provider_summary": provider_summary or {},
            "source_validation": {},
            "propagation_audit": {},
            "consistency": {},
            "span_validation": {},
            "cut_validation": {},
            "bbs_validation": {},
            "regression": {"summary": "catalog_only — forensic validators skipped"},
            "validation": {"passed": 0, "total": 0, "rules": []},
            "recommendation": "A",
        }
        report_md = (
            "# Phase R.1.2A — Geometry Accuracy (catalog-only)\n\n"
            "**MODE:** catalog_only — GeometryProvider resolve + validated_beam_geometry.json\n"
            "Forensic rebuild / validators skipped (web + offline production path).\n"
        )
        return self.export_all(stub_result, report_md)

    def generate_report(self, result: Dict[str, Any]) -> str:
        val = result.get("validation", {})
        cons = result.get("consistency", {})
        span = result.get("span_validation", {})
        cut = result.get("cut_validation", {})
        bbs = result.get("bbs_validation", {})
        prop = result.get("propagation_audit", {})
        rec = result.get("recommendation", "B")
        prov = result.get("provider_summary", {}).get("audit", {})

        lines = [
            "# Phase R.1.2A — Geometry Accuracy & Span Propagation Engine",
            "",
            "**MODEL_VERSION:** 8.9.4",
            f"**Validation:** {val.get('passed', 0)}/{val.get('total', 8)} rules passed",
            "",
            "## 1. Executive Summary",
            "",
            "Constant Spacing=8.775 m across all beams was caused by V.ROOT.1 "
            "`DynamicBeamDiscovery._nearby_texts` returning every drawing text and "
            "`_extract_span` selecting the global max DIMENSION (8775 mm).",
            "",
            "GeometryProvider is now the sole production geometry interface. "
            f"Unique spans: **{cons.get('unique_span_count', '?')}** across "
            f"**{cons.get('beams_with_span', '?')}** beams with geometry.",
            "",
            "## 2. Root Cause Analysis",
            "",
            "| Module | Function | Defect | Status |",
            "|--------|----------|--------|--------|",
        ]
        for f in prop.get("findings", []):
            lines.append(
                f"| `{f['module']}` | `{f['function']}` | {f['defect']} | {f['status']} |"
            )

        lines.extend([
            "",
            "## 3. Geometry Provider Architecture",
            "",
            "```",
            "Framing Plan LINE (evidence-scored)",
            "Reinforcement DIMENSION (spatially filtered)",
            "Beam Registry (rejected if constant-span anomaly)",
            "        |",
            "        v",
            " GeometryProvider  -->  validated_beam_geometry.json",
            "        |",
            "        v",
            " EngineeringBarBuilder -> Steel -> BBS -> Workbook",
            "```",
            "",
            f"- Framing hits: {prov.get('framing_hits', '?')}",
            f"- Reinforcement hits: {prov.get('reinforcement_hits', '?')}",
            f"- Source counts: {prov.get('source_counts', {})}",
            f"- Registry constant span rejected: {prov.get('registry_constant_span_rejected')}",
            "",
            "## 4. Geometry Trace Results",
            "",
            f"- Trails: {result.get('trace', {}).get('total_beams', '?')}",
            f"- Passed: {result.get('trace', {}).get('passed', '?')}",
            f"- Failed: {result.get('trace', {}).get('failed', '?')}",
            f"- Missing: {result.get('trace', {}).get('missing', '?')}",
            "",
            "## 5. Geometry Propagation Audit",
            "",
            f"- Findings documented: {len(prop.get('findings', []))}",
            f"- Fixed: {prop.get('fixed_count', '?')}",
            "",
            "## 6. Span Validation Results",
            "",
            f"- Match %: {span.get('match_pct', '?')}%",
            f"- Mismatches: {span.get('mismatch_count', '?')}",
            f"- Tolerance: {span.get('tolerance_m', 0.001)} m",
            "",
            "## 7. Cut Length Validation Results",
            "",
            f"- Bars checked: {cut.get('bars_checked', '?')}",
            f"- Issues: {cut.get('issue_count', '?')}",
            "",
            "## 8. BBS Geometry Validation",
            "",
            f"- Headers checked: {bbs.get('headers_checked', '?')}",
            f"- Unique spacings: {bbs.get('unique_spacings', '?')}",
            f"- Constant spacing detected: {bbs.get('constant_spacing_detected', '?')}",
            f"- Mismatches: {bbs.get('mismatch_count', '?')}",
            "",
            "## 9. Regression Results",
            "",
            f"- {result.get('regression', {}).get('summary', 'N/A')}",
            "",
            "## 10. Remaining Geometry Risks",
            "",
            "- Framing line association can pick non-beam segments on dense plans.",
            "- Beams without framing labels rely on reinforcement DIMENSION evidence.",
            "- Missing spans are flagged, never silently replaced with defaults.",
            "",
            "## 11. Exported Artefacts",
            "",
            "All artefacts under `PhaseR1_2A_geometry_accuracy/` (output_root)",
            "",
            "## 12. Validation Summary",
            "",
        ])
        for rule in val.get("rules", []):
            icon = "[PASS]" if rule["passed"] else "[FAIL]"
            lines.append(f"- {icon} **{rule['rule_id']}**: {rule['name']} — {rule['detail']}")

        lines.extend(["", "## Recommendation", ""])
        if rec == "A":
            lines.append(
                "**Recommendation A: Ready for Phase R.1.2B — EngineeringBar Deduplication & Consolidation Engine**"
            )
        else:
            lines.append(
                "**Recommendation B: Additional geometry improvements required.**"
            )
        return "\n".join(lines)
