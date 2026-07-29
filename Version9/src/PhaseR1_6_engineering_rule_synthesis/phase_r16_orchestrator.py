"""
Phase R.1.6 orchestrator.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from engineering_rule_builder import EngineeringRuleBuilder
from gap_resolution_engine import GapResolutionEngine
from input_loader import InputLoader
from json_exporter import JsonExporter
from recommendation_generator import RecommendationGenerator
from report_generator import ReportGenerator
from rule_conflict_detector import RuleConflictDetector
from rule_dependency_engine import RuleDependencyEngine
from rule_library_builder import RuleLibraryBuilder
from rule_pattern_detector import RulePatternDetector
from rule_priority_engine import RulePriorityEngine
from rule_traceability_engine import RuleTraceabilityEngine
from rule_validation_engine import RegressionEngine, RuleValidationEngine

MODEL_VERSION = "8.8.0"
PHASE_ID = "R.1.6"


class PhaseR16Orchestrator:
    def __init__(self, v8_root: Optional[Path] = None):
        self.v8 = Path(v8_root) if v8_root else Path(__file__).resolve().parents[2]
        self.out = self.v8 / "data" / "output" / "PhaseR1_6_engineering_rule_synthesis"
        self.package_dir = Path(__file__).resolve().parent

    def run(self) -> Dict[str, Any]:
        print("=" * 72)
        print("Phase R.1.6 — Engineering Rule Synthesis & Gap Resolution Engine")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print("READ-ONLY — no production modification / no auto-correction")
        print("=" * 72)
        t0 = time.perf_counter()

        print("\n[1/9] Loading R.1.4 + R.1.5 artefacts ...")
        data = InputLoader(self.v8).load()
        issues = data["issues"]
        print(f"      Engineering issues={len(issues)}")
        if not issues:
            raise RuntimeError("No R.1.5 issues found — run Phase R.1.5 first.")

        print("\n[2/9] Pattern detection ...")
        patterns = RulePatternDetector().detect(issues)
        print(f"      Patterns={patterns.get('pattern_count')}")

        print("\n[3/9] Synthesizing Engineering Rules ...")
        rules = EngineeringRuleBuilder().build_library(issues, patterns)
        print(f"      Rules={len(rules)}")

        print("\n[4/9] Dependencies + conflicts ...")
        rules, dependencies = RuleDependencyEngine().apply(rules)
        rules, conflicts = RuleConflictDetector().detect(rules)
        print(f"      Edges={dependencies.get('edge_count')} acyclic={dependencies.get('acyclic')}")
        print(f"      Conflicts={conflicts.get('conflict_count')}")

        print("\n[5/9] Priority + library + gap plan + roadmap ...")
        rules = RulePriorityEngine().prioritize(rules)
        lib_builder = RuleLibraryBuilder()
        library = lib_builder.library_index(rules)
        roadmap = lib_builder.build_roadmap(rules)
        gap_plan = GapResolutionEngine().plan(rules)
        rule_recs = RecommendationGenerator().generate(rules)

        print("\n[6/9] Traceability ...")
        traceability = RuleTraceabilityEngine().build(rules, issues, data["backlog"])
        print(f"      Traceability complete={traceability.get('complete')}")

        print("\n[7/9] Validation + regression ...")
        placeholder_exports = {f"f{i}": "" for i in range(10)}
        validation = RuleValidationEngine().validate(
            issues, rules, dependencies, conflicts, traceability,
            placeholder_exports, self.package_dir,
        )
        regression = RegressionEngine().run(rules, self.package_dir)
        if not regression.get("passed"):
            validation["rules"].append({"id": "regression_passed", "passed": False})
        else:
            validation["rules"].append({"id": "regression_passed", "passed": True})
        validation["passed"] = sum(1 for r in validation["rules"] if r["passed"])
        validation["total"] = len(validation["rules"])
        validation["overall_passed"] = validation["passed"] == validation["total"]
        recommendation = "A" if validation["overall_passed"] else "B"
        print(f"      Validation {validation['passed']}/{validation['total']} -> {recommendation}")

        payload: Dict[str, Any] = {
            "model_version": MODEL_VERSION,
            "phase": PHASE_ID,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "recommendation": recommendation,
            "issues": issues,
            "rules": rules,
            "patterns": patterns,
            "dependencies": dependencies,
            "conflicts": conflicts,
            "library": library,
            "roadmap": roadmap,
            "gap_plan": gap_plan,
            "traceability": traceability,
            "validation": validation,
            "regression": regression,
            "rule_recommendations": rule_recs,
            "sources": data["sources"],
        }

        print("\n[8/9] Exporting artefacts ...")
        paths = JsonExporter(self.out).export_all(payload)
        md = ReportGenerator().markdown(payload)
        md_path = self.out / "phase_r16_summary.md"
        md_path.write_text(md, encoding="utf-8")
        paths["phase_r16_summary.md"] = str(md_path)

        # Final validation with real exports
        validation = RuleValidationEngine().validate(
            issues, rules, dependencies, conflicts, traceability, paths, self.package_dir,
        )
        validation["rules"].append({
            "id": "regression_passed",
            "passed": bool(regression.get("passed")),
        })
        validation["passed"] = sum(1 for r in validation["rules"] if r["passed"])
        validation["total"] = len(validation["rules"])
        validation["overall_passed"] = validation["passed"] == validation["total"]
        recommendation = "A" if validation["overall_passed"] else "B"
        payload["validation"] = validation
        payload["recommendation"] = recommendation
        (self.out / "rule_validation.json").write_text(
            json.dumps(validation, indent=2), encoding="utf-8"
        )
        md_path.write_text(ReportGenerator().markdown(payload), encoding="utf-8")

        print("\n[9/9] Done")
        print("=" * 72)
        status = "PASS" if validation["overall_passed"] else "WARN"
        print(f"STATUS: {status} | Recommendation: {recommendation}")
        print(f"Output: {self.out}")
        print("=" * 72)

        payload["export_paths"] = paths
        payload["status"] = status
        return payload
