"""Phase D.3.3 — annotation ownership reconciliation pipeline."""

import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from src.config.input_paths import InputPaths
from src.config.output_paths import OutputPaths
from src.framing.beam_geometry import beam_mark_sort_key
from src.ownership.ownership_debug_exporter import OwnershipDebugExporter
from src.ownership.ownership_reconciliation_engine import OwnershipReconciliationEngine
from src.ownership.ownership_validator import OwnershipValidator

DEFAULT_REINFORCEMENT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")


class OwnershipPipeline:
    """Run Phase D.3.3 annotation ownership reconciliation."""

    def __init__(
        self,
        input_paths: InputPaths,
        output_paths: OutputPaths,
        dxf_path: Path | None = None,
    ) -> None:
        self._inputs = input_paths
        self._outputs = output_paths
        self._dxf_path = dxf_path or DEFAULT_REINFORCEMENT_DXF

    def run(self) -> Dict[str, Any]:
        engineering = self._read_json(self._inputs.engineering_dataset_d17f)
        beam_cells = self._read_json(self._inputs.beam_cells)
        detail_regions = self._read_json(self._outputs.detail_regions)
        beam_groups = self._read_json(self._outputs.beam_groups_refined)

        from src.ownership.ownership_geometry import filter_region_sketches_to_cells

        detail_regions = filter_region_sketches_to_cells(
            detail_regions, beam_cells
        )

        dxf_str = str(self._dxf_path) if self._dxf_path.exists() else None
        if dxf_str is None:
            logger.warning("Reinforcement DXF not found — leader matching disabled")

        reconciled = OwnershipReconciliationEngine().reconcile(
            engineering,
            detail_regions,
            beam_groups,
            beam_cells,
            dxf_str,
        )
        validation = OwnershipValidator().validate(
            reconciled["master"], detail_regions
        )

        summary = self._build_summary(reconciled, validation, detail_regions)
        report = self._build_report(summary, reconciled, validation, detail_regions)

        self._outputs.phase_d33_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(
            self._outputs.annotation_ownership_master, reconciled["master"]
        )
        self._write_json(
            self._outputs.annotation_region_mapping, reconciled["region_mapping"]
        )
        self._write_json(
            self._outputs.annotation_sketch_mapping, reconciled["sketch_mapping"]
        )
        self._write_json(
            self._outputs.ownership_confidence, reconciled["confidence"]
        )
        self._write_json(
            self._outputs.ownership_conflicts, reconciled["conflicts"]
        )
        self._write_json(self._outputs.ownership_validation, validation)
        self._write_json(self._outputs.ownership_summary, summary)
        self._write_text(self._outputs.ownership_report_txt, report)

        OwnershipDebugExporter().export(
            reconciled["master"],
            detail_regions,
            self._outputs.ownership_debug_dxf,
        )

        logger.info("Phase D.3.3 complete — validation {}", validation["status"])
        return {
            "reconciled": reconciled,
            "validation": validation,
            "summary": summary,
            "report": report,
        }

    def _build_summary(
        self,
        reconciled: Dict[str, Any],
        validation: Dict[str, Any],
        detail_regions: List[dict[str, Any]],
    ) -> Dict[str, Any]:
        ambiguous_cases = [
            {
                "annotation_id": m["annotation_id"],
                "clean_text": m.get("clean_text"),
                "detail_region_id": m.get("detail_region_id"),
                "confidence_score": m.get("confidence_score"),
            }
            for m in reconciled["master"]
            if m["ownership_status"] == "AMBIGUOUS"
        ]
        return {
            "total_annotations": validation["total_annotations"],
            "owned_count": validation["owned_count"],
            "ambiguous_count": validation["ambiguous_count"],
            "unassigned_count": validation["unassigned_count"],
            "ownership_conflict_count": len(reconciled["conflicts"]),
            "average_confidence": validation["average_confidence"],
            "validation_status": validation["status"],
            "parser_ready": validation["parser_ready"],
            "contamination_cases": validation["contamination_cases"],
            "resolved_contamination_count": validation["resolved_contamination_count"],
            "top_conflicts": reconciled["conflicts"][:10],
            "ambiguous_cases": ambiguous_cases,
            "region_annotation_counts": validation["region_coverage"],
            "key_regions": self._key_region_summary(
                reconciled["master"], detail_regions
            ),
        }

    def _key_region_summary(
        self,
        master: List[dict[str, Any]],
        detail_regions: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        key_beams = {"B1", "B4", "B8", "B9", "B10", "B13", "B14"}
        summaries: List[dict[str, Any]] = []
        for region in detail_regions:
            titles = set(region["beam_titles"])
            if not titles & key_beams:
                continue
            region_id = region["region_id"]
            records = [m for m in master if m.get("detail_region_id") == region_id]
            foreign_hist = [
                m
                for m in records
                if str(m.get("historical_beam_mark", "")).upper() not in titles
            ]
            foreign_resolved = [
                m
                for m in records
                if str(m.get("resolved_beam_mark", "")).upper() not in titles
            ]
            summaries.append(
                {
                    "region_id": region_id,
                    "beam_titles": sorted(titles, key=beam_mark_sort_key),
                    "annotation_count": len(records),
                    "historical_contamination_count": len(foreign_hist),
                    "resolved_contamination_count": len(foreign_resolved),
                    "resolved_beam_marks": sorted(
                        {
                            str(m.get("resolved_beam_mark", "")).upper()
                            for m in records
                            if m.get("resolved_beam_mark")
                        },
                        key=beam_mark_sort_key,
                    ),
                }
            )
        return summaries

    def _build_report(
        self,
        summary: Dict[str, Any],
        reconciled: Dict[str, Any],
        validation: Dict[str, Any],
        detail_regions: List[dict[str, Any]],
    ) -> str:
        lines = [
            "Phase D.3.3 — Annotation Ownership Reconciliation",
            "=" * 55,
            f"Total annotations: {summary['total_annotations']}",
            f"Owned: {summary['owned_count']}",
            f"Ambiguous: {summary['ambiguous_count']}",
            f"Unassigned: {summary['unassigned_count']}",
            f"Ownership conflicts: {summary['ownership_conflict_count']}",
            f"Average confidence: {summary['average_confidence']}",
            f"Validation: {summary['validation_status']}",
            f"Parser ready: {'YES' if summary['parser_ready'] else 'NO'}",
            "",
            "Key detail regions:",
        ]
        for entry in summary.get("key_regions", []):
            lines.append(
                f"  {entry['region_id']}: {', '.join(entry['beam_titles'])} — "
                f"{entry['annotation_count']} ann, "
                f"hist_contam={entry['historical_contamination_count']}, "
                f"resolved_contam={entry['resolved_contamination_count']}, "
                f"resolved_marks={', '.join(entry['resolved_beam_marks'])}"
            )
        if validation.get("contamination_cases"):
            lines.extend(["", "Contamination cases:"])
            for case in validation["contamination_cases"]:
                lines.append(
                    f"  {case['region_id']}: {case['foreign_count']} foreign "
                    f"({', '.join(case['foreign_beam_marks'])})"
                )
        if reconciled["conflicts"]:
            lines.extend(["", "Top conflicts:"])
            for conflict in reconciled["conflicts"][:5]:
                lines.append(
                    f"  {conflict['annotation_id']}: "
                    f"{conflict.get('clean_text', '')[:40]}"
                )
        if summary.get("ambiguous_cases"):
            lines.extend(["", "Ambiguous cases requiring review:"])
            for case in summary["ambiguous_cases"][:10]:
                lines.append(
                    f"  {case['annotation_id']}: {case.get('clean_text', '')}"
                )
        lines.extend(
            [
                "",
                f"Resolved contaminations: {summary['resolved_contamination_count']}",
                "",
                "Stop after D.3.3 — do not begin Phase D.4 without review.",
            ]
        )
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
