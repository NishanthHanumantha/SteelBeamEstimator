"""
JSON exporters for Phase R.1.5 artefacts.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from engineering_issue_model import EngineeringIssue

MODEL_VERSION = "8.7.0"


class JsonExporter:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, payload: Dict[str, Any]) -> Dict[str, str]:
        issues: List[EngineeringIssue] = payload["issues"]
        paths: Dict[str, str] = {}

        def dump(name: str, data: Any) -> None:
            p = self.output_dir / name
            p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[name] = str(p)

        dump("engineering_issue_summary.json", {
            "model_version": MODEL_VERSION,
            "issue_count": len(issues),
            "finding_count": payload.get("finding_count"),
            "overall_accuracy": payload.get("overall_accuracy"),
            "steel_gap_kg": payload.get("steel_gap_kg"),
            "issues": [
                {
                    "issue_id": i.issue_id,
                    "category": i.category,
                    "subcategory": i.subcategory,
                    "frequency": i.frequency,
                    "severity": i.severity,
                    "engineering_impact": i.engineering_impact,
                    "steel_impact_kg": i.steel_impact_kg,
                    "confidence": i.confidence,
                    "originating_phase": i.originating_phase,
                    "priority": i.priority,
                    "expected_accuracy_gain": i.expected_accuracy_gain,
                }
                for i in issues
            ],
        })
        dump("engineering_issue_details.json", {
            "model_version": MODEL_VERSION,
            "issues": [i.to_dict() for i in issues],
        })
        dump("engineering_issue_rankings.json", payload["rankings"])
        dump("engineering_recommendations.json", {
            "model_version": MODEL_VERSION,
            "recommendations": [
                {
                    "issue_id": i.issue_id,
                    "category": i.category,
                    "recommended_fix": i.recommended_fix,
                    "recommended_phase": i.recommended_phase,
                    "expected_accuracy_gain": i.expected_accuracy_gain,
                    "priority": i.priority,
                    "confidence": i.confidence,
                    "root_cause": i.root_cause,
                }
                for i in issues
            ],
        })
        dump("engineering_improvement_backlog.json", payload["backlog"])
        dump("engineering_trends.json", payload["trends"])
        dump("phase_attribution_summary.json", payload["phase_summary"])
        dump("severity_summary.json", payload["severity_summary"])
        dump("frequency_summary.json", payload["frequency"])
        dump("engineering_error_dashboard.json", payload["dashboard"])
        dump("benchmark_regression.json", payload["regression"])
        dump("validation_report.json", payload["validation"])
        return paths
