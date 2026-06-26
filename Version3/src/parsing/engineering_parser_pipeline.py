"""Phase D.4 — engineering annotation parsing pipeline."""

import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.config.output_paths import OutputPaths
from src.parsing.engineering_parser_debug_exporter import EngineeringParserDebugExporter
from src.parsing.engineering_parser_validator import EngineeringParserValidator
from src.parsing.reinforcement_parser import ReinforcementParser


class EngineeringParserPipeline:
    """Run Phase D.4 engineering annotation parsing from D.3.3 ownership."""

    def __init__(self, output_paths: OutputPaths) -> None:
        self._outputs = output_paths

    def run(self) -> Dict[str, Any]:
        ownership = self._read_json(self._outputs.annotation_ownership_master)
        beam_groups = self._read_json(self._outputs.beam_groups_refined)
        sketches = self._read_json(
            Path("data/input/beam_sketches.json")
        )
        sketch_index = {str(s["sketch_id"]): s for s in sketches}

        parse_result = ReinforcementParser().parse_all(
            ownership, beam_groups, sketch_index
        )
        validation = EngineeringParserValidator().validate(ownership, parse_result)
        summary = self._build_summary(parse_result, validation)
        report = self._build_report(summary, validation, parse_result)

        self._outputs.phase_d4_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(
            self._outputs.engineering_objects,
            parse_result["engineering_objects"],
        )
        self._write_json(
            self._outputs.parsed_longitudinal_bars,
            parse_result["parsed_longitudinal_bars"],
        )
        self._write_json(
            self._outputs.parsed_stirrups_d4,
            parse_result["parsed_stirrups"],
        )
        self._write_json(
            self._outputs.parsed_anchorage_d4,
            parse_result["parsed_anchorage"],
        )
        self._write_json(
            self._outputs.parsed_sfr_d4,
            parse_result["parsed_sfr"],
        )
        self._write_json(self._outputs.engineering_parser_summary, summary)
        self._write_json(self._outputs.engineering_parser_validation, validation)
        self._write_text(self._outputs.engineering_parser_report_txt, report)

        EngineeringParserDebugExporter().export(
            parse_result["engineering_objects"],
            self._outputs.engineering_parser_debug_dxf,
        )

        logger.info("Phase D.4 complete — validation {}", validation["status"])
        return {
            "parse_result": parse_result,
            "validation": validation,
            "summary": summary,
            "report": report,
        }

    def _build_summary(
        self,
        parse_result: Dict[str, List[dict[str, Any]]],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "owned_annotation_count": validation["owned_annotation_count"],
            "engineering_object_count": validation["engineering_object_count"],
            "longitudinal_bar_count": validation["longitudinal_bar_count"],
            "stirrup_count": validation["stirrup_count"],
            "anchorage_count": validation["anchorage_count"],
            "sfr_count": validation["sfr_count"],
            "failed_parse_count": validation["failed_parse_count"],
            "validation_status": validation["status"],
            "parser_ready": validation["parser_ready"],
        }

    def _build_report(
        self,
        summary: Dict[str, Any],
        validation: Dict[str, Any],
        parse_result: Dict[str, List[dict[str, Any]]],
    ) -> str:
        lines = [
            "Phase D.4 — Engineering Annotation Parsing",
            "=" * 50,
            f"Owned annotations: {summary['owned_annotation_count']}",
            f"Engineering objects: {summary['engineering_object_count']}",
            f"Longitudinal bars: {summary['longitudinal_bar_count']}",
            f"Stirrups: {summary['stirrup_count']}",
            f"Anchorage: {summary['anchorage_count']}",
            f"SFR: {summary['sfr_count']}",
            f"Failed parses: {summary['failed_parse_count']}",
            f"Validation: {summary['validation_status']}",
            f"Parser ready: {'YES' if summary['parser_ready'] else 'NO'}",
        ]
        if validation.get("warnings"):
            lines.extend(["", "Warnings:"])
            for w in validation["warnings"]:
                lines.append(f"  - {w}")
        lines.append("")
        lines.append("Stop after D.4 / D.4.1 — do not begin Phase D.5.")
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
