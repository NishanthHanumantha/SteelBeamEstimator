"""Phase D.2 — parse and normalize engineering annotations."""

from typing import Any, Dict, List, Literal, Optional, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.parsing.annotation_parsers import parse_annotation

ParserStatus = Literal["PARSED", "FAILED", "UNSUPPORTED", "SKIPPED"]


class ParsedRecord(TypedDict, total=False):
    annotation_id: str
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    annotation_type: str
    raw_text: str
    clean_text: str
    parsed_fields: Dict[str, Any]
    source_entity_type: str
    source_layer: str
    x: float
    y: float
    parser_status: ParserStatus
    parse_error: str
    source_annotation_index: int
    source_occurrence_id: int
    source_sketch_id: str


class ParsingSummary(TypedDict):
    parser_ready_input_count: int
    parsed_successfully: int
    failed_parses: int
    unsupported_count: int
    skipped_count: int
    coverage_pct: float
    bar_count: int
    stirrup_count: int
    anchorage_count: int
    side_face_reinf_count: int
    top_failed_patterns: List[Dict[str, Any]]
    ready_for_phase_e: bool


class ParsingResult(TypedDict):
    master: List[ParsedRecord]
    bars: List[ParsedRecord]
    stirrups: List[ParsedRecord]
    anchorage: List[ParsedRecord]
    side_face_reinf: List[ParsedRecord]
    failed: List[ParsedRecord]
    summary: ParsingSummary
    report_text: str


_SUPPORTED_TYPES = frozenset({"BAR", "STIRRUP", "ANCHORAGE", "SIDE_FACE_REINF"})


class AnnotationParsingPipeline:
    """Convert PARSER_READY engineering annotations into structured objects."""

    def parse(
        self,
        final_records: List[dict[str, Any]],
        sfr_parsing_policy: Optional[dict[str, Any]] = None,
    ) -> ParsingResult:
        valid_sfr_keys = self._valid_sfr_keys(sfr_parsing_policy)
        inputs = self._collect_parser_ready(final_records)
        logger.info("D.2 parsing: {} parser-ready annotations", len(inputs))

        master: List[ParsedRecord] = []
        bars: List[ParsedRecord] = []
        stirrups: List[ParsedRecord] = []
        anchorage_list: List[ParsedRecord] = []
        sfr_list: List[ParsedRecord] = []
        failed: List[ParsedRecord] = []
        failure_counts: Dict[str, int] = {}

        for index, item in enumerate(inputs):
            record = self._parse_one(item, index, valid_sfr_keys)
            master.append(record)

            status = record.get("parser_status", "FAILED")
            if status == "PARSED":
                ann_type = record["annotation_type"]
                if ann_type == "BAR":
                    bars.append(record)
                elif ann_type == "STIRRUP":
                    stirrups.append(record)
                elif ann_type == "ANCHORAGE":
                    anchorage_list.append(record)
                elif ann_type == "SIDE_FACE_REINF":
                    sfr_list.append(record)
            else:
                failed.append(record)
                key = f"{record.get('annotation_type')}|{record.get('clean_text')}|{record.get('parse_error', '')}"
                failure_counts[key] = failure_counts.get(key, 0) + 1

        parsed_count = len(bars) + len(stirrups) + len(anchorage_list) + len(sfr_list)
        ready_count = len(inputs)
        coverage = (parsed_count / ready_count * 100) if ready_count else 0.0

        top_failed = sorted(
            [
                {"pattern": k, "count": v}
                for k, v in failure_counts.items()
            ],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        unsupported = sum(1 for r in failed if r.get("parser_status") == "UNSUPPORTED")

        summary = ParsingSummary(
            parser_ready_input_count=ready_count,
            parsed_successfully=parsed_count,
            failed_parses=len(failed),
            unsupported_count=unsupported,
            skipped_count=0,
            coverage_pct=round(coverage, 2),
            bar_count=len(bars),
            stirrup_count=len(stirrups),
            anchorage_count=len(anchorage_list),
            side_face_reinf_count=len(sfr_list),
            top_failed_patterns=top_failed,
            ready_for_phase_e=coverage >= 98.0 and parsed_count > 0,
        )

        report_text = self._build_report(summary, failed)
        return ParsingResult(
            master=master,
            bars=bars,
            stirrups=stirrups,
            anchorage=anchorage_list,
            side_face_reinf=sfr_list,
            failed=failed,
            summary=summary,
            report_text=report_text,
        )

    def _valid_sfr_keys(
        self, sfr_parsing_policy: Optional[dict[str, Any]]
    ) -> set[tuple[str, str]]:
        keys: set[tuple[str, str]] = set()
        if not sfr_parsing_policy:
            return keys
        for entry in sfr_parsing_policy.get("VALID_SFR", {}).get("entries", []):
            keys.add((str(entry["sketch_id"]), str(entry["clean_text"])))
        return keys

    def _collect_parser_ready(
        self, final_records: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        items: List[dict[str, Any]] = []
        for sketch_record in final_records:
            beam_mark = str(sketch_record["beam_mark"])
            occurrence_id = int(sketch_record["occurrence_id"])
            sketch_id = str(sketch_record["sketch_id"])
            for ann in sketch_record.get("annotations", []):
                if str(ann.get("final_status", "")) != "PARSER_READY":
                    continue
                items.append(
                    {
                        "beam_mark": beam_mark,
                        "occurrence_id": occurrence_id,
                        "sketch_id": sketch_id,
                        **ann,
                    }
                )
        items.sort(
            key=lambda i: (
                beam_mark_sort_key(i["beam_mark"]),
                i["occurrence_id"],
                i["sketch_id"],
                i.get("clean_text", ""),
                float(i.get("x", 0)),
                float(i.get("y", 0)),
            )
        )
        return items

    def _parse_one(
        self,
        item: dict[str, Any],
        index: int,
        valid_sfr_keys: set[tuple[str, str]],
    ) -> ParsedRecord:
        annotation_id = f"ANN_{index + 1:05d}"
        beam_mark = str(item["beam_mark"])
        occurrence_id = int(item["occurrence_id"])
        sketch_id = str(item["sketch_id"])
        clean_text = str(item["clean_text"])
        annotation_type = str(item["annotation_type"])

        base: ParsedRecord = {
            "annotation_id": annotation_id,
            "beam_mark": beam_mark,
            "occurrence_id": occurrence_id,
            "sketch_id": sketch_id,
            "annotation_type": annotation_type,
            "raw_text": str(item.get("text", "")),
            "clean_text": clean_text,
            "source_entity_type": str(item.get("entity_type", "")),
            "x": round(float(item["x"]), 1),
            "y": round(float(item["y"]), 1),
            "source_annotation_index": index,
            "source_occurrence_id": occurrence_id,
            "source_sketch_id": sketch_id,
        }
        if "layer" in item:
            base["source_layer"] = str(item["layer"])

        if annotation_type not in _SUPPORTED_TYPES:
            base["parser_status"] = "UNSUPPORTED"
            base["parse_error"] = f"unsupported annotation_type: {annotation_type}"
            return base

        parsed_fields, error = parse_annotation(annotation_type, clean_text)
        if parsed_fields is not None:
            base["parsed_fields"] = parsed_fields
            base["parser_status"] = "PARSED"
            return base

        base["parser_status"] = "FAILED" if error and "unsupported" not in error else "UNSUPPORTED"
        if error and "unsupported annotation_type" in error:
            base["parser_status"] = "UNSUPPORTED"
        base["parse_error"] = error or "unknown parse failure"
        return base

    def _build_report(
        self, summary: ParsingSummary, failed: List[ParsedRecord]
    ) -> str:
        lines = [
            "======================================================================",
            "Annotation Parsing Report (Phase D.2)",
            "======================================================================",
            "",
            f"Total parser-ready annotations: {summary['parser_ready_input_count']}",
            f"Parsed successfully: {summary['parsed_successfully']}",
            f"Failed parses: {summary['failed_parses']}",
            f"Coverage: {summary['coverage_pct']}%",
            "",
            "Counts by type:",
            f"  BAR: {summary['bar_count']}",
            f"  STIRRUP: {summary['stirrup_count']}",
            f"  ANCHORAGE: {summary['anchorage_count']}",
            f"  SIDE_FACE_REINF: {summary['side_face_reinf_count']}",
            "",
            f"READY_FOR_PHASE_E: {summary['ready_for_phase_e']}",
            "",
        ]
        if summary["top_failed_patterns"]:
            lines.append("Top failed patterns:")
            for entry in summary["top_failed_patterns"]:
                lines.append(f"  - {entry['pattern']} (count={entry['count']})")
            lines.append("")

        if failed:
            lines.append(f"Failed records: {len(failed)}")
            for rec in failed[:5]:
                lines.append(
                    f"  {rec['annotation_id']} {rec['clean_text']}: {rec.get('parse_error', '')}"
                )

        lines.extend(
            [
                "",
                "======================================================================",
            ]
        )
        return "\n".join(lines) + "\n"
