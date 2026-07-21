"""
Load R.1.4 + R.1.5 JSON artefacts only.
MODEL_VERSION: 8.8.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

MODEL_VERSION = "8.8.0"


def _read(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class InputLoader:
    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root)
        self.r14 = self.v8 / "data" / "output" / "PhaseR1_4_production_accuracy_benchmark"
        self.r15 = self.v8 / "data" / "output" / "PhaseR1_5_engineering_error_intelligence"

    def load(self) -> Dict[str, Any]:
        details = _read(self.r15 / "engineering_issue_details.json") or {}
        issues = details.get("issues") or []
        if not issues:
            summary = _read(self.r15 / "engineering_issue_summary.json") or {}
            issues = summary.get("issues") or []

        return {
            "issues": issues,
            "rankings": _read(self.r15 / "engineering_issue_rankings.json") or {},
            "backlog": _read(self.r15 / "engineering_improvement_backlog.json") or {},
            "recommendations": _read(self.r15 / "engineering_recommendations.json") or {},
            "issue_summary": _read(self.r15 / "engineering_issue_summary.json") or {},
            "r14": {
                "official_model": _read(self.r14 / "official_workbook_model.json") or {},
                "production_snapshot_meta": {
                    k: (_read(self.r14 / "production_snapshot.json") or {}).get(k)
                    for k in (
                        "intent_count", "detail_count", "piece_count",
                        "engineering_bar_count", "beam_count", "steel_summary",
                    )
                },
                "kpis": _read(self.r14 / "production_kpis.json") or {},
                "diagnostics": _read(self.r14 / "production_error_diagnostics.json") or {},
                "root_cause": _read(self.r14 / "root_cause_analysis.json") or {},
            },
            "sources": {
                "r14": str(self.r14),
                "r15": str(self.r15),
            },
        }
