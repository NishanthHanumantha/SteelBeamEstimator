"""Phase D.1.7C — read-only integrity audit of engineering annotations."""

import re
from collections import defaultdict
from typing import Any, Dict, List, Literal, Optional, TypedDict

from loguru import logger

from src.annotations.annotation_type_classifier import AnnotationTypeClassifier

FragmentClass = Literal["VALID_FRAGMENT", "SUSPICIOUS_FRAGMENT"]
StirrupClass = Literal["COMPLETE", "PARTIAL", "INVALID"]
AnchorageClass = Literal["VALID_ANCHORAGE", "SUSPICIOUS_ANCHORAGE"]
SfrClass = Literal["VALID_SFR", "PARTIAL_SFR", "INVALID_SFR"]
DuplicateClass = Literal[
    "EXPECTED_SHARED",
    "DUPLICATE_OWNERSHIP",
    "DUPLICATE_SKETCH_ENTRY",
]
RejectionClass = Literal["CORRECTLY_REJECTED", "POSSIBLE_FALSE_REJECTION"]
ReadinessScore = Literal["PASS", "WARN", "FAIL"]

_SOURCE_FILE = "engineering_annotations.json"

_STIRRUP_COMPLETE = re.compile(
    r"^\d+L?-?Y\d+@(?:\d+(?:/\d+)*)C/C$",
    re.IGNORECASE,
)
_STIRRUP_LEG = re.compile(r"^\d+L", re.IGNORECASE)
_STIRRUP_BAR = re.compile(r"Y\d+", re.IGNORECASE)
_STIRRUP_SPACING = re.compile(r"@.*C/C", re.IGNORECASE)

_ANCHORAGE_VALID = re.compile(r"^Ld(?:\+\d+db)?$", re.IGNORECASE)
_ANCHORAGE_SUSPICIOUS = re.compile(
    r"^(d|db|Ld\+|\+\d+db)$",
    re.IGNORECASE,
)

_SFR_KEYWORD = re.compile(
    r"SIDE\s*\.?\s*FACE|S\.F\.R|(?:^|[^A-Z])SFR(?:[^A-Z]|$)|ON BOTH FACE",
    re.IGNORECASE,
)
_SFR_BAR = re.compile(r"\d+-?Y\d+", re.IGNORECASE)

_VALID_FRAGMENTS = frozenset({"Ld"})

_FALSE_REJECTION_MARKERS = [
    re.compile(r"@"),
    re.compile(r"C/C", re.IGNORECASE),
    re.compile(r"\bLd\b", re.IGNORECASE),
    re.compile(r"db", re.IGNORECASE),
    re.compile(r"Y\d+", re.IGNORECASE),
    re.compile(r"S\.F\.R", re.IGNORECASE),
    re.compile(r"SIDE\s*FACE", re.IGNORECASE),
]
_TRUNCATED_FRAGMENT = re.compile(r"^d$", re.IGNORECASE)

_ENGINEERING_TYPES = frozenset(
    {"BAR", "STIRRUP", "ANCHORAGE", "SIDE_FACE_REINF"}
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


class FragmentRecord(TypedDict):
    fragment_text: str
    annotation_type: str
    beam_mark: str
    sketch_id: str
    source_file: str
    reason: str
    classification: FragmentClass
    x: float
    y: float


class StirrupRecord(TypedDict):
    clean_text: str
    beam_mark: str
    sketch_id: str
    classification: StirrupClass
    leg_count: Optional[str]
    bar_dia: Optional[str]
    spacing_pattern: Optional[str]
    x: float
    y: float


class AnchorageRecord(TypedDict):
    clean_text: str
    beam_mark: str
    sketch_id: str
    classification: AnchorageClass
    x: float
    y: float


class SfrRecord(TypedDict):
    clean_text: str
    beam_mark: str
    sketch_id: str
    classification: SfrClass
    contains_bar_info: bool
    contains_side_face_keyword: bool
    x: float
    y: float


class DuplicateRecord(TypedDict):
    clean_text: str
    x: float
    y: float
    classification: DuplicateClass
    owners: List[Dict[str, Any]]


class TypeMismatchRecord(TypedDict):
    text: str
    assigned_type: str
    expected_type: str
    beam_mark: str
    sketch_id: str
    x: float
    y: float


class RejectedReviewRecord(TypedDict):
    clean_text: str
    annotation_type: str
    beam_mark: str
    sketch_id: str
    classification: RejectionClass
    matched_markers: List[str]
    rejection_reason: str
    x: float
    y: float


class ParserReadiness(TypedDict):
    total_engineering_annotations: int
    parser_ready_annotations: int
    questionable_annotations: int
    questionable_pct: float
    readiness_score: ReadinessScore
    by_type: Dict[str, Dict[str, int]]


class IntegritySummary(TypedDict):
    truncated_fragments_found: int
    suspicious_fragments_found: int
    incomplete_stirrups_found: int
    invalid_stirrups_found: int
    invalid_anchorage_entries_found: int
    suspicious_anchorage_entries_found: int
    invalid_sfr_entries_found: int
    partial_sfr_entries_found: int
    duplicate_ownership_issues: int
    duplicate_sketch_entries: int
    expected_shared_entries: int
    type_mismatches: int
    false_rejections: int
    parser_readiness_score: ReadinessScore
    recommendation: str


class AuditResult(TypedDict):
    fragments: List[FragmentRecord]
    stirrups: Dict[str, Any]
    anchorage: Dict[str, Any]
    sfr: Dict[str, Any]
    duplicates: List[DuplicateRecord]
    type_consistency: Dict[str, Any]
    rejected_review: Dict[str, Any]
    parser_readiness: ParserReadiness
    summary: IntegritySummary
    report_text: str


class EngineeringAnnotationIntegrityAuditor:
    """Audit engineering_annotations.json for parser-readiness before Phase D.2."""

    def __init__(self) -> None:
        self._classifier = AnnotationTypeClassifier()

    def audit(
        self,
        engineering_records: List[dict[str, Any]],
        rejected_annotations: List[dict[str, Any]],
        types_extended: Optional[List[dict[str, Any]]] = None,
    ) -> AuditResult:
        flat = self._flatten(engineering_records)
        logger.info("Integrity audit: {} engineering annotations", len(flat))

        fragments = self._audit_fragments(flat)
        stirrup_report = self._audit_stirrups(flat)
        anchorage_report = self._audit_anchorage(flat)
        sfr_report = self._audit_sfr(flat)
        duplicates = self._audit_duplicates(flat)
        type_report = self._audit_type_consistency(flat)
        rejected_report = self._audit_rejected(rejected_annotations)
        parser_readiness = self._assess_parser_readiness(
            flat,
            fragments,
            stirrup_report,
            anchorage_report,
            sfr_report,
            type_report,
        )
        summary = self._build_summary(
            fragments,
            stirrup_report,
            anchorage_report,
            sfr_report,
            duplicates,
            type_report,
            rejected_report,
            parser_readiness,
        )
        report_text = self._build_report_text(summary, parser_readiness)

        return AuditResult(
            fragments=fragments,
            stirrups=stirrup_report,
            anchorage=anchorage_report,
            sfr=sfr_report,
            duplicates=duplicates,
            type_consistency=type_report,
            rejected_review=rejected_report,
            parser_readiness=parser_readiness,
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
                for key in ("layer", "ownership_source", "engineering_source"):
                    if key in item:
                        entry[key] = str(item[key])
                flat.append(entry)
        return flat

    def _audit_fragments(self, flat: List[FlatAnnotation]) -> List[FragmentRecord]:
        records: List[FragmentRecord] = []
        for item in flat:
            text = item["clean_text"].strip()
            if len(text) > 3:
                continue
            if text in _VALID_FRAGMENTS:
                classification: FragmentClass = "VALID_FRAGMENT"
                reason = "Known complete short engineering token"
            else:
                classification = "SUSPICIOUS_FRAGMENT"
                reason = f"Short fragment (len={len(text)}) not a known standalone token"
            records.append(
                FragmentRecord(
                    fragment_text=text,
                    annotation_type=item["annotation_type"],
                    beam_mark=item["beam_mark"],
                    sketch_id=item["sketch_id"],
                    source_file=_SOURCE_FILE,
                    reason=reason,
                    classification=classification,
                    x=item["x"],
                    y=item["y"],
                )
            )
        return records

    def _audit_stirrups(self, flat: List[FlatAnnotation]) -> Dict[str, Any]:
        records: List[StirrupRecord] = []
        counts = {"COMPLETE": 0, "PARTIAL": 0, "INVALID": 0}
        for item in flat:
            if item["annotation_type"] != "STIRRUP":
                continue
            text = item["clean_text"].strip()
            leg_match = _STIRRUP_LEG.search(text)
            bar_match = _STIRRUP_BAR.search(text)
            spacing_match = _STIRRUP_SPACING.search(text)

            if _STIRRUP_COMPLETE.match(text):
                classification: StirrupClass = "COMPLETE"
            elif leg_match and bar_match and spacing_match:
                classification = "COMPLETE"
            elif bar_match or spacing_match or leg_match:
                classification = "PARTIAL"
            else:
                classification = "INVALID"

            counts[classification] += 1
            records.append(
                StirrupRecord(
                    clean_text=text,
                    beam_mark=item["beam_mark"],
                    sketch_id=item["sketch_id"],
                    classification=classification,
                    leg_count=leg_match.group(0) if leg_match else None,
                    bar_dia=bar_match.group(0) if bar_match else None,
                    spacing_pattern=spacing_match.group(0) if spacing_match else None,
                    x=item["x"],
                    y=item["y"],
                )
            )
        return {
            "total_stirrups": len(records),
            "counts": counts,
            "records": records,
        }

    def _audit_anchorage(self, flat: List[FlatAnnotation]) -> Dict[str, Any]:
        records: List[AnchorageRecord] = []
        counts = {"VALID_ANCHORAGE": 0, "SUSPICIOUS_ANCHORAGE": 0}
        for item in flat:
            if item["annotation_type"] != "ANCHORAGE":
                continue
            text = item["clean_text"].strip()
            if _ANCHORAGE_VALID.match(text):
                classification: AnchorageClass = "VALID_ANCHORAGE"
            elif _ANCHORAGE_SUSPICIOUS.match(text):
                classification = "SUSPICIOUS_ANCHORAGE"
            else:
                classification = "SUSPICIOUS_ANCHORAGE"
            counts[classification] += 1
            records.append(
                AnchorageRecord(
                    clean_text=text,
                    beam_mark=item["beam_mark"],
                    sketch_id=item["sketch_id"],
                    classification=classification,
                    x=item["x"],
                    y=item["y"],
                )
            )
        return {
            "total_anchorage": len(records),
            "counts": counts,
            "records": records,
        }

    def _audit_sfr(self, flat: List[FlatAnnotation]) -> Dict[str, Any]:
        records: List[SfrRecord] = []
        counts = {"VALID_SFR": 0, "PARTIAL_SFR": 0, "INVALID_SFR": 0}
        for item in flat:
            if item["annotation_type"] != "SIDE_FACE_REINF":
                continue
            text = item["clean_text"].strip()
            has_keyword = bool(_SFR_KEYWORD.search(text))
            has_bar = bool(_SFR_BAR.search(text))
            note_like = bool(
                re.search(r"DETAIL|SECTION|CURVED|DEPTH\s*>", text, re.IGNORECASE)
            )

            if has_keyword and has_bar:
                classification: SfrClass = "VALID_SFR"
            elif has_keyword and not note_like:
                classification = "PARTIAL_SFR"
            elif has_keyword and note_like:
                classification = "PARTIAL_SFR"
            else:
                classification = "INVALID_SFR"

            counts[classification] += 1
            records.append(
                SfrRecord(
                    clean_text=text,
                    beam_mark=item["beam_mark"],
                    sketch_id=item["sketch_id"],
                    classification=classification,
                    contains_bar_info=has_bar,
                    contains_side_face_keyword=has_keyword,
                    x=item["x"],
                    y=item["y"],
                )
            )
        return {
            "total_sfr": len(records),
            "counts": counts,
            "records": records,
        }

    def _audit_duplicates(self, flat: List[FlatAnnotation]) -> List[DuplicateRecord]:
        by_key: Dict[tuple[str, float, float], List[FlatAnnotation]] = defaultdict(list)
        by_sketch_key: Dict[tuple[str, str, float, float], int] = defaultdict(int)

        for item in flat:
            key = (item["clean_text"], item["x"], item["y"])
            by_key[key].append(item)
            sketch_key = (
                item["sketch_id"],
                item["clean_text"],
                item["x"],
                item["y"],
            )
            by_sketch_key[sketch_key] += 1

        duplicates: List[DuplicateRecord] = []
        for key, owners in by_key.items():
            clean_text, x, y = key
            if len(owners) <= 1:
                continue

            sketch_ids = {o["sketch_id"] for o in owners}
            occurrence_ids = {o["occurrence_id"] for o in owners}
            beam_marks = {o["beam_mark"] for o in owners}

            sketch_dup = any(
                by_sketch_key[(o["sketch_id"], clean_text, x, y)] > 1
                for o in owners
            )

            if sketch_dup:
                classification: DuplicateClass = "DUPLICATE_SKETCH_ENTRY"
            elif len(sketch_ids) > 1:
                if len(beam_marks) == 1 and len(occurrence_ids) > 1:
                    classification = "EXPECTED_SHARED"
                else:
                    classification = "DUPLICATE_OWNERSHIP"
            elif len(occurrence_ids) > 1:
                classification = "EXPECTED_SHARED"
            else:
                classification = "DUPLICATE_SKETCH_ENTRY"

            owner_info = [
                {
                    "beam_mark": o["beam_mark"],
                    "occurrence_id": o["occurrence_id"],
                    "sketch_id": o["sketch_id"],
                }
                for o in owners
            ]
            duplicates.append(
                DuplicateRecord(
                    clean_text=clean_text,
                    x=x,
                    y=y,
                    classification=classification,
                    owners=owner_info,
                )
            )
        return duplicates

    def _audit_type_consistency(self, flat: List[FlatAnnotation]) -> Dict[str, Any]:
        mismatches: List[TypeMismatchRecord] = []
        for item in flat:
            _, _, expected = self._classifier.classify(item["text"])
            assigned = item["annotation_type"]
            if expected not in _ENGINEERING_TYPES:
                continue
            if assigned != expected:
                mismatches.append(
                    TypeMismatchRecord(
                        text=item["clean_text"],
                        assigned_type=assigned,
                        expected_type=expected,
                        beam_mark=item["beam_mark"],
                        sketch_id=item["sketch_id"],
                        x=item["x"],
                        y=item["y"],
                    )
                )
        return {
            "total_checked": len(flat),
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }

    def _audit_rejected(
        self, rejected_annotations: List[dict[str, Any]]
    ) -> Dict[str, Any]:
        records: List[RejectedReviewRecord] = []
        counts = {"CORRECTLY_REJECTED": 0, "POSSIBLE_FALSE_REJECTION": 0}
        for item in rejected_annotations:
            clean_text = str(item["clean_text"])
            matched: List[str] = []
            for pattern in _FALSE_REJECTION_MARKERS:
                if pattern.search(clean_text):
                    matched.append(pattern.pattern)

            is_false = bool(matched) or _TRUNCATED_FRAGMENT.match(clean_text.strip())
            classification: RejectionClass = (
                "POSSIBLE_FALSE_REJECTION" if is_false else "CORRECTLY_REJECTED"
            )
            counts[classification] += 1
            records.append(
                RejectedReviewRecord(
                    clean_text=clean_text,
                    annotation_type=str(item.get("annotation_type", "")),
                    beam_mark=str(item.get("beam_mark", "")),
                    sketch_id=str(item.get("sketch_id", "")),
                    classification=classification,
                    matched_markers=matched,
                    rejection_reason=str(item.get("rejection_reason", "")),
                    x=round(float(item["x"]), 1),
                    y=round(float(item["y"]), 1),
                )
            )
        false_records = [r for r in records if r["classification"] == "POSSIBLE_FALSE_REJECTION"]
        return {
            "total_rejected": len(records),
            "counts": counts,
            "false_rejection_count": len(false_records),
            "records": records,
            "false_rejections": false_records,
        }

    def _assess_parser_readiness(
        self,
        flat: List[FlatAnnotation],
        fragments: List[FragmentRecord],
        stirrup_report: Dict[str, Any],
        anchorage_report: Dict[str, Any],
        sfr_report: Dict[str, Any],
        type_report: Dict[str, Any],
    ) -> ParserReadiness:
        questionable_ids: set[tuple[str, str, float, float]] = set()

        for rec in fragments:
            if rec["classification"] == "SUSPICIOUS_FRAGMENT":
                questionable_ids.add(
                    (rec["sketch_id"], rec["fragment_text"], rec["x"], rec["y"])
                )

        for rec in stirrup_report["records"]:
            if rec["classification"] in ("PARTIAL", "INVALID"):
                questionable_ids.add(
                    (rec["sketch_id"], rec["clean_text"], rec["x"], rec["y"])
                )

        for rec in anchorage_report["records"]:
            if rec["classification"] == "SUSPICIOUS_ANCHORAGE":
                questionable_ids.add(
                    (rec["sketch_id"], rec["clean_text"], rec["x"], rec["y"])
                )

        for rec in sfr_report["records"]:
            if rec["classification"] in ("PARTIAL_SFR", "INVALID_SFR"):
                questionable_ids.add(
                    (rec["sketch_id"], rec["clean_text"], rec["x"], rec["y"])
                )

        for rec in type_report["mismatches"]:
            questionable_ids.add(
                (rec["sketch_id"], rec["text"], rec["x"], rec["y"])
            )

        total = len(flat)
        questionable = len(questionable_ids)
        questionable_pct = (questionable / total * 100) if total else 0.0

        incomplete_stirrups = stirrup_report["counts"]["PARTIAL"] + stirrup_report["counts"]["INVALID"]
        suspicious_anchorage = anchorage_report["counts"]["SUSPICIOUS_ANCHORAGE"]
        type_mismatches = type_report["mismatch_count"]

        if questionable_pct > 5:
            score: ReadinessScore = "FAIL"
        elif questionable_pct >= 2 or (
            incomplete_stirrups > 0
            or suspicious_anchorage > 0
            or type_mismatches > 0
        ):
            score = "WARN"
        else:
            score = "PASS"

        by_type: Dict[str, Dict[str, int]] = {}
        for ann_type in _ENGINEERING_TYPES:
            type_items = [i for i in flat if i["annotation_type"] == ann_type]
            type_questionable = sum(
                1
                for i in type_items
                if (i["sketch_id"], i["clean_text"], i["x"], i["y"]) in questionable_ids
            )
            by_type[ann_type] = {
                "total": len(type_items),
                "parser_ready": len(type_items) - type_questionable,
                "questionable": type_questionable,
            }

        return ParserReadiness(
            total_engineering_annotations=total,
            parser_ready_annotations=total - questionable,
            questionable_annotations=questionable,
            questionable_pct=round(questionable_pct, 2),
            readiness_score=score,
            by_type=by_type,
        )

    def _build_summary(
        self,
        fragments: List[FragmentRecord],
        stirrup_report: Dict[str, Any],
        anchorage_report: Dict[str, Any],
        sfr_report: Dict[str, Any],
        duplicates: List[DuplicateRecord],
        type_report: Dict[str, Any],
        rejected_report: Dict[str, Any],
        parser_readiness: ParserReadiness,
    ) -> IntegritySummary:
        suspicious_fragments = sum(
            1 for f in fragments if f["classification"] == "SUSPICIOUS_FRAGMENT"
        )
        dup_ownership = sum(
            1 for d in duplicates if d["classification"] == "DUPLICATE_OWNERSHIP"
        )
        dup_sketch = sum(
            1 for d in duplicates if d["classification"] == "DUPLICATE_SKETCH_ENTRY"
        )
        expected_shared = sum(
            1 for d in duplicates if d["classification"] == "EXPECTED_SHARED"
        )

        score = parser_readiness["readiness_score"]
        false_rejections = rejected_report["false_rejection_count"]
        recommendation = (
            "READY_FOR_D2"
            if score == "PASS" and false_rejections == 0
            else "FIX_REQUIRED_BEFORE_D2"
        )

        return IntegritySummary(
            truncated_fragments_found=len(fragments),
            suspicious_fragments_found=suspicious_fragments,
            incomplete_stirrups_found=stirrup_report["counts"]["PARTIAL"],
            invalid_stirrups_found=stirrup_report["counts"]["INVALID"],
            invalid_anchorage_entries_found=0,
            suspicious_anchorage_entries_found=anchorage_report["counts"][
                "SUSPICIOUS_ANCHORAGE"
            ],
            invalid_sfr_entries_found=sfr_report["counts"]["INVALID_SFR"],
            partial_sfr_entries_found=sfr_report["counts"]["PARTIAL_SFR"],
            duplicate_ownership_issues=dup_ownership,
            duplicate_sketch_entries=dup_sketch,
            expected_shared_entries=expected_shared,
            type_mismatches=type_report["mismatch_count"],
            false_rejections=false_rejections,
            parser_readiness_score=score,
            recommendation=recommendation,
        )

    def _build_report_text(
        self,
        summary: IntegritySummary,
        parser_readiness: ParserReadiness,
    ) -> str:
        lines = [
            "======================================================================",
            "Engineering Annotation Integrity Audit (Phase D.1.7C)",
            "======================================================================",
            "",
            "1. Truncated fragments found: "
            f"{summary['truncated_fragments_found']}",
            f"   Suspicious fragments: {summary['suspicious_fragments_found']}",
            "",
            "2. Incomplete stirrups found: "
            f"{summary['incomplete_stirrups_found']}",
            f"   Invalid stirrups: {summary['invalid_stirrups_found']}",
            "",
            "3. Invalid anchorage entries: "
            f"{summary['invalid_anchorage_entries_found']}",
            f"   Suspicious anchorage: "
            f"{summary['suspicious_anchorage_entries_found']}",
            "",
            "4. Invalid SFR entries: "
            f"{summary['invalid_sfr_entries_found']}",
            f"   Partial SFR entries: {summary['partial_sfr_entries_found']}",
            "",
            "5. Duplicate ownership issues: "
            f"{summary['duplicate_ownership_issues']}",
            f"   Duplicate sketch entries: {summary['duplicate_sketch_entries']}",
            f"   Expected shared: {summary['expected_shared_entries']}",
            "",
            f"6. Type mismatches: {summary['type_mismatches']}",
            "",
            f"7. False rejections: {summary['false_rejections']}",
            "",
            "8. Parser readiness:",
            f"   Total: {parser_readiness['total_engineering_annotations']}",
            f"   Parser-ready: {parser_readiness['parser_ready_annotations']}",
            f"   Questionable: {parser_readiness['questionable_annotations']}",
            f"   Questionable %: {parser_readiness['questionable_pct']}%",
            "",
            "9. Parser readiness score: "
            f"{summary['parser_readiness_score']}",
            "",
            f"Recommendation: {summary['recommendation']}",
            "",
            "======================================================================",
        ]
        return "\n".join(lines) + "\n"
