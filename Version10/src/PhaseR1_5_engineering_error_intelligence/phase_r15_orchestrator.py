"""
Phase R.1.5 orchestrator — Engineering Error Intelligence Engine.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

from engineering_issue_builder import EngineeringIssueBuilder
from error_cluster_engine import ErrorClusterEngine
from frequency_analysis_engine import FrequencyAnalysisEngine
from improvement_backlog_engine import ImprovementBacklogEngine
from input_loader import BenchmarkInputLoader
from json_exporter import JsonExporter
from report_builder import ReportBuilder
from root_cause_engine import RootCauseEngine
from trend_engine import TrendEngine
from validation import PhaseR15Validator, RegressionEngine

MODEL_VERSION = "8.7.0"
PHASE_ID = "R.1.5"


class PhaseR15Orchestrator:
    def __init__(self, v8_root: Optional[Path] = None):
        self.v8 = Path(v8_root) if v8_root else Path(__file__).resolve().parents[2]
        self.out = self.v8 / "data" / "output" / "PhaseR1_5_engineering_error_intelligence"
        self.package_dir = Path(__file__).resolve().parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.5 — Engineering Error Intelligence Engine")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("READ-ONLY analysis — no production modification")
        print("=" * 72)
        t0 = time.perf_counter()

        print("\n[1/8] Loading R.1.4 benchmark artefacts ...")
        data = BenchmarkInputLoader(self.v8).load()
        findings = data["findings"]
        print(
            f"      Findings={len(findings)} steel_gap={data['steel_gap_kg']} kg "
            f"accuracy={round(data['overall_accuracy']*100, 2)}%"
        )
        if not findings:
            raise RuntimeError("No R.1.4 diagnostics found — run Phase R.1.4 first.")

        print("\n[2/8] Classifying + clustering findings ...")
        clusters = ErrorClusterEngine().cluster(findings)
        print(f"      Clusters (Engineering Issues)={len(clusters)}")

        print("\n[3/8] Building EngineeringIssue objects ...")
        issues = EngineeringIssueBuilder().build_all(
            clusters,
            official_total_kg=data["official_total_kg"],
            steel_gap_kg=data["steel_gap_kg"],
            kpi_loss=data["kpi_loss"],
        )
        print(f"      Issues built={len(issues)}")

        print("\n[4/8] Frequency / impact summaries ...")
        frequency = FrequencyAnalysisEngine().analyze(issues, len(findings))
        reporter = ReportBuilder()
        phase_summary = reporter.phase_summary(issues)
        severity_summary = reporter.severity_summary(issues)

        print("\n[5/8] Ranking + recommendations + backlog ...")
        # Rank issues
        ranked_issues = sorted(
            issues,
            key=lambda i: (-i.engineering_impact, -i.frequency, -i.confidence, i.issue_id),
        )
        rankings = RootCauseEngine().rank(ranked_issues, top_n=20)
        backlog = ImprovementBacklogEngine().build(ranked_issues)
        trends = TrendEngine().analyze(
            issues, findings, data["official_total_kg"], data["steel_gap_kg"],
        )
        print(f"      Top issue: {rankings['rankings'][0]['category'] if rankings.get('rankings') else 'n/a'}")
        print(f"      Backlog items: {backlog.get('item_count')}")

        print("\n[6/8] Validation + regression ...")
        # Temporary exports count placeholder — validate after export
        validation_pre_exports = {f"placeholder_{i}": "" for i in range(11)}
        validation = PhaseR15Validator().validate(
            findings, issues, rankings, backlog, validation_pre_exports, self.package_dir,
        )
        regression = RegressionEngine().run(issues, rankings, self.package_dir)
        # merge regression into validation gate
        if not regression.get("passed"):
            validation["overall_passed"] = False
            validation["rules"].append({"id": "regression_passed", "passed": False})
        else:
            validation["rules"].append({"id": "regression_passed", "passed": True})
            validation["passed"] = sum(1 for r in validation["rules"] if r["passed"])
            validation["total"] = len(validation["rules"])
            validation["overall_passed"] = validation["passed"] == validation["total"]

        recommendation = "A" if validation.get("overall_passed") else "B"
        print(f"      Validation {validation['passed']}/{validation['total']} -> {recommendation}")

        dashboard = reporter.build_dashboard(
            issues, rankings, backlog, trends, validation,
            data["overall_accuracy"], data["steel_gap_kg"],
        )

        payload: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "recommendation": recommendation,
            "finding_count": len(findings),
            "issues": issues,
            "rankings": rankings,
            "backlog": backlog,
            "trends": trends,
            "frequency": frequency,
            "phase_summary": phase_summary,
            "severity_summary": severity_summary,
            "dashboard": dashboard,
            "validation": validation,
            "regression": regression,
            "overall_accuracy": data["overall_accuracy"],
            "steel_gap_kg": data["steel_gap_kg"],
            "sources": data["sources"],
        }

        print("\n[7/8] Exporting artefacts ...")
        exporter = JsonExporter(self.out)
        paths = exporter.export_all(payload)
        md = reporter.markdown(payload)
        md_path = self.out / "phase_r15_summary.md"
        md_path.write_text(md, encoding="utf-8")
        paths["phase_r15_summary.md"] = str(md_path)

        # Re-check reports_generated with real exports
        validation = PhaseR15Validator().validate(
            findings, issues, rankings, backlog, paths, self.package_dir,
        )
        if regression.get("passed"):
            validation["rules"].append({"id": "regression_passed", "passed": True})
        else:
            validation["rules"].append({"id": "regression_passed", "passed": False})
        validation["passed"] = sum(1 for r in validation["rules"] if r["passed"])
        validation["total"] = len(validation["rules"])
        validation["overall_passed"] = validation["passed"] == validation["total"]
        recommendation = "A" if validation.get("overall_passed") else "B"
        payload["validation"] = validation
        payload["recommendation"] = recommendation
        # rewrite validation report
        (self.out / "validation_report.json").write_text(
            __import__("json").dumps(validation, indent=2), encoding="utf-8"
        )
        md_path.write_text(reporter.markdown(payload), encoding="utf-8")

        print("\n[8/8] Done")
        print("=" * 72)
        print(f"STATUS: {'PASS' if validation['overall_passed'] else 'WARN'} | Recommendation: {recommendation}")
        print(f"Output: {self.out}")
        print("=" * 72)

        payload["export_paths"] = paths
        payload["status"] = "PASS" if validation["overall_passed"] else "WARN"
        return payload
