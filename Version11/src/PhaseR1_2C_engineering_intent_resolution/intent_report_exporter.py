"""Export Phase R.1.2C artefacts."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict


class IntentReportExporter:
    OUT_DIR_NAME = "PhaseR1_2C_engineering_intent_resolution"

    def __init__(self, v7_root: pathlib.Path):
        self._out = v7_root / "data/output" / self.OUT_DIR_NAME
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(self, result: Dict[str, Any], report_md: str) -> Dict[str, str]:
        written = {}
        payloads = {
            "engineering_intents.json": {
                "model_version": result.get("model_version"),
                "intent_count": len(result.get("intents") or []),
                "intents": result.get("intents") or [],
            },
            "engineering_role_resolution.json": result.get("role_resolution") or {},
            "engineering_diameter_resolution.json": result.get("diameter_resolution") or {},
            "engineering_extent_resolution.json": result.get("extent_resolution") or {},
            "engineering_intent_confidence.json": result.get("confidence") or {},
            "engineering_consistency_validation.json": result.get("consistency") or {},
            "engineeringbar_intent_mapping.json": {
                "model_version": result.get("model_version"),
                "mappings": result.get("mapping") or [],
            },
            "bbs_intent_validation.json": result.get("bbs_validation") or {},
            "estimator_comparison_metrics.json": result.get("estimator_comparison") or {},
            "benchmark_regression_intent.json": result.get("regression") or {},
        }
        for name, data in payloads.items():
            path = self._out / name
            path.write_text(
                json.dumps(data, indent=2, default=str, ensure_ascii=False),
                encoding="utf-8",
            )
            written[name] = str(path)
        md = self._out / "engineering_intent_resolution_report.md"
        md.write_text(report_md, encoding="utf-8")
        written["engineering_intent_resolution_report.md"] = str(md)
        return written

    def generate_report(self, result: Dict[str, Any]) -> str:
        val = result.get("validation") or {}
        role = result.get("role_resolution") or {}
        ext = result.get("extent_resolution") or {}
        conf = result.get("confidence") or {}
        bbs = result.get("bbs_validation") or {}
        est = result.get("estimator_comparison") or {}
        reg = result.get("regression") or {}
        rec = result.get("recommendation", "B")
        lines = [
            "# Phase R.1.2C — Engineering Intent Resolution Engine",
            "",
            "**MODEL_VERSION:** 8.3.2",
            f"**Validation:** {val.get('passed', 0)}/{val.get('total', 8)} rules passed",
            f"**Recommendation:** {rec}",
            "",
            "## 1. Executive Summary",
            "",
            "Remaining estimator deviations were driven by incorrect engineering "
            "intent (role / extent) after annotation discovery and consolidation "
            "were already correct. R.1.2C introduces an explicit "
            "`EngineeringIntent` layer: Facts → Intent → EngineeringBar.",
            "",
            f"- Intents resolved: **{len(result.get('intents') or [])}**",
            f"- Role changes vs R.1 hypothesis: **{role.get('changed_count')}**",
            f"- Mean intent confidence: **{conf.get('mean')}**",
            f"- Production steel: **{bbs.get('steel_weight_kg')} kg**",
            "",
            "## 2. Root Cause Analysis",
            "",
            "R.1 annotation classification ranked MAIN by quantity then diameter, "
            "allowing high-count small bars (e.g. `8Y8`) to outrank true mains "
            "(`3Y20`). Extent was hard-coded as `FULL_SPAN` in L2 export.",
            "",
            "## 3. Engineering Intent Architecture",
            "",
            "```",
            "Engineering Facts (annotations + geometry + relationships)",
            "    -> EngineeringRoleResolver",
            "    -> EngineeringDiameterResolver",
            "    -> EngineeringExtentResolver",
            "    -> Consistency + Confidence",
            "    -> EngineeringIntent",
            "    -> EngineeringBarBuilder",
            "    -> R.1.2B Consolidation",
            "```",
            "",
            "## 4. Role Resolution Results",
            "",
            f"- Changed roles: {role.get('changed_count')}",
            f"- Unchanged: {role.get('unchanged_count')}",
            "",
            "## 5. Diameter Resolution Results",
            "",
            "Diameters resolved from label parse + field agreement + neighbour mode "
            "(not nearest-text).",
            "",
            "## 6. Reinforcement Extent Results",
            "",
            f"- Extent histogram: `{ext.get('extent_histogram')}`",
            "",
            "## 7. Engineering Consistency Validation",
            "",
            f"- Flags: {(result.get('consistency') or {}).get('flag_count')}",
            f"- Histogram: `{(result.get('consistency') or {}).get('flag_histogram')}`",
            "",
            "## 8. BBS & Estimator Comparison",
            "",
            f"- BBS roles: `{bbs.get('role_counts')}`",
            f"- Extents: `{bbs.get('extent_counts')}`",
            f"- Estimator steel accuracy: {est.get('steel_accuracy_pct')}",
            f"- Role balance: `{est.get('role_balance')}`",
            "",
            "## 9. Regression Results",
            "",
            f"- No regression: {reg.get('no_regression')}",
            f"- Summary: {reg.get('summary')}",
            "",
            "## 10. Remaining Engineering Interpretation Gaps",
            "",
            "- Stirrup zone spacing / multi-zone interpretation (R.1.2D).",
            "- Fine-grained curtailment lengths vs estimator cut lengths.",
            "- Side-face detection still depth-heuristic where mid-zone evidence is weak.",
            "",
            "## 11. Exported Artefacts",
            "",
        ]
        for name in (
            "engineering_intents.json",
            "engineering_role_resolution.json",
            "engineering_diameter_resolution.json",
            "engineering_extent_resolution.json",
            "engineering_intent_confidence.json",
            "engineering_consistency_validation.json",
            "engineeringbar_intent_mapping.json",
            "bbs_intent_validation.json",
            "estimator_comparison_metrics.json",
            "benchmark_regression_intent.json",
            "engineering_intent_resolution_report.md",
        ):
            lines.append(f"- `{self.OUT_DIR_NAME}/{name}`")
        lines.extend(["", "## 12. Recommendation", ""])
        if rec == "A":
            lines.append(
                "**Recommendation A** — Ready for Phase R.1.2D — "
                "Stirrup Zone & Reinforcement Extent Interpretation Engine"
            )
        else:
            lines.append(
                "**Recommendation B** — Additional Engineering Intent improvements required."
            )
        lines.extend(["", "---", "*Phase R.1.2C | MODEL_VERSION 8.3.2*", ""])
        return "\n".join(lines)
