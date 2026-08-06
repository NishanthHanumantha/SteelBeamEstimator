"""
Load R.1.4 benchmark artefacts (JSON only).
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engineering_issue_model import RawFinding

MODEL_VERSION = "8.7.0"


def _read(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class BenchmarkInputLoader:
    """Consume R.1.4 outputs only — no Excel / DXF."""

    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root)
        self.r14 = self.v8 / "data" / "output" / "PhaseR1_4_production_accuracy_benchmark"

    def load(self) -> Dict[str, Any]:
        diagnostics = _read(self.r14 / "production_error_diagnostics.json") or {}
        root_cause = _read(self.r14 / "root_cause_analysis.json") or {}
        kpis = _read(self.r14 / "production_kpis.json") or _read(self.r14 / "benchmark_kpis.json") or {}
        official = (
            _read(self.r14 / "official_workbook_model.json")
            or _read(self.r14 / "official_engineering_model.json")
            or {}
        )
        production = _read(self.r14 / "production_snapshot.json") or {}
        steel = _read(self.r14 / "steel_accuracy.json") or {}
        beam = _read(self.r14 / "beam_accuracy.json") or {}
        reinf = _read(self.r14 / "reinforcement_accuracy.json") or {}
        scorecard = _read(self.r14 / "production_scorecard.json") or (kpis.get("scorecard") or {})

        # Assemble comparison_results from available accuracy files
        comparison = {
            "beam_accuracy": beam,
            "reinforcement_accuracy": reinf,
            "steel_accuracy": steel,
            "bbs_accuracy": _read(self.r14 / "bbs_accuracy.json") or {},
            "workbook_accuracy": _read(self.r14 / "workbook_accuracy.json") or {},
            "piece_accuracy": _read(self.r14 / "piece_accuracy.json") or {},
            "engineeringbar_accuracy": _read(self.r14 / "engineeringbar_accuracy.json") or {},
        }

        findings = self._merge_findings(diagnostics, root_cause)
        official_kg = float(
            steel.get("official_total_kg")
            or (official.get("steel_summary") or {}).get("total_kg")
            or 0.0
        )
        prod_kg = float(
            steel.get("production_total_kg")
            or (production.get("steel_summary") or {}).get("total_kg")
            or 0.0
        )
        overall = float(
            (kpis.get("kpis") or {}).get("KPI_12_overall_production_accuracy")
            or scorecard.get("overall_pct", 0) / 100.0
            or root_cause.get("overall_production_accuracy")
            or 0.0
        )
        if overall > 1.0:
            overall = overall / 100.0

        return {
            "sources": {
                "r14_dir": str(self.r14),
                "diagnostics": str(self.r14 / "production_error_diagnostics.json"),
                "root_cause": str(self.r14 / "root_cause_analysis.json"),
                "kpis": str(self.r14 / "production_kpis.json"),
            },
            "findings": findings,
            "diagnostics": diagnostics,
            "root_cause": root_cause,
            "kpis": kpis,
            "scorecard": scorecard,
            "official_model": official,
            "production_snapshot": {
                "intent_count": production.get("intent_count"),
                "detail_count": production.get("detail_count"),
                "piece_count": production.get("piece_count"),
                "engineering_bar_count": production.get("engineering_bar_count"),
                "beam_count": production.get("beam_count"),
                "steel_summary": production.get("steel_summary"),
            },
            "comparison": comparison,
            "official_total_kg": official_kg,
            "production_total_kg": prod_kg,
            "steel_gap_kg": round(official_kg - prod_kg, 3),
            "overall_accuracy": overall,
            "kpi_loss": round(max(0.0, 1.0 - overall), 4),
        }

    def _merge_findings(self, diagnostics: Dict[str, Any], root_cause: Dict[str, Any]) -> List[RawFinding]:
        rc_by_key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for f in root_cause.get("findings") or []:
            key = (str(f.get("error_type") or ""), str(f.get("entity") or ""), str(f.get("message") or ""))
            rc_by_key[key] = f

        findings: List[RawFinding] = []
        for idx, d in enumerate(diagnostics.get("diagnostics") or [], start=1):
            key = (str(d.get("error_type") or ""), str(d.get("entity") or ""), str(d.get("message") or ""))
            rc = rc_by_key.get(key) or {}
            findings.append(RawFinding(
                finding_id=f"F-{idx:04d}",
                error_type=str(d.get("error_type") or ""),
                entity=str(d.get("entity") or ""),
                field=str(d.get("field") or ""),
                message=str(d.get("message") or ""),
                originating_phase=str(rc.get("originating_phase") or ""),
                confidence=float(rc.get("confidence") or 0.5),
                suggested_fix=str(rc.get("suggested_engineering_fix") or ""),
            ))
        return findings
