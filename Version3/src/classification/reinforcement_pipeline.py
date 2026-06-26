"""Phase D.4.1 — reinforcement classification pipeline."""

import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.classification.reinforcement_classifier import ReinforcementClassifier
from src.classification.reinforcement_debug_exporter import ReinforcementDebugExporter
from src.classification.reinforcement_validator import ReinforcementValidator
from src.config.output_paths import OutputPaths
from src.framing.beam_geometry import beam_mark_sort_key


class ReinforcementPipeline:
    """Run Phase D.4.1 reinforcement classification on D.4 engineering objects."""

    def __init__(self, output_paths: OutputPaths) -> None:
        self._outputs = output_paths

    def run(self) -> Dict[str, Any]:
        objects = self._read_json(self._outputs.engineering_objects_for_classification())
        classified = ReinforcementClassifier().classify_all(objects)
        validation = ReinforcementValidator().validate(objects, classified)
        summary = self._build_summary(classified, validation)
        report = self._build_report(summary, validation, classified)

        self._outputs.phase_d41_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._outputs.reinforcement_classification, classified)
        self._write_json(self._outputs.reinforcement_summary, summary)
        self._write_json(self._outputs.reinforcement_validation, validation)
        self._write_text(self._outputs.reinforcement_report_txt, report)

        ReinforcementDebugExporter().export(
            classified, self._outputs.reinforcement_debug_dxf
        )

        logger.info("Phase D.4.1 complete — validation {}", validation["status"])
        return {
            "classified": classified,
            "validation": validation,
            "summary": summary,
            "report": report,
        }

    def _build_summary(
        self,
        classified: List[dict[str, Any]],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        by_category: Dict[str, int] = {}
        for entry in classified:
            cat = entry.get("estimator_category", "UNCLASSIFIED")
            by_category[cat] = by_category.get(cat, 0) + 1

        beam_samples = self._beam_samples(classified, ["B1", "B8", "B9", "B10", "B14"])
        return {
            "classified_count": len(classified),
            "by_estimator_category": by_category,
            "longitudinal_bar_count": validation["longitudinal_bar_count"],
            "stirrup_count": validation["stirrup_count"],
            "anchorage_count": validation["anchorage_count"],
            "sfr_count": validation["sfr_count"],
            "validation_status": validation["status"],
            "parser_ready": validation["parser_ready"],
            "beam_samples": beam_samples,
        }

    def _beam_samples(
        self,
        classified: List[dict[str, Any]],
        beams: List[str],
    ) -> Dict[str, List[dict[str, Any]]]:
        samples: Dict[str, List[dict[str, Any]]] = {}
        beam_set = set(beams)
        for entry in classified:
            mark = str(entry.get("resolved_beam_mark", "")).upper()
            if mark in beam_set:
                samples.setdefault(mark, []).append(
                    {
                        "object_id": entry.get("object_id"),
                        "clean_text": entry.get("clean_text"),
                        "engineering_type": entry.get("engineering_type"),
                        "estimator_category": entry.get("estimator_category"),
                        "position": entry.get("position"),
                        "continuity": entry.get("continuity"),
                        "quantity": entry.get("quantity"),
                        "diameter_mm": entry.get("diameter_mm"),
                    }
                )
        for mark in sorted(samples.keys(), key=beam_mark_sort_key):
            samples[mark] = samples[mark]
        return samples

    def _build_report(
        self,
        summary: Dict[str, Any],
        validation: Dict[str, Any],
        classified: List[dict[str, Any]],
    ) -> str:
        lines = [
            "Phase D.4.1 — Reinforcement Classification",
            "=" * 50,
            f"Classified objects: {summary['classified_count']}",
            f"Longitudinal bars: {summary['longitudinal_bar_count']}",
            f"Stirrups: {summary['stirrup_count']}",
            f"Anchorage: {summary['anchorage_count']}",
            f"SFR: {summary['sfr_count']}",
            f"Validation: {summary['validation_status']}",
            "",
            "Estimator categories:",
        ]
        for cat, count in sorted(summary.get("by_estimator_category", {}).items()):
            lines.append(f"  {cat}: {count}")
        if validation.get("warnings"):
            lines.extend(["", "Warnings:"])
            for w in validation["warnings"]:
                lines.append(f"  - {w}")
        lines.extend(["", "Sample beams:"])
        for mark, entries in summary.get("beam_samples", {}).items():
            lines.append(f"  {mark}: {len(entries)} object(s)")
        lines.append("")
        lines.append("Stop after D.4.1 — do not begin Phase D.5.")
        return "\n".join(lines)

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"Required input not found: {path}")
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, data: Any) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def _write_text(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
