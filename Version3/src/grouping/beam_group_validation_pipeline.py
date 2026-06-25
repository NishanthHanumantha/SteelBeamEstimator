"""Phase D.3.1 — beam group confidence validation pipeline."""

import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.config.input_paths import InputPaths
from src.config.output_paths import OutputPaths
from src.grouping.beam_group_confidence import BeamGroupConfidenceScorer
from src.grouping.beam_group_debug_exporter_v2 import BeamGroupDebugExporterV2
from src.grouping.beam_group_validator_v2 import BeamGroupValidatorV2
from src.framing.beam_geometry import beam_mark_sort_key


class BeamGroupValidationPipeline:
    """Read-only confidence audit for Phase D.3 beam groups."""

    def __init__(self, input_paths: InputPaths, output_paths: OutputPaths) -> None:
        self._inputs = input_paths
        self._outputs = output_paths
        self._d3 = output_paths.phase_d3_dir

    def run(self) -> Dict[str, Any]:
        beam_groups = self._read_json(self._d3 / "beam_groups.json")
        shared = self._read_json(self._d3 / "shared_annotations.json")
        expanded = self._read_json(self._d3 / "expanded_group_annotations.json")

        sketches = self._read_json(self._inputs.beam_sketches)
        headers = self._read_json(self._inputs.header_occurrences)

        confidence = BeamGroupConfidenceScorer().score_all(
            beam_groups, sketches, headers, shared, expanded
        )
        validation = BeamGroupValidatorV2().validate(confidence)
        report = self._build_report(confidence, validation)

        self._outputs.phase_d31_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._outputs.beam_group_confidence, confidence)
        self._write_json(self._outputs.beam_group_validation_v2, validation)
        self._write_text(self._outputs.beam_group_validation_report_txt, report)

        BeamGroupDebugExporterV2().export(
            beam_groups, confidence, self._outputs.beam_group_validation_debug_dxf
        )

        logger.info(
            "Phase D.3.1 complete — status={}, parser_ready={}",
            validation["status"],
            validation["parser_ready"],
        )
        return {
            "confidence": confidence,
            "validation": validation,
            "report": report,
        }

    def _build_report(
        self,
        confidence: List[dict[str, Any]],
        validation: Dict[str, Any],
    ) -> str:
        lines = [
            "======================================================================",
            "Phase D.3.1 — Beam Group Confidence & Validation Report",
            "======================================================================",
            "",
            f"Total groups: {validation['total_groups']}",
            f"HIGH: {validation['high_confidence_count']}",
            f"MEDIUM: {validation['medium_confidence_count']}",
            f"LOW: {validation['low_confidence_count']}",
            f"INVALID: {validation['invalid_group_count']}",
            f"Validation status: {validation['status']}",
            f"Parser ready: {validation['parser_ready']}",
            "",
        ]

        if validation.get("recommended_corrections"):
            lines.append("Recommended corrections:")
            for item in validation["recommended_corrections"]:
                lines.append(f"  - {item}")
            lines.append("")

        sorted_results = sorted(
            confidence, key=lambda r: beam_mark_sort_key(r["members"][0])
        )
        for result in sorted_results:
            lines.extend(
                [
                    "--------------------------------------------------",
                    result["group_id"],
                    f"Members: {', '.join(result['members'])}",
                    f"Confidence: {result['confidence_score']} {result['confidence']}",
                    "Rule scores:",
                ]
            )
            for rule, score in result["rule_scores"].items():
                lines.append(f"  {rule}: {score}")
            if result.get("reasons"):
                lines.append("Reasons:")
                for reason in result["reasons"]:
                    lines.append(f"  - {reason}")
            if result.get("warnings"):
                lines.append("Warnings:")
                for warning in result["warnings"]:
                    lines.append(f"  - {warning}")
            lines.append(f"Recommendation: {result.get('recommendation', 'KEEP')}")
            lines.append("")

        lines.append("Assumptions:")
        lines.append("  - Read-only audit; Phase D.3 outputs unchanged")
        lines.append("  - Confidence from 7 weighted engineering signals (0–100)")
        lines.append("")
        return "\n".join(lines)

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def _write_json(self, path: Path, data: Any) -> None:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        logger.info("Wrote {}", path)

    def _write_text(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        logger.info("Wrote {}", path)
