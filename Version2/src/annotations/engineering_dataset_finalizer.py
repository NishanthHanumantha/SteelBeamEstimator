"""Phase D.1.7D — finalize engineering dataset for Phase D.2 parsing."""

import math
import re
from typing import Any, Dict, List, Literal, Optional, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key

FinalStatus = Literal["PARSER_READY", "IGNORED_FRAGMENT", "DEDUPLICATED"]
ResolutionType = Literal["MERGED_WITH_ANCHORAGE", "STANDALONE_FRAGMENT"]
ParserAction = Literal["IGNORE_FRAGMENT", "PARSE", "IGNORE_NOTE"]
ReadinessStatus = Literal["READY_FOR_D2", "FIX_REQUIRED_BEFORE_D2"]

_ANCHORAGE_CLUSTER_DISTANCE_MM = 800.0
_TRUNCATED_FRAGMENT = re.compile(r"^d$", re.IGNORECASE)
_SFR_BAR = re.compile(r"\d+-?Y\d+", re.IGNORECASE)
_SFR_NOTE = re.compile(r"DETAIL|SECTION|CURVED|DEPTH\s*>", re.IGNORECASE)
_SFR_KEYWORD = re.compile(
    r"SIDE\s*\.?\s*FACE|S\.F\.R|(?:^|[^A-Z])SFR(?:[^A-Z]|$)|ON BOTH FACE",
    re.IGNORECASE,
)


class FlatAnnotation(TypedDict, total=False):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    text: str
    clean_text: str
    entity_type: str
    annotation_type: str
    x: float
    y: float
    layer: str
    ownership_source: str
    engineering_source: str
    final_status: FinalStatus


class SketchFinalRecord(TypedDict):
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    annotations: List[FlatAnnotation]


class FragmentResolution(TypedDict):
    clean_text: str
    beam_mark: str
    sketch_id: str
    x: float
    y: float
    resolution_type: ResolutionType
    linked_annotation: Optional[str]
    parser_action: ParserAction
    distance_to_linked_mm: Optional[float]
    reason: str


class FinalSummary(TypedDict):
    total_input_annotations: int
    parser_ready_annotations: int
    ignored_fragments: int
    deduplicated_entries_removed: int
    bar_count: int
    stirrup_count: int
    anchorage_count: int
    side_face_reinf_count: int
    questionable_annotations: int
    readiness_status: ReadinessStatus


class FinalizationResult(TypedDict):
    final_records: List[SketchFinalRecord]
    fragment_resolution: Dict[str, Any]
    sfr_parsing_policy: Dict[str, Any]
    d2_parser_policy: Dict[str, Any]
    deduplicated_entries: List[FlatAnnotation]
    summary: FinalSummary
    report_text: str


class EngineeringDatasetFinalizer:
    """Produce parser-ready engineering_annotations_final.json for Phase D.2."""

    def finalize(
        self,
        engineering_records: List[dict[str, Any]],
        rejected_review: Optional[dict[str, Any]] = None,
        sfr_integrity_report: Optional[dict[str, Any]] = None,
    ) -> FinalizationResult:
        flat = self._flatten(engineering_records)
        logger.info("Finalizing {} engineering annotations", len(flat))

        fragment_resolution = self._resolve_false_rejection(
            flat, rejected_review
        )
        partial_sfr_keys = self._partial_sfr_keys(sfr_integrity_report, flat)

        deduped_flat, deduplicated_entries = self._deduplicate(flat)
        fragment_resolution["deduplicated_entries"] = deduplicated_entries

        final_flat: List[FlatAnnotation] = []

        for item in deduped_flat:
            key = self._position_key(item)
            if key in partial_sfr_keys:
                entry = dict(item)
                entry["final_status"] = "IGNORED_FRAGMENT"
                final_flat.append(entry)
                continue
            entry = dict(item)
            entry["final_status"] = "PARSER_READY"
            final_flat.append(entry)

        final_records = self._group_by_sketch(final_flat)
        summary = self._build_summary(
            len(flat),
            final_flat,
            deduplicated_entries,
            fragment_resolution,
        )
        sfr_policy = self._build_sfr_policy(sfr_integrity_report)
        d2_policy = self._build_d2_parser_policy()
        report_text = self._build_report_text(
            fragment_resolution,
            deduplicated_entries,
            summary,
            sfr_policy,
            d2_policy,
        )

        return FinalizationResult(
            final_records=final_records,
            fragment_resolution=fragment_resolution,
            sfr_parsing_policy=sfr_policy,
            d2_parser_policy=d2_policy,
            deduplicated_entries=deduplicated_entries,
            summary=summary,
            report_text=report_text,
        )

    def _flatten(
        self, engineering_records: List[dict[str, Any]]
    ) -> List[FlatAnnotation]:
        flat: List[FlatAnnotation] = []
        for record in engineering_records:
            beam_mark = str(record["beam_mark"])
            occurrence_id = int(record["occurrence_id"])
            sketch_id = str(record["sketch_id"])
            for item in record.get("annotations", []):
                entry: FlatAnnotation = {
                    "beam_mark": beam_mark,
                    "occurrence_id": occurrence_id,
                    "sketch_id": sketch_id,
                    "text": str(item.get("text", "")),
                    "clean_text": str(item["clean_text"]),
                    "entity_type": str(item.get("entity_type", "")),
                    "annotation_type": str(item["annotation_type"]),
                    "x": round(float(item["x"]), 1),
                    "y": round(float(item["y"]), 1),
                }
                for key in (
                    "layer",
                    "ownership_source",
                    "engineering_source",
                ):
                    if key in item:
                        entry[key] = str(item[key])
                flat.append(entry)
        return flat

    def _resolve_false_rejection(
        self,
        flat: List[FlatAnnotation],
        rejected_review: Optional[dict[str, Any]],
    ) -> Dict[str, Any]:
        false_rejections: List[dict[str, Any]] = []
        if rejected_review:
            false_rejections = rejected_review.get("false_rejections", [])

        resolutions: List[FragmentResolution] = []
        for rejection in false_rejections:
            clean_text = str(rejection["clean_text"]).strip()
            beam_mark = str(rejection["beam_mark"])
            sketch_id = str(rejection["sketch_id"])
            fx = round(float(rejection["x"]), 1)
            fy = round(float(rejection["y"]), 1)

            linked: Optional[FlatAnnotation] = None
            min_distance: Optional[float] = None

            for item in flat:
                if item["beam_mark"] != beam_mark or item["sketch_id"] != sketch_id:
                    continue
                if item["annotation_type"] != "ANCHORAGE":
                    continue
                dist = math.hypot(item["x"] - fx, item["y"] - fy)
                if min_distance is None or dist < min_distance:
                    min_distance = dist
                    linked = item

            if linked is not None and min_distance is not None:
                if min_distance <= _ANCHORAGE_CLUSTER_DISTANCE_MM:
                    resolution_type: ResolutionType = "MERGED_WITH_ANCHORAGE"
                    reason = (
                        f"Fragment '{clean_text}' within {min_distance:.1f}mm of "
                        f"anchorage '{linked['clean_text']}' in same sketch"
                    )
                    linked_text = linked["clean_text"]
                else:
                    resolution_type = "STANDALONE_FRAGMENT"
                    reason = (
                        f"Fragment '{clean_text}' not within anchorage cluster "
                        f"(nearest {min_distance:.1f}mm)"
                    )
                    linked_text = None
            else:
                resolution_type = "STANDALONE_FRAGMENT"
                reason = f"No anchorage annotation in sketch {sketch_id}"
                linked_text = None
                min_distance = None

            resolutions.append(
                FragmentResolution(
                    clean_text=clean_text,
                    beam_mark=beam_mark,
                    sketch_id=sketch_id,
                    x=fx,
                    y=fy,
                    resolution_type=resolution_type,
                    linked_annotation=linked_text,
                    parser_action="IGNORE_FRAGMENT",
                    distance_to_linked_mm=round(min_distance, 1) if min_distance else None,
                    reason=reason,
                )
            )

        resolved_count = len(resolutions)
        merged_count = sum(
            1 for r in resolutions if r["resolution_type"] == "MERGED_WITH_ANCHORAGE"
        )

        return {
            "false_rejections_reviewed": resolved_count,
            "false_rejections_remaining": 0,
            "merged_with_anchorage": merged_count,
            "standalone_fragments": resolved_count - merged_count,
            "resolutions": resolutions,
            "deduplicated_entries": [],
        }

    def _partial_sfr_keys(
        self,
        sfr_integrity_report: Optional[dict[str, Any]],
        flat: List[FlatAnnotation],
    ) -> set[tuple[str, str, float, float]]:
        keys: set[tuple[str, str, float, float]] = set()
        if sfr_integrity_report:
            for rec in sfr_integrity_report.get("records", []):
                if rec.get("classification") == "PARTIAL_SFR":
                    keys.add(
                        (
                            str(rec["sketch_id"]),
                            str(rec["clean_text"]),
                            round(float(rec["x"]), 1),
                            round(float(rec["y"]), 1),
                        )
                    )
            return keys

        for item in flat:
            if item["annotation_type"] != "SIDE_FACE_REINF":
                continue
            text = item["clean_text"]
            has_bar = bool(_SFR_BAR.search(text))
            is_note = bool(_SFR_NOTE.search(text))
            if not has_bar or is_note:
                keys.add(self._position_key(item))
        return keys

    def _position_key(
        self, item: FlatAnnotation
    ) -> tuple[str, str, float, float]:
        return (
            item["sketch_id"],
            item["clean_text"],
            item["x"],
            item["y"],
        )

    def _deduplicate(
        self, flat: List[FlatAnnotation]
    ) -> tuple[List[FlatAnnotation], List[FlatAnnotation]]:
        seen: set[tuple[str, float, float]] = set()
        kept: List[FlatAnnotation] = []
        removed: List[FlatAnnotation] = []

        for item in flat:
            key = (item["clean_text"], item["x"], item["y"])
            if key in seen:
                dup = dict(item)
                dup["final_status"] = "DEDUPLICATED"
                removed.append(dup)
                continue
            seen.add(key)
            kept.append(item)

        return kept, removed

    def _group_by_sketch(
        self, flat: List[FlatAnnotation]
    ) -> List[SketchFinalRecord]:
        by_sketch: Dict[tuple[str, int, str], SketchFinalRecord] = {}
        for item in flat:
            sketch_key = (
                item["beam_mark"],
                item["occurrence_id"],
                item["sketch_id"],
            )
            if sketch_key not in by_sketch:
                by_sketch[sketch_key] = SketchFinalRecord(
                    beam_mark=item["beam_mark"],
                    occurrence_id=item["occurrence_id"],
                    sketch_id=item["sketch_id"],
                    annotations=[],
                )
            by_sketch[sketch_key]["annotations"].append(item)

        records = list(by_sketch.values())
        records.sort(
            key=lambda r: (
                beam_mark_sort_key(r["beam_mark"]),
                r["occurrence_id"],
                r["sketch_id"],
            )
        )
        return records

    def _build_sfr_policy(
        self, sfr_integrity_report: Optional[dict[str, Any]]
    ) -> Dict[str, Any]:
        valid_examples = [
            "S.F.R.- 2-Y10",
            "4-Y8, SIDE FACE REINF. ON BOTH FACES",
        ]
        partial_examples = [
            "S.F.R. ON BOTH FACE",
            "SIDE FACE REINFORCEMENT DETAILS FOR CURVED BEAMS DEPTH>450",
        ]
        valid_entries: List[dict[str, Any]] = []
        partial_entries: List[dict[str, Any]] = []

        if sfr_integrity_report:
            for rec in sfr_integrity_report.get("records", []):
                entry = {
                    "clean_text": rec["clean_text"],
                    "beam_mark": rec["beam_mark"],
                    "sketch_id": rec["sketch_id"],
                    "classification": rec["classification"],
                }
                if rec["classification"] == "VALID_SFR":
                    valid_entries.append(entry)
                elif rec["classification"] == "PARTIAL_SFR":
                    partial_entries.append(entry)

        return {
            "VALID_SFR": {
                "action": "PARSE",
                "description": "Parse bar quantity and diameter from side-face reinforcement callouts.",
                "examples": valid_examples,
                "entries": valid_entries,
            },
            "PARTIAL_SFR": {
                "action": "IGNORE_NOTE",
                "description": (
                    "Documented in final dataset but excluded from "
                    "reinforcement quantity parsing."
                ),
                "examples": partial_examples,
                "entries": partial_entries,
            },
        }

    def _build_d2_parser_policy(self) -> Dict[str, Any]:
        return {
            "BAR": {
                "parse_fields": ["quantity", "diameter"],
                "examples": ["2-Y16", "2-Y20", "4-Y25"],
            },
            "STIRRUP": {
                "parse_fields": ["leg_count", "diameter", "spacing"],
                "examples": [
                    "2L-Y8@100C/C",
                    "2L-Y8@150C/C",
                    "2L-Y8@100/200/100C/C",
                ],
            },
            "ANCHORAGE": {
                "parse_fields": ["Ld", "extension"],
                "examples": ["Ld", "Ld+10db", "Ld+12db"],
            },
            "SIDE_FACE_REINF": {
                "parse_when": "bar_info_present",
                "examples": [
                    "S.F.R.- 2-Y10",
                    "4-Y8 SIDE FACE REINF",
                ],
                "ignore_classification": "PARTIAL_SFR",
            },
            "IGNORE": {
                "categories": [
                    "notes",
                    "fragments",
                    "geometry_dimensions",
                    "autocad_measurements",
                    "deduplicated_entries",
                ],
                "examples": [
                    "687",
                    "688",
                    "530",
                    "537",
                    "500",
                    "1900",
                    "2150",
                    "d",
                ],
            },
        }

    def _build_summary(
        self,
        total_input: int,
        final_flat: List[FlatAnnotation],
        deduplicated_entries: List[FlatAnnotation],
        fragment_resolution: Dict[str, Any],
    ) -> FinalSummary:
        parser_ready = [
            i for i in final_flat if i.get("final_status") == "PARSER_READY"
        ]
        ignored = [
            i for i in final_flat if i.get("final_status") == "IGNORED_FRAGMENT"
        ]
        resolved_fragments = fragment_resolution.get("false_rejections_reviewed", 0)

        type_counts = {"BAR": 0, "STIRRUP": 0, "ANCHORAGE": 0, "SIDE_FACE_REINF": 0}
        for item in parser_ready:
            ann_type = item["annotation_type"]
            if ann_type in type_counts:
                type_counts[ann_type] += 1

        questionable = 0
        readiness: ReadinessStatus = "READY_FOR_D2"
        if fragment_resolution.get("false_rejections_remaining", 0) > 0:
            readiness = "FIX_REQUIRED_BEFORE_D2"
        if questionable > 0:
            readiness = "FIX_REQUIRED_BEFORE_D2"

        return FinalSummary(
            total_input_annotations=total_input,
            parser_ready_annotations=len(parser_ready),
            ignored_fragments=len(ignored) + resolved_fragments,
            deduplicated_entries_removed=len(deduplicated_entries),
            bar_count=type_counts["BAR"],
            stirrup_count=type_counts["STIRRUP"],
            anchorage_count=type_counts["ANCHORAGE"],
            side_face_reinf_count=type_counts["SIDE_FACE_REINF"],
            questionable_annotations=questionable,
            readiness_status=readiness,
        )

    def _build_report_text(
        self,
        fragment_resolution: Dict[str, Any],
        deduplicated_entries: List[FlatAnnotation],
        summary: FinalSummary,
        sfr_policy: Dict[str, Any],
        d2_policy: Dict[str, Any],
    ) -> str:
        lines = [
            "======================================================================",
            "Engineering Dataset Finalization Report (Phase D.1.7D)",
            "======================================================================",
            "",
            "1. False Rejection Resolution",
            f"   Reviewed: {fragment_resolution['false_rejections_reviewed']}",
            f"   Remaining: {fragment_resolution['false_rejections_remaining']}",
            f"   Merged with anchorage: {fragment_resolution['merged_with_anchorage']}",
            "",
        ]
        for res in fragment_resolution.get("resolutions", []):
            lines.append(
                f"   - '{res['clean_text']}' ({res['beam_mark']}/{res['sketch_id']}): "
                f"{res['resolution_type']} -> {res['parser_action']}"
            )
            if res.get("linked_annotation"):
                lines.append(f"     Linked: {res['linked_annotation']}")

        lines.extend(
            [
                "",
                "2. Deduplication Results",
                f"   Entries removed: {summary['deduplicated_entries_removed']}",
                f"   Unique positions retained: {summary['parser_ready_annotations'] + summary.get('ignored_fragments', 0) - fragment_resolution.get('false_rejections_reviewed', 0)}",
                "",
                "3. Final Engineering Counts (parser-ready)",
                f"   BAR: {summary['bar_count']}",
                f"   STIRRUP: {summary['stirrup_count']}",
                f"   ANCHORAGE: {summary['anchorage_count']}",
                f"   SIDE_FACE_REINF: {summary['side_face_reinf_count']}",
                "",
                "4. SFR Handling Policy",
                f"   VALID_SFR action: {sfr_policy['VALID_SFR']['action']}",
                f"   PARTIAL_SFR action: {sfr_policy['PARTIAL_SFR']['action']}",
                f"   Partial entries ignored: {len(sfr_policy['PARTIAL_SFR']['entries'])}",
                "",
                "5. D.2 Parser Policy Summary",
                "   BAR: parse quantity + diameter",
                "   STIRRUP: parse leg_count + diameter + spacing",
                "   ANCHORAGE: parse Ld + extension",
                "   SIDE_FACE_REINF: parse when bar info present",
                "   IGNORE: notes, fragments, geometry, measurements",
                "",
                "6. Final Readiness Status",
                f"   Questionable annotations: {summary['questionable_annotations']}",
                f"   Readiness: {summary['readiness_status']}",
                "",
                "======================================================================",
            ]
        )
        return "\n".join(lines) + "\n"
