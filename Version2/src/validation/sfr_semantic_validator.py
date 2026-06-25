"""Phase D.1.7F — semantic classification for SIDE_FACE_REINF annotations."""

import re
from typing import Any, Dict, List, Literal, Optional, TypedDict

from loguru import logger

from src.parsing.annotation_parsers import parse_side_face_reinf

SemanticClass = Literal[
    "ENGINEERING_SFR",
    "REFERENCE_NOTE",
    "PARTIAL_SFR",
    "UNKNOWN",
]

FinalStatus = Literal[
    "PARSER_READY",
    "IGNORED_REFERENCE",
    "IGNORED_FRAGMENT",
    "SFR_REJECTED",
    "SFR_UNKNOWN",
]

ValidationStatus = Literal["PASS", "WARN", "FAIL"]
Recommendation = Literal["READY_FOR_PHASE_E", "FIX_REQUIRED"]

_ENGINEERING_BAR_PATTERN = re.compile(r"\d+\s*-?\s*Y\d+", re.IGNORECASE)
_QUANTITY_DIAMETER_PATTERN = re.compile(r"(\d+)\s*-?\s*Y(\d+)", re.IGNORECASE)
_DIAMETER_PATTERN = re.compile(r"Y(\d+)", re.IGNORECASE)

_REFERENCE_KEYWORDS = (
    "DETAIL",
    "DETAILS",
    "CURVED BEAMS",
    "CURVED BEAM",
    "DEPTH>",
    "DEPTH >",
    "ON BOTH FACE",
    "ON BOTH FACES",
)

_PARTIAL_KEYWORDS = (
    "SIDE FACE REINF",
    "SIDE FACE",
    "S.F.R.",
    "S.F.R",
    "SFR",
)

_DETAIL_KEYWORDS = ("DETAIL", "DETAILS")
_CURVED_KEYWORDS = ("CURVED BEAMS", "CURVED BEAM", "CURVED")
_DEPTH_KEYWORDS = ("DEPTH>", "DEPTH >")


class SemanticFlags(TypedDict):
    contains_quantity: bool
    contains_diameter: bool
    contains_engineering_pattern: bool
    contains_reference_keywords: bool
    contains_detail_keyword: bool
    contains_curved_keyword: bool
    contains_depth_keyword: bool


class SfrSemanticRecord(TypedDict, total=False):
    annotation_id: str
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    clean_text: str
    raw_text: str
    x: float
    y: float
    semantic_class: SemanticClass
    semantic_reason: str
    final_status: FinalStatus
    ownership_validator_status: Optional[str]
    flags: SemanticFlags


class SemanticDistribution(TypedDict):
    ENGINEERING_SFR: int
    REFERENCE_NOTE: int
    PARTIAL_SFR: int
    UNKNOWN: int


class SemanticSummary(TypedDict):
    total_sfr_annotations: int
    semantic_distribution: SemanticDistribution
    engineering_sfr_count: int
    reference_note_count: int
    partial_sfr_count: int
    unknown_count: int
    parser_ready_sfr_count: int
    ownership_rejected_engineering_count: int
    validation_status: ValidationStatus
    recommendation: Recommendation


class SemanticValidationChecks(TypedDict):
    engineering_sfr_have_quantity_and_diameter: bool
    no_reference_notes_parser_ready: bool
    no_partial_fragments_parser_ready: bool
    no_engineering_sfr_incorrectly_rejected: bool


class SemanticValidationResult(TypedDict):
    status: ValidationStatus
    checks: SemanticValidationChecks
    issues: List[str]


class SfrSemanticResult(TypedDict):
    semantic_records: List[SfrSemanticRecord]
    engineering_annotations_semantic: List[SfrSemanticRecord]
    refined_master: List[dict[str, Any]]
    validation: SemanticValidationResult
    summary: SemanticSummary
    report_text: str


class SfrSemanticClassifier:
    """Classify SFR annotation text without modifying ownership."""

    def normalize(self, text: str) -> str:
        normalized = text.upper().strip()
        normalized = normalized.replace(".", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def analyze_flags(self, clean_text: str) -> SemanticFlags:
        normalized = self.normalize(clean_text)
        qty_dia_matches = list(_QUANTITY_DIAMETER_PATTERN.finditer(normalized))
        contains_engineering_pattern = bool(_ENGINEERING_BAR_PATTERN.search(normalized))
        contains_quantity = bool(qty_dia_matches)
        contains_diameter = bool(_DIAMETER_PATTERN.search(normalized)) and contains_quantity

        contains_reference_keywords = any(k in normalized for k in _REFERENCE_KEYWORDS)
        contains_detail_keyword = any(k in normalized for k in _DETAIL_KEYWORDS)
        contains_curved_keyword = any(k in normalized for k in _CURVED_KEYWORDS)
        contains_depth_keyword = any(k in normalized for k in _DEPTH_KEYWORDS)

        return SemanticFlags(
            contains_quantity=contains_quantity,
            contains_diameter=contains_diameter,
            contains_engineering_pattern=contains_engineering_pattern,
            contains_reference_keywords=contains_reference_keywords,
            contains_detail_keyword=contains_detail_keyword,
            contains_curved_keyword=contains_curved_keyword,
            contains_depth_keyword=contains_depth_keyword,
        )

    def classify(self, clean_text: str) -> tuple[SemanticClass, str, SemanticFlags]:
        flags = self.analyze_flags(clean_text)
        normalized = self.normalize(clean_text)

        if flags["contains_engineering_pattern"]:
            try:
                parse_side_face_reinf(clean_text)
                return (
                    "ENGINEERING_SFR",
                    "Contains bar quantity and diameter specification",
                    flags,
                )
            except Exception:
                pass

        is_reference = (
            not flags["contains_quantity"]
            and not flags["contains_diameter"]
            and (
                flags["contains_detail_keyword"]
                or flags["contains_curved_keyword"]
                or flags["contains_depth_keyword"]
                or "ON BOTH FACE" in normalized
                or "ON BOTH FACES" in normalized
            )
        )
        if is_reference:
            return "REFERENCE_NOTE", "Reference note only", flags

        is_partial = any(keyword in normalized for keyword in _PARTIAL_KEYWORDS)
        if is_partial and not flags["contains_engineering_pattern"]:
            return "PARTIAL_SFR", "SFR mention without engineering specification", flags

        if flags["contains_engineering_pattern"]:
            return (
                "ENGINEERING_SFR",
                "Contains engineering reinforcement pattern",
                flags,
            )

        return "UNKNOWN", "Unclassified SFR annotation", flags


class SfrSemanticValidator:
    """Apply semantic validation to SIDE_FACE_REINF in D.1.7E master dataset."""

    def __init__(self) -> None:
        self._classifier = SfrSemanticClassifier()

    def validate(self, master_records: List[dict[str, Any]]) -> SfrSemanticResult:
        semantic_records: List[SfrSemanticRecord] = []
        sfr_index = 0

        for sketch_record in master_records:
            for ann in sketch_record.get("annotations", []):
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    continue
                sfr_index += 1
                record = self._classify_annotation(ann, sketch_record, sfr_index)
                semantic_records.append(record)

        logger.info("D.1.7F: classified {} SFR annotations", len(semantic_records))

        refined_master = self._build_refined_master(master_records, semantic_records)
        validation = self._validate_semantics(semantic_records, refined_master)
        summary = self._build_summary(semantic_records, refined_master, validation)
        report_text = self._build_report(summary, validation, semantic_records)

        return SfrSemanticResult(
            semantic_records=semantic_records,
            engineering_annotations_semantic=[
                r for r in semantic_records if r["semantic_class"] == "ENGINEERING_SFR"
            ],
            refined_master=refined_master,
            validation=validation,
            summary=summary,
            report_text=report_text,
        )

    def _classify_annotation(
        self,
        ann: dict[str, Any],
        sketch_record: dict[str, Any],
        index: int,
    ) -> SfrSemanticRecord:
        clean_text = str(ann["clean_text"])
        semantic_class, reason, flags = self._classifier.classify(clean_text)

        ownership = ann.get("sfr_validation", {})
        ownership_status = ownership.get("validator_status")

        final_status = self._resolve_final_status(
            semantic_class, ownership_status, ann.get("final_status")
        )

        beam_mark = str(ann.get("beam_mark", sketch_record["beam_mark"]))
        occurrence_id = int(ann.get("occurrence_id", sketch_record["occurrence_id"]))
        sketch_id = str(ann.get("sketch_id", sketch_record["sketch_id"]))

        return SfrSemanticRecord(
            annotation_id=f"SFR_SEM_{index:05d}",
            beam_mark=beam_mark,
            occurrence_id=occurrence_id,
            sketch_id=sketch_id,
            clean_text=clean_text,
            raw_text=str(ann.get("text", "")),
            x=round(float(ann["x"]), 1),
            y=round(float(ann["y"]), 1),
            semantic_class=semantic_class,
            semantic_reason=reason,
            final_status=final_status,
            ownership_validator_status=str(ownership_status) if ownership_status else None,
            flags=flags,
        )

    @staticmethod
    def _resolve_final_status(
        semantic_class: SemanticClass,
        ownership_status: Optional[str],
        prior_status: Optional[str],
    ) -> FinalStatus:
        if semantic_class == "ENGINEERING_SFR":
            if ownership_status == "VALIDATED":
                return "PARSER_READY"
            return "SFR_REJECTED"
        if semantic_class == "REFERENCE_NOTE":
            return "IGNORED_REFERENCE"
        if semantic_class == "PARTIAL_SFR":
            return "IGNORED_FRAGMENT"
        if prior_status == "SFR_REJECTED":
            return "SFR_REJECTED"
        return "SFR_UNKNOWN"

    def _build_refined_master(
        self,
        master_records: List[dict[str, Any]],
        semantic_records: List[SfrSemanticRecord],
    ) -> List[dict[str, Any]]:
        lookup = {
            (
                str(r["clean_text"]),
                round(float(r["x"]), 1),
                round(float(r["y"]), 1),
                str(r["sketch_id"]),
            ): r
            for r in semantic_records
        }

        refined: List[dict[str, Any]] = []
        for sketch_record in master_records:
            sketch_id = str(sketch_record["sketch_id"])
            new_anns: List[dict[str, Any]] = []
            for ann in sketch_record.get("annotations", []):
                entry = dict(ann)
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    new_anns.append(entry)
                    continue

                key = (
                    str(ann["clean_text"]),
                    round(float(ann["x"]), 1),
                    round(float(ann["y"]), 1),
                    sketch_id,
                )
                sem = lookup.get(key)
                if sem is None:
                    new_anns.append(entry)
                    continue

                entry["sfr_semantic_validation"] = {
                    "semantic_class": sem["semantic_class"],
                    "semantic_reason": sem["semantic_reason"],
                    "final_status": sem["final_status"],
                    "flags": sem["flags"],
                }
                entry["final_status"] = sem["final_status"]
                new_anns.append(entry)

            refined.append(
                {
                    "beam_mark": sketch_record["beam_mark"],
                    "occurrence_id": sketch_record["occurrence_id"],
                    "sketch_id": sketch_id,
                    "annotations": new_anns,
                }
            )
        return refined

    def _validate_semantics(
        self,
        semantic_records: List[SfrSemanticRecord],
        refined_master: List[dict[str, Any]],
    ) -> SemanticValidationResult:
        issues: List[str] = []

        engineering = [r for r in semantic_records if r["semantic_class"] == "ENGINEERING_SFR"]
        engineering_ok = all(
            r["flags"]["contains_quantity"] and r["flags"]["contains_diameter"]
            for r in engineering
        )
        if not engineering_ok:
            issues.append("Engineering SFR missing quantity or diameter flags")

        parser_ready_sfr = self._count_parser_ready_sfr(refined_master)
        ref_parser_ready = [
            r for r in semantic_records
            if r["semantic_class"] == "REFERENCE_NOTE"
            and self._is_parser_ready_in_master(r, refined_master)
        ]
        no_ref_parser_ready = len(ref_parser_ready) == 0
        if not no_ref_parser_ready:
            issues.append("Reference notes remain parser-ready")

        partial_parser_ready = [
            r for r in semantic_records
            if r["semantic_class"] == "PARTIAL_SFR"
            and self._is_parser_ready_in_master(r, refined_master)
        ]
        no_partial_parser_ready = len(partial_parser_ready) == 0
        if not no_partial_parser_ready:
            issues.append("Partial SFR fragments remain parser-ready")

        wrongly_rejected = [
            r for r in engineering
            if r.get("ownership_validator_status") == "VALIDATED"
            and not self._is_parser_ready_in_master(r, refined_master)
        ]
        no_wrong_reject = len(wrongly_rejected) == 0
        if not no_wrong_reject:
            issues.append("Validated engineering SFR not parser-ready after semantics")

        checks = SemanticValidationChecks(
            engineering_sfr_have_quantity_and_diameter=engineering_ok,
            no_reference_notes_parser_ready=no_ref_parser_ready,
            no_partial_fragments_parser_ready=no_partial_parser_ready,
            no_engineering_sfr_incorrectly_rejected=no_wrong_reject,
        )

        if all(checks.values()):
            status: ValidationStatus = "PASS"
        elif engineering_ok and no_ref_parser_ready and no_partial_parser_ready:
            status = "WARN"
        else:
            status = "FAIL"

        return SemanticValidationResult(status=status, checks=checks, issues=issues)

    def _is_parser_ready_in_master(
        self, record: SfrSemanticRecord, refined_master: List[dict[str, Any]]
    ) -> bool:
        for sketch_record in refined_master:
            if str(sketch_record["sketch_id"]) != record["sketch_id"]:
                continue
            for ann in sketch_record.get("annotations", []):
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    continue
                if (
                    str(ann.get("clean_text")) == record["clean_text"]
                    and round(float(ann["x"]), 1) == record["x"]
                    and round(float(ann["y"]), 1) == record["y"]
                ):
                    return str(ann.get("final_status")) == "PARSER_READY"
        return False

    @staticmethod
    def _count_parser_ready_sfr(refined_master: List[dict[str, Any]]) -> int:
        count = 0
        for sketch_record in refined_master:
            for ann in sketch_record.get("annotations", []):
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    continue
                if str(ann.get("final_status")) == "PARSER_READY":
                    count += 1
        return count

    def _build_summary(
        self,
        semantic_records: List[SfrSemanticRecord],
        refined_master: List[dict[str, Any]],
        validation: SemanticValidationResult,
    ) -> SemanticSummary:
        dist: SemanticDistribution = {
            "ENGINEERING_SFR": 0,
            "REFERENCE_NOTE": 0,
            "PARTIAL_SFR": 0,
            "UNKNOWN": 0,
        }
        for rec in semantic_records:
            dist[rec["semantic_class"]] += 1

        engineering = dist["ENGINEERING_SFR"]
        ownership_rejected_engineering = sum(
            1
            for r in semantic_records
            if r["semantic_class"] == "ENGINEERING_SFR"
            and r.get("ownership_validator_status") != "VALIDATED"
        )
        parser_ready = self._count_parser_ready_sfr(refined_master)

        recommendation: Recommendation = (
            "READY_FOR_PHASE_E"
            if validation["status"] in ("PASS", "WARN") and parser_ready > 0
            else "FIX_REQUIRED"
        )

        return SemanticSummary(
            total_sfr_annotations=len(semantic_records),
            semantic_distribution=dist,
            engineering_sfr_count=engineering,
            reference_note_count=dist["REFERENCE_NOTE"],
            partial_sfr_count=dist["PARTIAL_SFR"],
            unknown_count=dist["UNKNOWN"],
            parser_ready_sfr_count=parser_ready,
            ownership_rejected_engineering_count=ownership_rejected_engineering,
            validation_status=validation["status"],
            recommendation=recommendation,
        )

    def _build_report(
        self,
        summary: SemanticSummary,
        validation: SemanticValidationResult,
        records: List[SfrSemanticRecord],
    ) -> str:
        lines = [
            "======================================================================",
            "SFR Semantic Validation Report (Phase D.1.7F)",
            "======================================================================",
            "",
            "Semantic distribution:",
            f"  ENGINEERING_SFR: {summary['semantic_distribution']['ENGINEERING_SFR']}",
            f"  REFERENCE_NOTE: {summary['semantic_distribution']['REFERENCE_NOTE']}",
            f"  PARTIAL_SFR: {summary['semantic_distribution']['PARTIAL_SFR']}",
            f"  UNKNOWN: {summary['semantic_distribution']['UNKNOWN']}",
            "",
            f"Engineering SFR count: {summary['engineering_sfr_count']}",
            f"Reference note count: {summary['reference_note_count']}",
            f"Partial fragment count: {summary['partial_sfr_count']}",
            f"Parser-ready SFR count: {summary['parser_ready_sfr_count']}",
            f"Ownership-rejected engineering SFR: {summary['ownership_rejected_engineering_count']}",
            "",
            f"Validation: {summary['validation_status']}",
            f"Recommendation: {summary['recommendation']}",
            "",
            "Checks:",
        ]
        for name, passed in validation["checks"].items():
            lines.append(f"  {name}: {'PASS' if passed else 'FAIL'}")

        if validation["issues"]:
            lines.append("")
            lines.append("Issues:")
            for issue in validation["issues"]:
                lines.append(f"  - {issue}")

        lines.extend(["", "Per-annotation classification:"])
        for rec in records:
            lines.append(
                f"  {rec['annotation_id']} [{rec['beam_mark']}] "
                f"{rec['clean_text'][:45]}: {rec['semantic_class']} -> {rec['final_status']} "
                f"({rec['semantic_reason']})"
            )

        lines.extend(["", "======================================================================"])
        return "\n".join(lines) + "\n"
