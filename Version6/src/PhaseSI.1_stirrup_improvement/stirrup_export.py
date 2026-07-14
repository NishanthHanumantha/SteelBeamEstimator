"""
Stirrup Export — Phase SI.1 MODULE 10

Exports 6 JSON artefacts to the SI.1 output directory.
"""
import json
import pathlib
from typing import Any, Dict


def _serialise(obj: Any) -> Any:
    if isinstance(obj, pathlib.Path):
        return str(obj)
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialise(v) for k, v in obj.__dict__.items()}
    if hasattr(obj, "value"):  # Enum
        return obj.value
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


class StirrupExport:
    """Exports all Phase SI.1 JSON artefacts."""

    def __init__(self, output_dir: pathlib.Path) -> None:
        self.out = output_dir

    def export_all(
        self,
        full_report: Dict[str, Any],
        statistics: Dict[str, Any],
        beam_results: list,
    ) -> Dict[str, pathlib.Path]:

        paths: Dict[str, pathlib.Path] = {}

        # 1. stirrup_distribution_report.json
        paths["stirrup_distribution_report"] = self._write(
            "stirrup_distribution_report.json",
            full_report["sections"].get("2_engineering_distribution", {}),
        )

        # 2. stirrup_quantity_report.json
        paths["stirrup_quantity_report"] = self._write(
            "stirrup_quantity_report.json",
            full_report["sections"].get("4_quantity_calculations", []),
        )

        # 3. stirrup_bbs_report.json
        paths["stirrup_bbs_report"] = self._write(
            "stirrup_bbs_report.json",
            full_report["sections"].get("5_bbs_summary", {}),
        )

        # 4. stirrup_weight_report.json
        paths["stirrup_weight_report"] = self._write(
            "stirrup_weight_report.json",
            full_report["sections"].get("6_steel_weight_summary", {}),
        )

        # 5. stirrup_statistics.json
        paths["stirrup_statistics"] = self._write(
            "stirrup_statistics.json",
            statistics,
        )

        # 6. stirrup_validation_report.json
        paths["stirrup_validation_report"] = self._write(
            "stirrup_validation_report.json",
            full_report["sections"].get("7_validation_summary", {}),
        )

        # Full report
        paths["stirrup_full_report"] = self._write(
            "stirrup_full_report.json",
            full_report,
        )

        return paths

    def _write(self, filename: str, data: Any) -> pathlib.Path:
        p = self.out / filename
        _dump(data, p)
        return p
