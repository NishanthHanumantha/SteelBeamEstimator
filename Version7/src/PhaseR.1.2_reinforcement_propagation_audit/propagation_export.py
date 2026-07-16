"""Export propagation audit JSON artefacts."""
from __future__ import annotations
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List


def _save(out: pathlib.Path, name: str, data: Any) -> pathlib.Path:
    p = out / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


class PropagationExport:

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def write_all(
        self,
        matrix: List[Dict[str, Any]],
        adapter_trace: Dict[str, Any],
        eng_trace: Dict[str, Any],
        steel_trace: Dict[str, Any],
        bbs_trace: Dict[str, Any],
        beam_summary_trace: Dict[str, Any],
        missing_report: Dict[str, Any],
        root_cause_report: Dict[str, Any],
        statistics: Dict[str, Any],
        validation_results: List,
        full_report: Dict[str, Any],
    ) -> Dict[str, str]:
        ts = datetime.utcnow().isoformat()
        paths: Dict[str, str] = {}
        meta = {"generated": ts, "phase": "R.1.2", "model_version": "7.3.2"}

        exports = {
            "beam_propagation_matrix.json": {"beams": matrix, **meta},
            "adapter_trace.json": {**adapter_trace, **meta},
            "engineering_bar_trace.json": {**eng_trace, **meta},
            "steel_weight_trace.json": {**steel_trace, **meta},
            "bbs_trace.json": {**bbs_trace, **meta},
            "beam_summary_trace.json": {**beam_summary_trace, **meta},
            "missing_bar_report.json": {**missing_report, **meta},
            "root_cause_report.json": {**root_cause_report, **meta},
            "propagation_statistics.json": {**statistics, **meta},
            "propagation_validation.json": {
                **meta,
                "validation_score": full_report.get("validation_score"),
                "all_pass": full_report.get("all_pass"),
                "rules": full_report.get("validation_rules"),
            },
            "reinforcement_propagation_report.json": {**full_report, **meta},
        }

        for name, data in exports.items():
            p = _save(self._out, name, data)
            key = name.replace(".json", "").replace("_", " ").strip()
            paths[name.replace(".json", "")] = str(p)

        return paths
