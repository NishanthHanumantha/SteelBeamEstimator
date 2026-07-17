"""
Stirrup Export — Phase SI.0 MODULE 11

Exports 7 JSON artefacts and the updated beam_reinforcement_models.json.
"""
import json
import pathlib
from typing import Any, Dict, List


def _serialise(obj: Any) -> Any:
    if hasattr(obj, "value"):  # Enum
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialise(v) for k, v in obj.__dict__.items()}
    if isinstance(obj, list):
        return [_serialise(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    return obj


def _dump(data: Any, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_serialise(data), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class StirrupRecoveryExport:

    def __init__(self, output_dir: pathlib.Path) -> None:
        self.out = output_dir

    def export_all(
        self,
        report: Dict[str, Any],
        statistics: Dict[str, Any],
        beam_results: list,
        updated_models: list,
        candidates: list,
        l2_wrapper: Dict[str, Any],
    ) -> Dict[str, pathlib.Path]:
        paths: Dict[str, pathlib.Path] = {}

        # 1. recovered_stirrups.json
        paths["recovered_stirrups"] = self._write(
            "recovered_stirrups.json",
            [r for r in _serialise(beam_results) if r.get("decision") == "RECOVERED"],
        )

        # 2. recovery_report.json
        paths["recovery_report"] = self._write("recovery_report.json", report)

        # 3. quality_validation.json
        paths["quality_validation"] = self._write(
            "quality_validation.json",
            report.get("validation", {}),
        )

        # 4. recovery_statistics.json
        paths["recovery_statistics"] = self._write("recovery_statistics.json", statistics)

        # 5. candidate_report.json
        paths["candidate_report"] = self._write(
            "candidate_report.json",
            _serialise(candidates),
        )

        # 6. beam_updates.json
        paths["beam_updates"] = self._write(
            "beam_updates.json",
            [r for r in _serialise(beam_results) if r.get("original_label") != r.get("recovered_label")],
        )

        # 7. phase_si0_summary.json
        paths["phase_si0_summary"] = self._write(
            "phase_si0_summary.json",
            {
                "phase": "SI.0",
                "model_version": "6.6.2",
                "summary": report.get("executive_summary", {}),
                "statistics": statistics,
            },
        )

        # 8. Updated beam_reinforcement_models.json (the critical output)
        updated_wrapper = dict(l2_wrapper)
        updated_wrapper["models"] = updated_models
        updated_wrapper["si0_applied"] = True
        updated_wrapper["si0_model_version"] = "6.6.2"
        paths["beam_reinforcement_models"] = self._write(
            "beam_reinforcement_models.json",
            updated_wrapper,
        )

        return paths

    def _write(self, filename: str, data: Any) -> pathlib.Path:
        p = self.out / filename
        _dump(data, p)
        return p
