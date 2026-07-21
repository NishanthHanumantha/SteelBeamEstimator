"""
JSON exporters for Phase R.1.6.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from engineering_rule_model import EngineeringRule

MODEL_VERSION = "8.8.0"


class JsonExporter:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, payload: Dict[str, Any]) -> Dict[str, str]:
        rules: List[EngineeringRule] = payload["rules"]
        paths: Dict[str, str] = {}

        def dump(name: str, data: Any) -> None:
            p = self.output_dir / name
            p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[name] = str(p)

        dump("engineering_rule_library.json", payload["library"])
        dump("engineering_rules.json", {
            "model_version": MODEL_VERSION,
            "rule_count": len(rules),
            "rules": [r.to_dict() for r in rules],
        })
        dump("rule_dependencies.json", payload["dependencies"])
        dump("rule_conflicts.json", payload["conflicts"])
        dump("rule_gap_analysis.json", {
            "model_version": MODEL_VERSION,
            "gaps": [
                {
                    "rule_id": r.rule_id,
                    "rule_family": r.rule_family,
                    "gap_type": r.gap_type,
                    "status": r.status,
                    "originating_issues": list(r.originating_issues),
                }
                for r in rules
            ],
        })
        dump("rule_pattern_analysis.json", payload["patterns"])
        dump("gap_resolution_plan.json", payload["gap_plan"])
        dump("implementation_roadmap.json", payload["roadmap"])
        dump("engineering_rule_traceability.json", payload["traceability"])
        dump("rule_validation.json", payload["validation"])
        dump("rule_recommendations.json", payload["rule_recommendations"])
        dump("benchmark_regression.json", payload["regression"])
        return paths
