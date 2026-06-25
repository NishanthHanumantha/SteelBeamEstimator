"""Phase D.3.2 — detail region detection pipeline orchestration."""

import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.config.input_paths import InputPaths
from src.config.output_paths import OutputPaths
from src.detail_regions.beam_group_from_region import BeamGroupFromRegion
from src.detail_regions.detail_region_builder import DetailRegionBuilder
from src.detail_regions.detail_region_debug_exporter import DetailRegionDebugExporter
from src.detail_regions.detail_region_detector import DetailRegionDetector
from src.detail_regions.detail_region_refiner import DetailRegionRefiner
from src.detail_regions.detail_region_validator import DetailRegionValidator
from src.framing.beam_geometry import beam_mark_sort_key


class DetailRegionPipeline:
    """Run Phase D.3.2 detail region detection and beam group refinement."""

    def __init__(self, input_paths: InputPaths, output_paths: OutputPaths) -> None:
        self._inputs = input_paths
        self._outputs = output_paths

    def run(self) -> Dict[str, Any]:
        beam_cells = self._read_json(self._inputs.beam_cells)
        sketches = self._read_json(self._inputs.beam_sketches)
        occurrences = self._read_json(self._inputs.header_occurrences)
        engineering = self._read_json(self._inputs.engineering_annotations_final)

        expanded_path = self._outputs.expanded_group_annotations
        expanded: List[dict[str, Any]] = []
        if expanded_path.exists():
            expanded = self._read_json(expanded_path)

        all_marks = [str(c["beam_mark"]).upper() for c in beam_cells]

        regions = DetailRegionDetector().detect(sketches, beam_cells, occurrences)
        regions = DetailRegionRefiner().refine(
            regions, occurrences, beam_cells, sketches
        )
        regions = self._renumber_regions(regions)
        regions = DetailRegionBuilder().enrich(regions, engineering, occurrences)

        region_results, validation = DetailRegionValidator().validate_and_score(
            regions, all_marks, expanded
        )
        beam_groups = BeamGroupFromRegion().derive(regions, beam_cells)

        summary = self._build_summary(regions, beam_groups, validation)
        report = self._build_report(summary, regions, validation)

        self._outputs.phase_d32_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._outputs.detail_regions, self._serialize_regions(regions))
        self._write_json(self._outputs.beam_groups_refined, beam_groups)
        self._write_json(self._outputs.detail_region_validation, validation)
        self._write_json(self._outputs.detail_region_summary, summary)
        self._write_text(self._outputs.detail_region_report_txt, report)

        DetailRegionDebugExporter().export(
            regions, region_results, self._outputs.detail_region_debug_dxf
        )

        logger.info("Phase D.3.2 complete — validation {}", validation["status"])
        return {
            "regions": regions,
            "beam_groups": beam_groups,
            "validation": validation,
            "summary": summary,
            "report": report,
        }

    def _renumber_regions(self, regions: List[dict[str, Any]]) -> List[dict[str, Any]]:
        sorted_regions = sorted(
            regions,
            key=lambda r: beam_mark_sort_key(r["beam_titles"][0]),
        )
        for index, region in enumerate(sorted_regions, start=1):
            region["region_id"] = f"DETAIL_REGION_{index:03d}"
        return sorted_regions

    def _serialize_regions(self, regions: List[dict[str, Any]]) -> List[dict[str, Any]]:
        return [
            {
                "region_id": r["region_id"],
                "bbox": r["bbox"],
                "beam_titles": r["beam_titles"],
                "member_sketches": r.get("member_sketches", []),
                "member_annotations": r.get("member_annotations", []),
                "confidence": r.get("confidence"),
                "continuous": r.get("continuous"),
                "confidence_label": r.get("confidence_label"),
                "is_multi_beam": r.get("is_multi_beam", len(r["beam_titles"]) > 1),
                "sketch_cluster_count": r.get("sketch_cluster_count"),
            }
            for r in regions
        ]

    def _build_summary(
        self,
        regions: List[dict[str, Any]],
        beam_groups: List[dict[str, Any]],
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        multi = [r for r in regions if len(r.get("beam_titles", [])) > 1]
        return {
            "total_detail_regions": len(regions),
            "single_beam_region_count": validation["single_beam_region_count"],
            "multi_beam_region_count": validation["multi_beam_region_count"],
            "invalid_region_count": validation["invalid_region_count"],
            "beam_groups_generated": len(beam_groups),
            "validation_status": validation["status"],
            "parser_ready": validation["parser_ready"],
            "multi_beam_regions": [
                {
                    "region_id": r["region_id"],
                    "beam_titles": r["beam_titles"],
                    "confidence": r.get("confidence"),
                    "confidence_label": r.get("confidence_label"),
                }
                for r in multi
            ],
            "recommendations": self._recommendations(validation),
        }

    def _recommendations(self, validation: Dict[str, Any]) -> List[str]:
        recs: List[str] = []
        if validation["invalid_region_count"]:
            recs.append(
                "Review invalid detail regions before parser handoff — "
                "disconnected sketch clusters without continuous reinforcement."
            )
        if validation["shared_annotation_issues"]:
            recs.append(
                "Re-run shared annotation expansion scoped to detail regions only."
            )
        if not validation["parser_ready"]:
            recs.append("Do not begin Phase D.4 until detail regions pass validation.")
        else:
            recs.append("Detail regions validated — await engineering review before Phase D.4.")
        return recs

    def _build_report(
        self,
        summary: Dict[str, Any],
        regions: List[dict[str, Any]],
        validation: Dict[str, Any],
    ) -> str:
        lines = [
            "Phase D.3.2 — Detail Region Detection & Group Refinement",
            "=" * 50,
            f"Total detail regions: {summary['total_detail_regions']}",
            f"Single-beam regions: {summary['single_beam_region_count']}",
            f"Multi-beam regions: {summary['multi_beam_region_count']}",
            f"Invalid regions: {summary['invalid_region_count']}",
            f"Beam groups generated: {summary['beam_groups_generated']}",
            f"Validation: {summary['validation_status']}",
            f"Parser ready: {'YES' if summary['parser_ready'] else 'NO'}",
            "",
            "Detail regions:",
        ]
        for region in sorted(regions, key=lambda r: r["region_id"]):
            titles = ", ".join(region["beam_titles"])
            lines.append(
                f"  {region['region_id']}: {titles} "
                f"(confidence={region.get('confidence')} "
                f"{region.get('confidence_label', '')}, "
                f"continuous={region.get('continuous')})"
            )
        if validation.get("warnings"):
            lines.extend(["", "Warnings:"])
            for warning in validation["warnings"]:
                lines.append(f"  - {warning}")
        if summary.get("recommendations"):
            lines.extend(["", "Recommendations:"])
            for rec in summary["recommendations"]:
                lines.append(f"  - {rec}")
        lines.append("")
        lines.append("Stop after D.3.2 — do not begin Phase D.4 without review.")
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
