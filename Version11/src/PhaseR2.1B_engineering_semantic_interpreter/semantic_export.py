"""
semantic_export.py — JSON export for Phase R.2.1B artefacts.
MODEL_VERSION: 7.11.0

Exports:
  engineering_semantic_objects.json
  semantic_statistics.json
  semantic_validation.json
  semantic_role_distribution.json
  semantic_modifier_distribution.json
  semantic_meaning_distribution.json
  semantic_placement_distribution.json
  semantic_summary.json
  engineering_semantic_report.json
  engineering_semantic_report.md
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List

from .semantic_models import EngineeringSemanticObject


def _eso_to_dict(e: EngineeringSemanticObject) -> Dict[str, Any]:
    return dataclasses.asdict(e)


class SemanticExport:

    MODEL_VERSION = "7.11.0"

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        esos_by_beam: Dict[str, List[EngineeringSemanticObject]],
        statistics: Dict[str, Any],
        validation: Dict[str, Any],
        report_md: str,
        production_result: Dict[str, Any],
    ) -> List[pathlib.Path]:
        exported = []

        all_esos = [e for elist in esos_by_beam.values() for e in elist]
        eso_dicts = [_eso_to_dict(e) for e in all_esos]
        by_beam_dicts = {
            bid: [_eso_to_dict(e) for e in elist]
            for bid, elist in esos_by_beam.items()
        }

        exported.append(self._write(
            "engineering_semantic_objects.json",
            {
                "model_version": self.MODEL_VERSION,
                "phase": "R.2.1B",
                "generated": datetime.utcnow().isoformat(),
                "total_objects": len(all_esos),
                "by_beam": by_beam_dicts,
            }
        ))

        exported.append(self._write(
            "semantic_statistics.json",
            {"model_version": self.MODEL_VERSION, **statistics},
        ))

        exported.append(self._write(
            "semantic_validation.json",
            {"model_version": self.MODEL_VERSION, **validation},
        ))

        exported.append(self._write(
            "semantic_role_distribution.json",
            {
                "model_version": self.MODEL_VERSION,
                "role_distribution": statistics.get("role_distribution", {}),
            }
        ))

        exported.append(self._write(
            "semantic_modifier_distribution.json",
            {
                "model_version": self.MODEL_VERSION,
                "modifier_distribution": statistics.get("modifier_distribution", {}),
            }
        ))

        exported.append(self._write(
            "semantic_meaning_distribution.json",
            {
                "model_version": self.MODEL_VERSION,
                "meaning_distribution": statistics.get("meaning_distribution", {}),
            }
        ))

        exported.append(self._write(
            "semantic_placement_distribution.json",
            {
                "model_version": self.MODEL_VERSION,
                "placement_distribution": statistics.get("placement_distribution", {}),
            }
        ))

        exported.append(self._write(
            "semantic_summary.json",
            {
                "model_version": self.MODEL_VERSION,
                "phase": "R.2.1B",
                "generated": datetime.utcnow().isoformat(),
                "statistics_summary": {
                    k: v for k, v in statistics.items()
                    if isinstance(v, (int, float, str))
                },
                "validation_summary": validation.get("summary"),
                "all_rules_pass": validation.get("all_pass"),
                "production_result": production_result,
            }
        ))

        exported.append(self._write(
            "engineering_semantic_report.json",
            {
                "model_version": self.MODEL_VERSION,
                "phase": "R.2.1B",
                "statistics": statistics,
                "validation": validation,
                "production": production_result,
            }
        ))

        # Markdown
        md_path = self._out / "engineering_semantic_report.md"
        md_path.write_text(report_md, encoding="utf-8")
        exported.append(md_path)

        return exported

    def _write(self, filename: str, data: Any) -> pathlib.Path:
        path = self._out / filename
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path
