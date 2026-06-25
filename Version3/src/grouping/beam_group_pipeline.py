"""Phase D.3 — beam group detection pipeline orchestration."""

import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.config.input_paths import InputPaths
from src.config.output_paths import OutputPaths
from src.debug.group_annotation_debug_exporter import GroupAnnotationDebugExporter
from src.grouping.beam_group_builder import BeamGroupBuilder
from src.grouping.beam_group_validator import BeamGroupValidator
from src.grouping.beam_group_types import BeamGroup, ExpandedAnnotation, SharedAnnotation
from src.grouping.group_annotation_expander import GroupAnnotationExpander
from src.grouping.group_annotation_owner import GroupAnnotationOwner
from src.grouping.group_annotation_validator import GroupAnnotationValidator
from src.grouping.shared_annotation_detector import SharedAnnotationDetector


class BeamGroupPipeline:
    """Run Phase D.3 beam group detection and shared annotation ownership."""

    def __init__(self, input_paths: InputPaths, output_paths: OutputPaths) -> None:
        self._inputs = input_paths
        self._outputs = output_paths

    def run(self) -> Dict[str, Any]:
        beam_cells = self._read_json(self._inputs.beam_cells)
        sketches = self._read_json(self._inputs.beam_sketches)
        occurrences = self._read_json(self._inputs.header_occurrences)
        sketch_ownership = self._read_json(self._inputs.sketch_ownership)
        engineering = self._read_json(self._inputs.engineering_annotations_final)

        beam_groups = BeamGroupBuilder().build(beam_cells, sketches, occurrences)
        group_validation = BeamGroupValidator().validate(
            beam_groups, [c["beam_mark"] for c in beam_cells]
        )

        shared = SharedAnnotationDetector().detect(engineering, beam_groups)
        ownership = GroupAnnotationOwner().assign(shared)
        expanded = GroupAnnotationExpander().expand(ownership, sketches, sketch_ownership)
        expansion_validation = GroupAnnotationValidator().validate(ownership, expanded)

        summary = self._build_summary(beam_groups, shared, expanded, group_validation, expansion_validation)
        report = self._build_report(summary, beam_groups, shared, expanded)

        self._outputs.phase_d3_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(self._outputs.beam_groups, beam_groups)
        self._write_json(self._outputs.beam_group_summary, summary)
        self._write_json(self._outputs.shared_annotations, shared)
        self._write_json(self._outputs.group_annotation_ownership, ownership)
        self._write_json(self._outputs.expanded_group_annotations, expanded)
        self._write_json(
            self._outputs.beam_group_validation,
            {
                "beam_groups": group_validation,
                "expansion": expansion_validation,
                "overall_status": self._overall_status(group_validation, expansion_validation),
            },
        )
        self._write_text(self._outputs.beam_group_report_txt, report)

        GroupAnnotationDebugExporter().export(
            beam_groups, shared, expanded, self._outputs.beam_group_debug_dxf
        )

        logger.info("Phase D.3 complete — overall status {}", summary["overall_status"])
        return {
            "beam_groups": beam_groups,
            "shared_annotations": shared,
            "ownership": ownership,
            "expanded": expanded,
            "summary": summary,
            "group_validation": group_validation,
            "expansion_validation": expansion_validation,
            "report": report,
        }

    def _build_summary(
        self,
        beam_groups: List[BeamGroup],
        shared: List[SharedAnnotation],
        expanded: List[ExpandedAnnotation],
        group_validation: Dict[str, Any],
        expansion_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        multi = [g for g in beam_groups if g["is_multi_beam"]]
        group_anns = [s for s in shared if s["ownership_mode"] == "GROUP"]
        sfr_expanded = [
            e for e in expanded
            if e.get("expanded_from_group")
            and "SIDE FACE" in str(e.get("clean_text", "")).upper()
        ]
        return {
            "beam_group_count": len(beam_groups),
            "multi_beam_group_count": len(multi),
            "multi_beam_groups": [
                {"beam_group_id": g["beam_group_id"], "members": g["members"]} for g in multi
            ],
            "engineering_annotation_count": len(shared),
            "group_owned_annotation_count": len(group_anns),
            "expanded_annotation_count": len(expanded),
            "group_expansion_count": sum(1 for e in expanded if e.get("expanded_from_group")),
            "sfr_group_expansions": [
                {"beam_mark": e["beam_mark"], "beam_group_id": e["beam_group_id"], "clean_text": e["clean_text"]}
                for e in sfr_expanded
            ],
            "group_validation_status": group_validation["status"],
            "expansion_validation_status": expansion_validation["status"],
            "overall_status": self._overall_status(group_validation, expansion_validation),
        }

    def _overall_status(
        self, group_validation: Dict[str, Any], expansion_validation: Dict[str, Any]
    ) -> str:
        statuses = {group_validation["status"], expansion_validation["status"]}
        if "FAIL" in statuses:
            return "FAIL"
        if "WARN" in statuses:
            return "WARN"
        return "PASS"

    def _build_report(
        self,
        summary: Dict[str, Any],
        beam_groups: List[BeamGroup],
        shared: List[SharedAnnotation],
        expanded: List[ExpandedAnnotation],
    ) -> str:
        lines = [
            "======================================================================",
            "Phase D.3 — Beam Group Detection & Shared Annotation Ownership",
            "======================================================================",
            "",
            f"Beam groups detected: {summary['beam_group_count']}",
            f"Multi-beam groups: {summary['multi_beam_group_count']}",
            f"Group-owned annotations: {summary['group_owned_annotation_count']}",
            f"Expanded annotations: {summary['expanded_annotation_count']}",
            f"Overall validation: {summary['overall_status']}",
            "",
            "Multi-beam groups:",
        ]
        for entry in summary["multi_beam_groups"]:
            lines.append(f"  {entry['beam_group_id']}: {', '.join(entry['members'])}")

        lines.extend(["", "Group-owned annotations:"])
        for ann in shared:
            if ann["ownership_mode"] != "GROUP":
                continue
            lines.append(
                f"  {ann['annotation_id']}: {ann['beam_group_id']} -> "
                f"{', '.join(ann['member_beams'])} | {ann['clean_text'][:50]}"
            )

        lines.extend(["", "SFR expansions:"])
        for entry in summary["sfr_group_expansions"]:
            lines.append(f"  {entry['beam_group_id']} -> {entry['beam_mark']}: {entry['clean_text'][:50]}")

        lines.extend(["", "All beam groups:"])
        for group in beam_groups:
            lines.append(
                f"  {group['beam_group_id']}: {', '.join(group['members'])} "
                f"(multi={group['is_multi_beam']})"
            )

        lines.append("")
        lines.append("Assumptions:")
        lines.append("  - Groups form from adjacent row cells with aligned detail sketch bands")
        lines.append("  - Shared annotations detected by geometry span, duplicate coords, semantics")
        lines.append("  - Version2 outputs used as read-only inputs; no Version2 files modified")
        lines.append("")
        return "\n".join(lines)

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"Missing input: {path}")
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        logger.info("Wrote {}", path)

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        logger.info("Wrote {}", path)
