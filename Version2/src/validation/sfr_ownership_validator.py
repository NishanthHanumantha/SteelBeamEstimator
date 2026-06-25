"""Phase D.1.7E — SFR ownership validation using geometry-based scoring."""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.geometry.beam_geometry_classifier import BeamGeometryClassifier

ValidatorStatus = Literal["VALIDATED", "REJECTED", "AMBIGUOUS"]

SCORE_CURVED = 40
SCORE_LEADER = 25
SCORE_BBOX_INSIDE = 15
SCORE_BBOX_ADJACENT = 8
SCORE_DISTANCE_MAX = 30
SCORE_SKETCH_CONSISTENCY = 5
THRESHOLD = 55
AMBIGUITY_MARGIN = 5
BBOX_ADJACENT_MARGIN_MM = 800.0
DISTANCE_FULL_RANGE_MM = 8000.0
MAX_SEARCH_DISTANCE_MM = 20000.0
ASSIGNED_SKETCH_PENALTY = 12
NEAREST_SKETCH_MARGIN_MM = 150.0
ASSIGNED_HORIZONTAL_OFFSET_MM = 2500.0
ASSIGNED_HORIZONTAL_PENALTY = 25


@dataclass(frozen=True)
class SketchContext:
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    bbox: dict[str, float]
    centroid_x: float
    centroid_y: float
    is_curved: bool


class SfrValidationRecord(TypedDict, total=False):
    annotation_id: str
    annotation_type: str
    beam_mark: str
    occurrence_id: int
    sketch_id: str
    raw_text: str
    clean_text: str
    x: float
    y: float
    final_status: str
    ownership_score: int
    validator_status: ValidatorStatus
    validated_beam_mark: Optional[str]
    validated_occurrence_id: Optional[int]
    validated_sketch_id: Optional[str]
    validation_reason: str
    beam_is_curved: bool
    candidate_beams: List[str]
    candidate_scores: List[int]


class SfrValidationReport(TypedDict):
    total_sfr_detected: int
    validated: int
    rejected: int
    ambiguous: int
    curved_beam_matches: int
    confidence_distribution: Dict[str, int]
    false_positive_candidates: List[str]
    false_negative_notes: List[str]
    records: List[SfrValidationRecord]


class SfrOwnershipResult(TypedDict):
    validated_sfr: List[SfrValidationRecord]
    validated_master: List[dict[str, Any]]
    report: SfrValidationReport
    report_text: str


class SfrOwnershipValidator:
    """Validate SIDE_FACE_REINF ownership before Phase D.2 parsing."""

    def validate(
        self,
        final_records: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        sketch_ownership: List[dict[str, Any]],
        dxf_path: str,
        ground_truth_beams: Optional[List[str]] = None,
    ) -> SfrOwnershipResult:
        classifier = BeamGeometryClassifier(dxf_path)
        sketch_contexts = self._build_sketch_contexts(
            sketches, classifier, sketch_ownership
        )

        sfr_items = self._collect_sfr(final_records)
        logger.info("D.1.7E: validating {} SFR annotations", len(sfr_items))

        validation_records: List[SfrValidationRecord] = []

        for idx, item in enumerate(sfr_items):
            record = self._validate_one(item, idx, sketch_contexts, classifier)
            validation_records.append(record)

        validated_master = self._build_validated_master(
            final_records, validation_records
        )

        report = self._build_report(validation_records, ground_truth_beams)
        report_text = self._build_report_text(report)

        return SfrOwnershipResult(
            validated_sfr=validation_records,
            validated_master=validated_master,
            report=report,
            report_text=report_text,
        )

    def _build_sketch_contexts(
        self,
        sketches: List[dict[str, Any]],
        classifier: BeamGeometryClassifier,
        sketch_ownership: List[dict[str, Any]],
    ) -> Dict[str, SketchContext]:
        sketch_to_occurrence: Dict[str, Tuple[str, int]] = {}
        for occ in sketch_ownership:
            beam_mark = str(occ["beam_mark"])
            occurrence_id = int(occ["occurrence_id"])
            for owned in occ.get("owned_sketches", []):
                sketch_to_occurrence[str(owned["sketch_id"])] = (
                    beam_mark,
                    occurrence_id,
                )

        contexts: Dict[str, SketchContext] = {}
        for sk in sketches:
            sketch_id = str(sk["sketch_id"])
            beam_mark = str(sk["beam_mark"])
            occurrence_id = 1
            if sketch_id in sketch_to_occurrence:
                beam_mark, occurrence_id = sketch_to_occurrence[sketch_id]

            bbox = sk["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
            is_curved = classifier.is_curved_beam(sketch_id, bbox)

            contexts[sketch_id] = SketchContext(
                beam_mark=beam_mark,
                occurrence_id=occurrence_id,
                sketch_id=sketch_id,
                bbox=bbox,
                centroid_x=cx,
                centroid_y=cy,
                is_curved=is_curved,
            )
        return contexts

    def _collect_sfr(self, final_records: List[dict[str, Any]]) -> List[dict[str, Any]]:
        items: List[dict[str, Any]] = []
        for sketch_record in final_records:
            for ann in sketch_record.get("annotations", []):
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    continue
                items.append(
                    {
                        "beam_mark": str(sketch_record["beam_mark"]),
                        "occurrence_id": int(sketch_record["occurrence_id"]),
                        "sketch_id": str(sketch_record["sketch_id"]),
                        **ann,
                    }
                )
        return items

    def _validate_one(
        self,
        item: dict[str, Any],
        index: int,
        sketch_contexts: Dict[str, SketchContext],
        classifier: BeamGeometryClassifier,
    ) -> SfrValidationRecord:
        ax = float(item["x"])
        ay = float(item["y"])
        assigned_mark = str(item["beam_mark"])
        assigned_sketch = str(item["sketch_id"])
        assigned_occurrence = int(item["occurrence_id"])

        leader_target = classifier.find_leader_target(ax, ay)
        eval_x, eval_y = leader_target if leader_target else (ax, ay)
        has_leader = leader_target is not None

        sketch_scores: List[Tuple[int, SketchContext, str]] = []
        for ctx in sketch_contexts.values():
            dist = self._distance_to_bbox(eval_x, eval_y, ctx.bbox)
            if dist > MAX_SEARCH_DISTANCE_MM:
                continue
            score, reason_parts = self._score_candidate(
                eval_x,
                eval_y,
                ax,
                ay,
                ctx,
                assigned_sketch,
                has_leader,
                dist,
            )
            sketch_scores.append((score, ctx, reason_parts))

        if not sketch_scores:
            return self._rejected_record(
                item, index, assigned_mark, assigned_sketch, assigned_occurrence,
                "No sketch candidates available",
            )

        nearest_dist = min(
            self._distance_to_bbox(eval_x, eval_y, ctx.bbox)
            for _, ctx, _ in sketch_scores
        )
        adjusted: List[Tuple[int, SketchContext, str]] = []
        for score, ctx, reason in sketch_scores:
            dist = self._distance_to_bbox(eval_x, eval_y, ctx.bbox)
            adjusted_score = score
            adjusted_reason = reason
            if (
                ctx.sketch_id == assigned_sketch
                and dist > nearest_dist + NEAREST_SKETCH_MARGIN_MM
            ):
                adjusted_score = max(0, adjusted_score - ASSIGNED_SKETCH_PENALTY)
                adjusted_reason = f"{reason} - distant assignment penalty"
            if ctx.sketch_id == assigned_sketch:
                inside, _ = self._bbox_relation(eval_x, eval_y, ctx.bbox)
                if not inside:
                    xmin = float(ctx.bbox["xmin"])
                    xmax = float(ctx.bbox["xmax"])
                    dx = max(xmin - eval_x, eval_x - xmax, 0.0)
                    if dx > ASSIGNED_HORIZONTAL_OFFSET_MM:
                        adjusted_score = max(
                            0, adjusted_score - ASSIGNED_HORIZONTAL_PENALTY
                        )
                        adjusted_reason = (
                            f"{adjusted_reason} - horizontal offset penalty"
                        )
            adjusted.append((adjusted_score, ctx, adjusted_reason))

        beam_best: Dict[str, Tuple[int, SketchContext, str]] = {}
        for score, ctx, reason in adjusted:
            mark = ctx.beam_mark
            existing = beam_best.get(mark)
            if existing is None or score > existing[0]:
                beam_best[mark] = (score, ctx, reason)

        candidates = sorted(beam_best.keys(), key=beam_mark_sort_key)
        candidate_scores = [beam_best[m][0] for m in candidates]

        ranked = sorted(adjusted, key=lambda t: t[0], reverse=True)
        best_score, best_ctx, best_reason = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0

        if best_score < THRESHOLD:
            status: ValidatorStatus = "REJECTED"
            reason = f"No beam exceeded ownership threshold (best={best_score})"
            validated_mark = None
            validated_occ = None
            validated_sketch = None
        else:
            win_inside, win_adjacent = self._bbox_relation(
                eval_x, eval_y, best_ctx.bbox
            )
            if (
                best_ctx.beam_mark != assigned_mark
                and not has_leader
                and not win_inside
                and not win_adjacent
            ):
                status = "REJECTED"
                reason = "Cross-beam reassignment without spatial link or leader"
                validated_mark = None
                validated_occ = None
                validated_sketch = None
            elif len(ranked) > 1 and (best_score - second_score) < AMBIGUITY_MARGIN:
                status = "AMBIGUOUS"
                reason = f"Competing sketches within {AMBIGUITY_MARGIN} points"
                validated_mark = None
                validated_occ = None
                validated_sketch = None
            else:
                status = "VALIDATED"
                validated_mark = best_ctx.beam_mark
                validated_occ = best_ctx.occurrence_id
                validated_sketch = best_ctx.sketch_id
                reason = best_reason

        return SfrValidationRecord(
            annotation_id=f"SFR_{index + 1:05d}",
            annotation_type="SIDE_FACE_REINF",
            beam_mark=assigned_mark,
            occurrence_id=assigned_occurrence,
            sketch_id=assigned_sketch,
            raw_text=str(item.get("text", "")),
            clean_text=str(item["clean_text"]),
            x=ax,
            y=ay,
            final_status=str(item.get("final_status", "")),
            ownership_score=best_score,
            validator_status=status,
            validated_beam_mark=validated_mark,
            validated_occurrence_id=validated_occ,
            validated_sketch_id=validated_sketch,
            validation_reason=reason,
            beam_is_curved=best_ctx.is_curved if status == "VALIDATED" else False,
            candidate_beams=candidates,
            candidate_scores=candidate_scores,
        )

    def _rejected_record(
        self,
        item: dict[str, Any],
        index: int,
        assigned_mark: str,
        assigned_sketch: str,
        assigned_occurrence: int,
        validation_reason: str,
    ) -> SfrValidationRecord:
        return SfrValidationRecord(
            annotation_id=f"SFR_{index + 1:05d}",
            annotation_type="SIDE_FACE_REINF",
            beam_mark=assigned_mark,
            occurrence_id=assigned_occurrence,
            sketch_id=assigned_sketch,
            raw_text=str(item.get("text", "")),
            clean_text=str(item["clean_text"]),
            x=float(item["x"]),
            y=float(item["y"]),
            final_status=str(item.get("final_status", "")),
            ownership_score=0,
            validator_status="REJECTED",
            validated_beam_mark=None,
            validated_occurrence_id=None,
            validated_sketch_id=None,
            validation_reason=validation_reason,
            beam_is_curved=False,
            candidate_beams=[],
            candidate_scores=[],
        )

    def _score_candidate(
        self,
        eval_x: float,
        eval_y: float,
        ann_x: float,
        ann_y: float,
        ctx: SketchContext,
        assigned_sketch: str,
        has_leader: bool,
        dist: float,
    ) -> Tuple[int, str]:
        parts: List[str] = []
        score = 0.0

        if ctx.is_curved:
            score += SCORE_CURVED
            parts.append("curved beam")

        if has_leader:
            leader_dist = self._distance_to_bbox(eval_x, eval_y, ctx.bbox)
            if leader_dist < 3000.0:
                score += SCORE_LEADER
                parts.append("leader match")

        inside, adjacent = self._bbox_relation(eval_x, eval_y, ctx.bbox)
        if inside:
            score += SCORE_BBOX_INSIDE
            parts.append("inside sketch")
        elif adjacent:
            score += SCORE_BBOX_ADJACENT
            parts.append("adjacent sketch")

        dist_factor = max(0.0, 1.0 - dist / DISTANCE_FULL_RANGE_MM)
        dist_points = SCORE_DISTANCE_MAX * dist_factor
        if dist_points >= 1.0:
            score += dist_points
            if dist_factor >= 0.55:
                parts.append("close centroid")

        nearest_sketch_dist = self._distance_to_bbox(ann_x, ann_y, ctx.bbox)
        if (
            ctx.sketch_id == assigned_sketch
            and nearest_sketch_dist < DISTANCE_FULL_RANGE_MM
        ):
            score += SCORE_SKETCH_CONSISTENCY
            parts.append("sketch consistency")

        reason = " + ".join(parts) if parts else "low confidence"
        return int(round(score)), reason

    @staticmethod
    def _bbox_relation(
        x: float, y: float, bbox: dict[str, float]
    ) -> Tuple[bool, bool]:
        xmin = float(bbox["xmin"])
        ymin = float(bbox["ymin"])
        xmax = float(bbox["xmax"])
        ymax = float(bbox["ymax"])
        inside = xmin <= x <= xmax and ymin <= y <= ymax
        adj_xmin = xmin - BBOX_ADJACENT_MARGIN_MM
        adj_ymin = ymin - BBOX_ADJACENT_MARGIN_MM
        adj_xmax = xmax + BBOX_ADJACENT_MARGIN_MM
        adj_ymax = ymax + BBOX_ADJACENT_MARGIN_MM
        adjacent = (
            not inside
            and adj_xmin <= x <= adj_xmax
            and adj_ymin <= y <= adj_ymax
        )
        return inside, adjacent

    @staticmethod
    def _distance_to_bbox(x: float, y: float, bbox: dict[str, float]) -> float:
        xmin = float(bbox["xmin"])
        ymin = float(bbox["ymin"])
        xmax = float(bbox["xmax"])
        ymax = float(bbox["ymax"])
        dx = 0.0
        if x < xmin:
            dx = xmin - x
        elif x > xmax:
            dx = x - xmax
        dy = 0.0
        if y < ymin:
            dy = ymin - y
        elif y > ymax:
            dy = y - ymax
        return math.hypot(dx, dy)

    def _sfr_validation_key(
        self,
        ann: dict[str, Any],
        sketch_id: str,
    ) -> Tuple[str, float, float, str]:
        return (
            str(ann["clean_text"]),
            round(float(ann["x"]), 1),
            round(float(ann["y"]), 1),
            sketch_id,
        )

    def _apply_sfr_validation(
        self,
        entry: dict[str, Any],
        val: SfrValidationRecord,
    ) -> dict[str, Any]:
        entry["sfr_validation"] = {
            "ownership_score": val["ownership_score"],
            "validator_status": val["validator_status"],
            "validated_beam_mark": val.get("validated_beam_mark"),
            "validation_reason": val["validation_reason"],
            "beam_is_curved": val["beam_is_curved"],
            "candidate_beams": val["candidate_beams"],
            "candidate_scores": val["candidate_scores"],
        }

        if val["validator_status"] == "VALIDATED":
            entry["beam_mark"] = val["validated_beam_mark"]
            entry["occurrence_id"] = val["validated_occurrence_id"]
            entry["sketch_id"] = val["validated_sketch_id"]
            if entry.get("final_status") == "PARSER_READY":
                entry["final_status"] = "PARSER_READY"
        else:
            entry["final_status"] = "SFR_REJECTED"
        return entry

    def _build_validated_master(
        self,
        final_records: List[dict[str, Any]],
        validation_records: List[SfrValidationRecord],
    ) -> List[dict[str, Any]]:
        sfr_lookup = {
            (
                str(r["clean_text"]),
                round(float(r["x"]), 1),
                round(float(r["y"]), 1),
                str(r["sketch_id"]),
            ): r
            for r in validation_records
        }

        master: List[dict[str, Any]] = []
        transfers: List[Tuple[dict[str, Any], str]] = []

        for sketch_record in final_records:
            sketch_id = str(sketch_record["sketch_id"])
            new_anns: List[dict[str, Any]] = []
            for ann in sketch_record.get("annotations", []):
                entry = dict(ann)
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    new_anns.append(entry)
                    continue

                key = self._sfr_validation_key(ann, sketch_id)
                val = sfr_lookup.get(key)
                if val is None:
                    new_anns.append(entry)
                    continue

                entry = self._apply_sfr_validation(entry, val)
                target_sketch = val.get("validated_sketch_id")
                if (
                    val["validator_status"] == "VALIDATED"
                    and target_sketch
                    and target_sketch != sketch_id
                ):
                    transfers.append((entry, str(target_sketch)))
                else:
                    new_anns.append(entry)

            master.append(
                {
                    "beam_mark": sketch_record["beam_mark"],
                    "occurrence_id": sketch_record["occurrence_id"],
                    "sketch_id": sketch_id,
                    "annotations": new_anns,
                }
            )

        sketch_index = {str(rec["sketch_id"]): rec for rec in master}
        for entry, target_sketch in transfers:
            target = sketch_index.get(target_sketch)
            if target is not None:
                target["annotations"].append(entry)
            else:
                logger.warning(
                    "Validated SFR target sketch missing: {}",
                    target_sketch,
                )

        return master

    def _build_report(
        self,
        records: List[SfrValidationRecord],
        ground_truth_beams: Optional[List[str]],
    ) -> SfrValidationReport:
        validated = sum(1 for r in records if r["validator_status"] == "VALIDATED")
        rejected = sum(1 for r in records if r["validator_status"] == "REJECTED")
        ambiguous = sum(1 for r in records if r["validator_status"] == "AMBIGUOUS")
        curved_matches = sum(
            1 for r in records if r["validator_status"] == "VALIDATED" and r["beam_is_curved"]
        )

        dist: Dict[str, int] = {"0-39": 0, "40-59": 0, "60-79": 0, "80-100": 0}
        for r in records:
            s = r["ownership_score"]
            if s < 40:
                dist["0-39"] += 1
            elif s < 60:
                dist["40-59"] += 1
            elif s < 80:
                dist["60-79"] += 1
            else:
                dist["80-100"] += 1

        fp: List[str] = []
        fn_notes: List[str] = []
        if ground_truth_beams:
            gt_set = set(ground_truth_beams)
            validated_marks = {
                r["validated_beam_mark"]
                for r in records
                if r["validator_status"] == "VALIDATED"
                and r.get("validated_beam_mark")
                and str(r.get("final_status", "")) == "PARSER_READY"
            }
            assigned_marks = {r["beam_mark"] for r in records}
            fp = sorted(validated_marks - gt_set)
            fn_notes = sorted(gt_set - validated_marks - assigned_marks)

        return SfrValidationReport(
            total_sfr_detected=len(records),
            validated=validated,
            rejected=rejected,
            ambiguous=ambiguous,
            curved_beam_matches=curved_matches,
            confidence_distribution=dist,
            false_positive_candidates=fp,
            false_negative_notes=fn_notes,
            records=records,
        )

    def _build_report_text(self, report: SfrValidationReport) -> str:
        lines = [
            "======================================================================",
            "SFR Ownership Validation Report (Phase D.1.7E)",
            "======================================================================",
            "",
            f"Total SFR detected: {report['total_sfr_detected']}",
            f"Validated: {report['validated']}",
            f"Rejected: {report['rejected']}",
            f"Ambiguous: {report['ambiguous']}",
            f"Curved beam matches: {report['curved_beam_matches']}",
            "",
            "Confidence distribution:",
        ]
        for band, count in report["confidence_distribution"].items():
            lines.append(f"  {band}: {count}")

        if report["false_positive_candidates"]:
            lines.append("")
            lines.append("Validated beams not in ground truth reference:")
            for m in report["false_positive_candidates"]:
                lines.append(f"  - {m}")

        if report["false_negative_notes"]:
            lines.append("")
            lines.append("Ground truth beams without validated SFR:")
            for m in report["false_negative_notes"]:
                lines.append(f"  - {m}")

        lines.extend(["", "Per-annotation results:"])
        for rec in report["records"]:
            lines.append(
                f"  {rec['annotation_id']} {rec['clean_text'][:40]}: "
                f"{rec['validator_status']} score={rec['ownership_score']} "
                f"-> {rec.get('validated_beam_mark', 'none')} ({rec['validation_reason']})"
            )

        lines.extend(["", "======================================================================"])
        return "\n".join(lines) + "\n"
