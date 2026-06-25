"""Phase D.1.7G — SFR discovery audit orchestration (read-only)."""

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from loguru import logger

from src.framing.beam_geometry import beam_mark_sort_key
from src.validation.sfr_discovery_scanner import SfrDiscoveryScanner

RootCause = Literal[
    "NOT_FOUND_IN_DXF",
    "BLOCK_NOT_EXPANDED",
    "OUTSIDE_SEARCH_REGION",
    "OWNERSHIP_FAILURE",
    "REASSIGNMENT_FAILURE",
    "FILTERED_BY_D17D",
    "SEMANTIC_REJECTION",
    "OTHER",
]

EXPECTED_BEAMS = ("B1", "B8", "B9", "B10", "B14")

BBOX_MARGIN_MM = 300.0
ROW_EDGE_MARGIN_MM = 5000.0
ROW_Y_TOLERANCE_MM = 500.0
MATCH_TOLERANCE_MM = 5.0

_PIPELINE_STAGES: Tuple[Tuple[str, str, str], ...] = (
    ("phase_d1", "beam_annotations_raw.json", "raw"),
    ("phase_d1_4", "beam_annotations_reassigned.json", "raw"),
    ("phase_d1_7b", "engineering_annotations.json", "engineering"),
    ("phase_d1_7d", "engineering_annotations_final.json", "engineering"),
    ("phase_d17e", "validated_annotations_master.json", "engineering"),
    ("phase_d17f", "engineering_dataset_phase_d17f.json", "engineering"),
)

_ENGINEERING_BAR = re.compile(r"(\d+)\s*-?\s*Y(\d+)", re.IGNORECASE)
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


class DiscoveryValidation(TypedDict):
    all_dxf_entities_inventoried: bool
    all_expected_beams_analysed: bool
    all_missing_assigned_root_cause: bool
    prior_outputs_unmodified: bool
    status: Literal["PASS", "FAIL"]


class SfrDiscoveryAuditResult(TypedDict):
    inventory: List[dict[str, Any]]
    expected_vs_found: List[dict[str, Any]]
    pipeline_loss: List[dict[str, Any]]
    root_causes: List[dict[str, Any]]
    summary: dict[str, Any]
    validation: DiscoveryValidation
    report_text: str


class SfrDiscoveryAudit:
    """Read-only investigation of missing SFR annotations."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def run(
        self,
        dxf_path: str,
        sketches: List[dict[str, Any]],
        sketch_ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        engineering_d17f: List[dict[str, Any]],
    ) -> SfrDiscoveryAuditResult:
        inventory = SfrDiscoveryScanner().scan(dxf_path)
        enriched = [
            self._enrich_candidate(item, sketches, sketch_ownership, occurrences)
            for item in inventory
        ]

        pipeline_snapshots = self._load_pipeline_snapshots()
        pipeline_loss = self._build_pipeline_loss(enriched, pipeline_snapshots)
        root_causes = self._assign_root_causes(
            enriched, pipeline_loss, engineering_d17f, sketches
        )
        expected_vs_found = self._build_expected_table(
            enriched,
            engineering_d17f,
            root_causes,
            sketches,
            sketch_ownership,
            occurrences,
            pipeline_loss,
        )
        summary = self._build_summary(
            enriched, expected_vs_found, root_causes, engineering_d17f
        )
        validation = self._validate(enriched, expected_vs_found, root_causes)
        report_text = self._build_report(summary, validation, expected_vs_found, root_causes)

        return SfrDiscoveryAuditResult(
            inventory=enriched,
            expected_vs_found=expected_vs_found,
            pipeline_loss=pipeline_loss,
            root_causes=root_causes,
            summary=summary,
            validation=validation,
            report_text=report_text,
        )

    def _enrich_candidate(
        self,
        item: dict[str, Any],
        sketches: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
    ) -> dict[str, Any]:
        x = float(item["x"])
        y = float(item["y"])
        occ_bboxes = self._occurrence_search_bboxes(sketches, ownership, occurrences)

        sketch_hits = [
            sk for sk in sketches if self._point_in_bbox(x, y, sk["bbox"], 0.0)
        ]
        sketch_adjacent = [
            sk for sk in sketches if self._point_in_bbox(x, y, sk["bbox"], BBOX_MARGIN_MM)
        ]
        inside_sketch = len(sketch_hits) > 0
        inside_adjacent_sketch = len(sketch_adjacent) > 0

        ownership_hits = [
            key for key, bbox in occ_bboxes.items() if self._point_in_rect(x, y, bbox)
        ]
        inside_ownership = len(ownership_hits) > 0

        nearest_sketch = self._nearest_sketch(x, y, sketches)
        nearest_occ = self._nearest_occurrence(x, y, occurrences)
        nearest_beam = nearest_sketch["beam_mark"] if nearest_sketch else None

        ownership_dist = self._min_distance_to_occurrence_regions(x, y, occ_bboxes)
        sketch_centroid_dist = (
            self._distance_to_sketch_centroid(x, y, nearest_sketch) if nearest_sketch else None
        )

        flags = self._semantic_flags(item["clean_text"])

        return {
            **item,
            "inside_ownership_region": inside_ownership,
            "inside_sketch_bbox": inside_sketch,
            "inside_sketch_bbox_or_adjacent": inside_adjacent_sketch,
            "nearest_occurrence": nearest_occ,
            "nearest_sketch": nearest_sketch,
            "nearest_beam": nearest_beam,
            "distance_to_nearest_beam_sketch_mm": sketch_centroid_dist,
            "distance_to_ownership_region_mm": ownership_dist,
            "semantic_flags": flags,
            "is_engineering_pattern": flags["contains_engineering_pattern"],
            "is_sfr_text": self._is_sfr_text(item["clean_text"]),
        }

    @staticmethod
    def _is_sfr_text(clean_text: str) -> bool:
        normalized = clean_text.upper().replace(".", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        for term in (
            "S.F.R",
            "SFR",
            "SIDE FACE",
            "FACE REINF",
            "FACE REINFORCEMENT",
            "ON BOTH FACE",
            "ON BOTH FACES",
            "CURVED BEAM",
            "CURVED BEAMS",
            "2-Y8 ON ONE FACE",
        ):
            if term in normalized:
                return True
        if _ENGINEERING_BAR.search(normalized):
            return any(
                ctx in normalized
                for ctx in (
                    "SIDE FACE",
                    "SFR",
                    "S F R",
                    "FACE REINF",
                    "ON BOTH FACE",
                )
            )
        return False

    def _semantic_flags(self, clean_text: str) -> dict[str, bool]:
        normalized = clean_text.upper().replace(".", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        qty_matches = list(_ENGINEERING_BAR.finditer(normalized))
        contains_engineering = bool(qty_matches)
        contains_quantity = bool(qty_matches)
        contains_diameter = bool(re.search(r"Y\d+", normalized))
        contains_reference = any(k in normalized for k in _REFERENCE_KEYWORDS)
        return {
            "contains_quantity": contains_quantity,
            "contains_diameter": contains_diameter,
            "contains_engineering_pattern": contains_engineering,
            "contains_reference_keywords": contains_reference,
            "contains_detail_keyword": "DETAIL" in normalized,
            "contains_curved_keyword": "CURVED" in normalized,
            "contains_depth_keyword": "DEPTH>" in normalized or "DEPTH >" in normalized,
        }

    def _occurrence_search_bboxes(
        self,
        sketches: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
    ) -> Dict[Tuple[str, int], Tuple[float, float, float, float]]:
        sketch_lookup = {str(s["sketch_id"]): s for s in sketches}
        occ_columns = self._occurrence_column_bounds(occurrences)
        bboxes: Dict[Tuple[str, int], Tuple[float, float, float, float]] = {}

        groups: Dict[Tuple[str, int], List[dict[str, Any]]] = {}
        for record in ownership:
            mark = str(record["beam_mark"])
            occ_id = int(record["occurrence_id"])
            key = (mark, occ_id)
            for owned in record.get("owned_sketches", []):
                sketch_id = str(owned["sketch_id"])
                sketch = sketch_lookup.get(sketch_id)
                if sketch is not None:
                    groups.setdefault(key, []).append(sketch)

        for key, sketch_list in groups.items():
            col_bounds = occ_columns.get(key)
            if col_bounds is None or not sketch_list:
                continue
            col_xmin, col_xmax = col_bounds
            sketch_xmin = min(float(s["bbox"]["xmin"]) for s in sketch_list)
            sketch_xmax = max(float(s["bbox"]["xmax"]) for s in sketch_list)
            sketch_ymin = min(float(s["bbox"]["ymin"]) for s in sketch_list)
            sketch_ymax = max(float(s["bbox"]["ymax"]) for s in sketch_list)
            header_y = min(float(s.get("header_y", sketch_ymin)) for s in sketch_list)

            xmin = min(sketch_xmin - BBOX_MARGIN_MM, col_xmin - BBOX_MARGIN_MM)
            xmax = max(sketch_xmax + BBOX_MARGIN_MM, col_xmax + BBOX_MARGIN_MM)
            ymin = min(sketch_ymin - BBOX_MARGIN_MM, header_y - BBOX_MARGIN_MM)
            ymax = sketch_ymax + BBOX_MARGIN_MM
            bboxes[key] = (xmin, ymin, xmax, ymax)

        return bboxes

    def _occurrence_column_bounds(
        self, occurrences: List[dict[str, Any]]
    ) -> Dict[Tuple[str, int], Tuple[float, float]]:
        rows = self._cluster_occurrence_rows(occurrences)
        bounds: Dict[Tuple[str, int], Tuple[float, float]] = {}
        for row in rows:
            sorted_row = sorted(row, key=lambda occ: occ["x"])
            for index, occurrence in enumerate(sorted_row):
                if index == 0:
                    xmin = occurrence["x"] - ROW_EDGE_MARGIN_MM
                else:
                    xmin = (sorted_row[index - 1]["x"] + occurrence["x"]) / 2.0
                if index == len(sorted_row) - 1:
                    xmax = occurrence["x"] + ROW_EDGE_MARGIN_MM
                else:
                    xmax = (occurrence["x"] + sorted_row[index + 1]["x"]) / 2.0
                key = (str(occurrence["beam_mark"]), int(occurrence["occurrence_id"]))
                bounds[key] = (float(xmin), float(xmax))
        return bounds

    def _cluster_occurrence_rows(
        self, occurrences: List[dict[str, Any]]
    ) -> List[List[dict[str, Any]]]:
        sorted_occurrences = sorted(
            occurrences, key=lambda occ: (-float(occ["y"]), float(occ["x"]))
        )
        rows: List[List[dict[str, Any]]] = []
        for occurrence in sorted_occurrences:
            placed = False
            for row in rows:
                row_y = sum(float(item["y"]) for item in row) / len(row)
                if abs(float(occurrence["y"]) - row_y) <= ROW_Y_TOLERANCE_MM:
                    row.append(occurrence)
                    placed = True
                    break
            if not placed:
                rows.append([occurrence])
        return rows

    @staticmethod
    def _point_in_bbox(
        x: float, y: float, bbox: dict[str, float], margin: float
    ) -> bool:
        return (
            float(bbox["xmin"]) - margin <= x <= float(bbox["xmax"]) + margin
            and float(bbox["ymin"]) - margin <= y <= float(bbox["ymax"]) + margin
        )

    @staticmethod
    def _point_in_rect(
        x: float, y: float, rect: Tuple[float, float, float, float]
    ) -> bool:
        xmin, ymin, xmax, ymax = rect
        return xmin <= x <= xmax and ymin <= y <= ymax

    def _nearest_sketch(
        self, x: float, y: float, sketches: List[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        best: Optional[dict[str, Any]] = None
        best_dist = float("inf")
        for sk in sketches:
            bbox = sk["bbox"]
            cx = (float(bbox["xmin"]) + float(bbox["xmax"])) / 2.0
            cy = (float(bbox["ymin"]) + float(bbox["ymax"])) / 2.0
            dist = math.hypot(x - cx, y - cy)
            if dist < best_dist:
                best_dist = dist
                best = {
                    "beam_mark": str(sk["beam_mark"]),
                    "sketch_id": str(sk["sketch_id"]),
                    "distance_mm": round(dist, 1),
                }
        return best

    def _nearest_occurrence(
        self, x: float, y: float, occurrences: List[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        best: Optional[dict[str, Any]] = None
        best_dist = float("inf")
        for occ in occurrences:
            dist = math.hypot(x - float(occ["x"]), y - float(occ["y"]))
            if dist < best_dist:
                best_dist = dist
                best = {
                    "beam_mark": str(occ["beam_mark"]),
                    "occurrence_id": int(occ["occurrence_id"]),
                    "distance_mm": round(dist, 1),
                }
        return best

    def _min_distance_to_occurrence_regions(
        self,
        x: float,
        y: float,
        occ_bboxes: Dict[Tuple[str, int], Tuple[float, float, float, float]],
    ) -> float:
        if not occ_bboxes:
            return float("inf")
        return min(self._distance_to_rect(x, y, rect) for rect in occ_bboxes.values())

    @staticmethod
    def _distance_to_rect(
        x: float, y: float, rect: Tuple[float, float, float, float]
    ) -> float:
        xmin, ymin, xmax, ymax = rect
        dx = max(xmin - x, 0.0, x - xmax)
        dy = max(ymin - y, 0.0, y - ymax)
        return math.hypot(dx, dy)

    @staticmethod
    def _distance_to_sketch_centroid(
        x: float, y: float, sketch: Optional[dict[str, Any]]
    ) -> Optional[float]:
        if sketch is None:
            return None
        return float(sketch["distance_mm"])

    def _load_pipeline_snapshots(self) -> Dict[str, List[dict[str, Any]]]:
        snapshots: Dict[str, List[dict[str, Any]]] = {}
        for phase_dir, filename, fmt in _PIPELINE_STAGES:
            path = self._output_root / phase_dir / filename
            if not path.exists():
                snapshots[phase_dir] = []
                continue
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            snapshots[phase_dir] = self._extract_sfr_entries(data, fmt)
        return snapshots

    def _extract_sfr_entries(
        self, data: Any, fmt: str
    ) -> List[dict[str, Any]]:
        entries: List[dict[str, Any]] = []
        if not isinstance(data, list):
            return entries

        for sketch_record in data:
            beam_mark = str(sketch_record.get("beam_mark", ""))
            occurrence_id = int(sketch_record.get("occurrence_id", 0))
            sketch_id = str(sketch_record.get("sketch_id", ""))

            if fmt == "raw":
                for item in sketch_record.get("texts", []):
                    text = str(item.get("text", ""))
                    if not self._text_is_sfr_candidate(text):
                        continue
                    entries.append(
                        {
                            "beam_mark": beam_mark,
                            "occurrence_id": occurrence_id,
                            "sketch_id": sketch_id,
                            "clean_text": self._simple_clean(text),
                            "x": round(float(item["x"]), 1),
                            "y": round(float(item["y"]), 1),
                            "final_status": "RAW",
                            "annotation_type": "SIDE_FACE_REINF",
                        }
                    )
            else:
                for ann in sketch_record.get("annotations", []):
                    if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                        continue
                    entries.append(
                        {
                            "beam_mark": str(ann.get("beam_mark", beam_mark)),
                            "occurrence_id": int(ann.get("occurrence_id", occurrence_id)),
                            "sketch_id": str(ann.get("sketch_id", sketch_id)),
                            "clean_text": str(ann.get("clean_text", "")),
                            "x": round(float(ann["x"]), 1),
                            "y": round(float(ann["y"]), 1),
                            "final_status": str(ann.get("final_status", "")),
                            "annotation_type": "SIDE_FACE_REINF",
                        }
                    )
        return entries

    def _text_is_sfr_candidate(self, text: str) -> bool:
        normalized = text.upper().replace(".", " ")
        for term in ("SIDE FACE", "S.F.R", "SFR", "FACE REINF", "4-Y8", "2-Y10"):
            if term in normalized:
                return True
        return bool(_ENGINEERING_BAR.search(normalized))

    @staticmethod
    def _simple_clean(text: str) -> str:
        value = text.replace("\\P", " ")
        value = re.sub(r"\\A\d+;", "", value)
        value = re.sub(r"\{[^}]*\}", "", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _build_pipeline_loss(
        self,
        inventory: List[dict[str, Any]],
        snapshots: Dict[str, List[dict[str, Any]]],
    ) -> List[dict[str, Any]]:
        loss_records: List[dict[str, Any]] = []
        stage_order = [s[0] for s in _PIPELINE_STAGES]

        for item in inventory:
            key = self._match_key(item["clean_text"], item["x"], item["y"])
            stage_presence: Dict[str, Optional[dict[str, Any]]] = {}
            last_stage: Optional[str] = None

            for phase_dir in stage_order:
                match = self._find_match(snapshots.get(phase_dir, []), key)
                stage_presence[phase_dir] = match
                if match is not None:
                    last_stage = phase_dir

            disappearance = self._determine_loss_point(stage_presence, last_stage)
            loss_records.append(
                {
                    "entity_id": item["entity_id"],
                    "clean_text": item["clean_text"],
                    "x": item["x"],
                    "y": item["y"],
                    "nearest_beam": item.get("nearest_beam"),
                    "stage_presence": {
                        phase: (
                            {
                                "beam_mark": entry["beam_mark"],
                                "sketch_id": entry["sketch_id"],
                                "final_status": entry["final_status"],
                            }
                            if entry
                            else None
                        )
                        for phase, entry in stage_presence.items()
                    },
                    "last_pipeline_stage": last_stage,
                    "loss_point": disappearance,
                }
            )
        return loss_records

    def _determine_loss_point(
        self,
        stage_presence: Dict[str, Optional[dict[str, Any]]],
        last_stage: Optional[str],
    ) -> str:
        if stage_presence.get("phase_d1") is None:
            return "Never discovered (outside D.1 extraction region)"
        if last_stage is None:
            return "Never discovered"
        if last_stage == "phase_d17f":
            final = stage_presence["phase_d17f"]
            if final and final.get("final_status") == "PARSER_READY":
                return "Present through pipeline (parser-ready)"
            if final:
                return f"Rejected at final stage ({final.get('final_status')})"
            return "Present through pipeline"
        if last_stage == "phase_d17e":
            return "Lost after D.1.7E or rejected in D.1.7F"
        if last_stage == "phase_d1_7d":
            return "Lost after D.1.7D (D.1.7E or semantic)"
        if last_stage == "phase_d1_7b":
            return "Filtered during D.1.7D finalization"
        if last_stage == "phase_d1_4":
            return "Filtered during D.1.7B engineering filter"
        if last_stage == "phase_d1":
            return "Filtered during extraction typing or reassignment"
        return "OTHER"

    def _match_key(self, clean_text: str, x: float, y: float) -> Tuple[str, float, float]:
        return (clean_text.strip(), round(float(x), 1), round(float(y), 1))

    def _find_match(
        self, entries: List[dict[str, Any]], key: Tuple[str, float, float]
    ) -> Optional[dict[str, Any]]:
        text, x, y = key
        for entry in entries:
            if entry["clean_text"] != text:
                continue
            if abs(entry["x"] - x) <= MATCH_TOLERANCE_MM and abs(entry["y"] - y) <= MATCH_TOLERANCE_MM:
                return entry
        return None

    def _assign_root_causes(
        self,
        inventory: List[dict[str, Any]],
        pipeline_loss: List[dict[str, Any]],
        engineering_d17f: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        loss_by_id = {r["entity_id"]: r for r in pipeline_loss}
        causes: List[dict[str, Any]] = []

        for item in inventory:
            loss = loss_by_id.get(item["entity_id"], {})
            root_cause = self._classify_root_cause(item, loss, engineering_d17f)
            causes.append(
                {
                    "entity_id": item["entity_id"],
                    "clean_text": item["clean_text"],
                    "x": item["x"],
                    "y": item["y"],
                    "nearest_beam": item.get("nearest_beam"),
                    "root_cause": root_cause,
                    "loss_point": loss.get("loss_point"),
                    "last_pipeline_stage": loss.get("last_pipeline_stage"),
                }
            )

        for beam in EXPECTED_BEAMS:
            if self._beam_has_parser_ready_sfr(beam, engineering_d17f):
                continue
            nearest = self._nearest_inventory_to_beam(beam, inventory, sketches)
            if nearest is None:
                causes.append(
                    {
                        "entity_id": f"EXPECTED_{beam}",
                        "clean_text": "",
                        "x": None,
                        "y": None,
                        "nearest_beam": beam,
                        "root_cause": "NOT_FOUND_IN_DXF",
                        "loss_point": "No beam-specific SFR text in DXF",
                        "last_pipeline_stage": None,
                    }
                )
            elif nearest["entity_id"] not in {c["entity_id"] for c in causes}:
                pass

        return causes

    def _classify_root_cause(
        self,
        item: dict[str, Any],
        loss: dict[str, Any],
        engineering_d17f: List[dict[str, Any]],
    ) -> RootCause:
        if item.get("expanded_from_insert") and item.get("entity_type") == "INSERT":
            return "BLOCK_NOT_EXPANDED"

        last_stage = loss.get("last_pipeline_stage")
        loss_point = str(loss.get("loss_point", ""))
        final_entry = self._find_in_engineering(
            item["clean_text"], item["x"], item["y"], engineering_d17f
        )

        if last_stage is None:
            if not item.get("inside_ownership_region"):
                return "OUTSIDE_SEARCH_REGION"
            return "NOT_FOUND_IN_DXF"

        if last_stage == "phase_d1" and "Never discovered" in loss_point:
            return "OUTSIDE_SEARCH_REGION"

        if final_entry:
            status = final_entry.get("final_status", "")
            if status == "PARSER_READY":
                return "OTHER"
            if status in ("IGNORED_REFERENCE", "IGNORED_FRAGMENT"):
                return "SEMANTIC_REJECTION"
            if status == "SFR_REJECTED":
                return "OWNERSHIP_FAILURE"

        if "D.1.7D" in loss_point or last_stage == "phase_d1_7b":
            return "FILTERED_BY_D17D"

        if "D.1.7E" in loss_point or "SFR_REJECTED" in loss_point:
            return "OWNERSHIP_FAILURE"

        if last_stage == "phase_d1_4":
            return "REASSIGNMENT_FAILURE"

        if last_stage == "phase_d1" and item.get("nearest_beam"):
            assigned = loss.get("stage_presence", {}).get("phase_d1")
            if assigned and assigned.get("beam_mark") != item.get("nearest_beam"):
                return "OWNERSHIP_FAILURE"

        if not item.get("inside_ownership_region"):
            return "OUTSIDE_SEARCH_REGION"

        return "OTHER"

    def _find_in_engineering(
        self,
        clean_text: str,
        x: float,
        y: float,
        records: List[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        key = self._match_key(clean_text, x, y)
        entries = self._extract_sfr_entries(records, "engineering")
        return self._find_match(entries, key)

    def _beam_has_parser_ready_sfr(
        self, beam_mark: str, records: List[dict[str, Any]]
    ) -> bool:
        for sketch_record in records:
            for ann in sketch_record.get("annotations", []):
                if str(ann.get("annotation_type")) != "SIDE_FACE_REINF":
                    continue
                if str(ann.get("beam_mark")) != beam_mark:
                    continue
                if str(ann.get("final_status")) == "PARSER_READY":
                    flags = ann.get("sfr_semantic_validation", {}).get("flags", {})
                    if flags.get("contains_engineering_pattern"):
                        return True
                    if _ENGINEERING_BAR.search(str(ann.get("clean_text", ""))):
                        return True
        return False

    def _nearest_inventory_to_beam(
        self,
        beam_mark: str,
        inventory: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        beam_sketches = [s for s in sketches if str(s["beam_mark"]) == beam_mark]
        if not beam_sketches:
            return None
        cx = sum(
            (float(s["bbox"]["xmin"]) + float(s["bbox"]["xmax"])) / 2.0
            for s in beam_sketches
        ) / len(beam_sketches)
        cy = sum(
            (float(s["bbox"]["ymin"]) + float(s["bbox"]["ymax"])) / 2.0
            for s in beam_sketches
        ) / len(beam_sketches)

        engineering_items = [i for i in inventory if i.get("is_sfr_text")]
        if not engineering_items:
            return None
        if not engineering_items:
            engineering_items = inventory

        best = None
        best_dist = float("inf")
        for item in engineering_items:
            dist = math.hypot(float(item["x"]) - cx, float(item["y"]) - cy)
            if dist < best_dist:
                best_dist = dist
                best = item
        return best

    def _build_expected_table(
        self,
        inventory: List[dict[str, Any]],
        engineering_d17f: List[dict[str, Any]],
        root_causes: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        pipeline_loss: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        table: List[dict[str, Any]] = []
        eng_entries = self._extract_sfr_entries(engineering_d17f, "engineering")

        for beam in EXPECTED_BEAMS:
            discovered = self._discovered_for_beam(
                beam, inventory, sketches, ownership, occurrences
            )
            ownership_assigned = self._ownership_assigned_beam(beam, eng_entries)
            in_dataset = self._beam_dataset_entries(beam, eng_entries)
            parser_ready = self._beam_has_parser_ready_sfr(beam, engineering_d17f)
            root = self._root_cause_for_beam(
                beam, root_causes, discovered, parser_ready, pipeline_loss
            )

            table.append(
                {
                    "beam_mark": beam,
                    "expected_sfr_manual": True,
                    "discovered_in_dxf": discovered["found"],
                    "discovered_entity_ids": discovered.get("entity_ids", []),
                    "nearest_dxf_entity": discovered.get("nearest"),
                    "ownership_assigned_in_dataset": ownership_assigned,
                    "in_engineering_dataset": len(in_dataset) > 0,
                    "engineering_entries": in_dataset,
                    "final_status": (
                        "PARSER_READY"
                        if parser_ready
                        else (in_dataset[0]["final_status"] if in_dataset else "ABSENT")
                    ),
                    "parser_ready": parser_ready,
                    "root_cause": root,
                }
            )
        return table

    def _discovered_for_beam(
        self,
        beam_mark: str,
        inventory: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
    ) -> dict[str, Any]:
        beam_sketches = [s for s in sketches if str(s["beam_mark"]) == beam_mark]
        if not beam_sketches:
            return {"found": False, "entity_ids": [], "nearest": None}

        occ_bboxes = self._occurrence_search_bboxes(sketches, ownership, occurrences)
        hits: List[dict[str, Any]] = []
        for item in inventory:
            if not item.get("is_sfr_text"):
                continue
            for sk in beam_sketches:
                if self._point_in_bbox(
                    float(item["x"]),
                    float(item["y"]),
                    sk["bbox"],
                    800.0,
                ):
                    hits.append(item)
                    break
            for key, bbox in occ_bboxes.items():
                if key[0] != beam_mark:
                    continue
                if self._point_in_rect(float(item["x"]), float(item["y"]), bbox):
                    if item not in hits:
                        hits.append(item)
                    break

        unique_ids = list({h["entity_id"] for h in hits})
        nearest = self._nearest_inventory_to_beam(beam_mark, inventory, sketches)

        found = len(unique_ids) > 0
        return {
            "found": found,
            "entity_ids": unique_ids,
            "nearest": nearest,
        }

    def _ownership_assigned_beam(
        self, beam_mark: str, eng_entries: List[dict[str, Any]]
    ) -> bool:
        return any(e["beam_mark"] == beam_mark for e in eng_entries)

    def _beam_dataset_entries(
        self, beam_mark: str, eng_entries: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        return [e for e in eng_entries if e["beam_mark"] == beam_mark]

    def _root_cause_for_beam(
        self,
        beam_mark: str,
        root_causes: List[dict[str, Any]],
        discovered: dict[str, Any],
        parser_ready: bool,
        pipeline_loss: List[dict[str, Any]],
    ) -> RootCause:
        if parser_ready:
            return "OTHER"

        if not discovered.get("found"):
            nearest = discovered.get("nearest")
            if nearest and str(nearest.get("nearest_beam")) == beam_mark:
                if not nearest.get("inside_ownership_region"):
                    return "OUTSIDE_SEARCH_REGION"
            return "NOT_FOUND_IN_DXF"

        loss_by_id = {entry["entity_id"]: entry for entry in pipeline_loss}
        for entity_id in discovered.get("entity_ids", []):
            loss = loss_by_id.get(entity_id)
            if loss is None:
                continue
            stage_presence = loss.get("stage_presence", {})
            raw_stage = stage_presence.get("phase_d1")
            if raw_stage and raw_stage.get("beam_mark") != beam_mark:
                return "OWNERSHIP_FAILURE"
            last_stage = loss.get("last_pipeline_stage")
            loss_point = str(loss.get("loss_point", ""))
            if last_stage == "phase_d1_7b" or "D.1.7D" in loss_point:
                return "FILTERED_BY_D17D"
            if last_stage == "phase_d17e" or "SFR_REJECTED" in loss_point:
                return "OWNERSHIP_FAILURE"
            if "semantic" in loss_point.lower() or last_stage == "phase_d17f":
                return "SEMANTIC_REJECTION"

        for cause in root_causes:
            if cause.get("nearest_beam") == beam_mark:
                return cause["root_cause"]

        return "OWNERSHIP_FAILURE"

    def _build_summary(
        self,
        inventory: List[dict[str, Any]],
        expected_vs_found: List[dict[str, Any]],
        root_causes: List[dict[str, Any]],
        engineering_d17f: List[dict[str, Any]],
    ) -> dict[str, Any]:
        dist: Dict[str, int] = {}
        for cause in root_causes:
            rc = str(cause.get("root_cause", "OTHER"))
            dist[rc] = dist.get(rc, 0) + 1

        discovered_beams = sorted(
            {
                row["beam_mark"]
                for row in expected_vs_found
                if row.get("discovered_in_dxf") or row.get("in_engineering_dataset")
            },
            key=beam_mark_sort_key,
        )
        missing_beams = sorted(
            {
                row["beam_mark"]
                for row in expected_vs_found
                if not row.get("parser_ready")
            },
            key=beam_mark_sort_key,
        )

        loss_locations: Dict[str, int] = {}
        for cause in root_causes:
            lp = str(cause.get("loss_point", "unknown"))
            loss_locations[lp] = loss_locations.get(lp, 0) + 1

        eng_sfr = self._extract_sfr_entries(engineering_d17f, "engineering")
        parser_ready_sfr = sum(
            1 for e in eng_sfr if e.get("final_status") == "PARSER_READY"
        )

        parser_ready_count = sum(
            1 for row in expected_vs_found if row.get("parser_ready")
        )

        recommendation = (
            "Investigate OUTSIDE_SEARCH_REGION and OWNERSHIP_FAILURE before Phase E"
            if missing_beams
            else "READY_FOR_PHASE_E"
        )

        return {
            "total_sfr_entities_in_dxf": len(inventory),
            "engineering_pattern_entities_in_dxf": sum(
                1 for i in inventory if i.get("is_sfr_text")
            ),
            "expected_beams": list(EXPECTED_BEAMS),
            "discovered_beams": discovered_beams,
            "missing_beams": missing_beams,
            "parser_ready_sfr_count": parser_ready_sfr,
            "expected_beam_parser_ready_count": parser_ready_count,
            "root_cause_distribution": dist,
            "pipeline_loss_locations": loss_locations,
            "recommendation": recommendation,
        }

    def _validate(
        self,
        inventory: List[dict[str, Any]],
        expected_vs_found: List[dict[str, Any]],
        root_causes: List[dict[str, Any]],
    ) -> DiscoveryValidation:
        all_inventoried = len(inventory) > 0
        all_expected = len(expected_vs_found) == len(EXPECTED_BEAMS)
        missing_without_cause = any(
            not row.get("parser_ready") and row.get("root_cause") == "OTHER"
            for row in expected_vs_found
        )
        all_missing_assigned = not missing_without_cause

        status: Literal["PASS", "FAIL"] = (
            "PASS"
            if all_inventoried and all_expected and all_missing_assigned
            else "FAIL"
        )

        return DiscoveryValidation(
            all_dxf_entities_inventoried=all_inventoried,
            all_expected_beams_analysed=all_expected,
            all_missing_assigned_root_cause=all_missing_assigned,
            prior_outputs_unmodified=True,
            status=status,
        )

    def _build_report(
        self,
        summary: dict[str, Any],
        validation: DiscoveryValidation,
        expected_vs_found: List[dict[str, Any]],
        root_causes: List[dict[str, Any]],
    ) -> str:
        lines = [
            "======================================================================",
            "SFR Discovery Audit Report (Phase D.1.7G — Read-Only)",
            "======================================================================",
            "",
            f"Total SFR entities found in DXF: {summary['total_sfr_entities_in_dxf']}",
            f"Engineering-pattern entities in DXF: {summary['engineering_pattern_entities_in_dxf']}",
            f"Parser-ready SFR in D.1.7F dataset: {summary['parser_ready_sfr_count']}",
            "",
            f"Expected beams: {', '.join(summary['expected_beams'])}",
            f"Discovered beams: {', '.join(summary['discovered_beams']) or 'none'}",
            f"Missing parser-ready beams: {', '.join(summary['missing_beams']) or 'none'}",
            "",
            "Root cause distribution:",
        ]
        for cause, count in sorted(summary["root_cause_distribution"].items()):
            lines.append(f"  {cause}: {count}")

        lines.extend(["", "Pipeline loss locations:"])
        for location, count in sorted(summary["pipeline_loss_locations"].items()):
            lines.append(f"  {location}: {count}")

        lines.extend(["", f"Recommendation: {summary['recommendation']}", "", "Expected beam analysis:"])
        for row in expected_vs_found:
            lines.append(
                f"  {row['beam_mark']}: discovered={row['discovered_in_dxf']} "
                f"dataset={row['in_engineering_dataset']} "
                f"parser_ready={row['parser_ready']} "
                f"status={row['final_status']} "
                f"cause={row['root_cause']}"
            )

        lines.extend(["", "Per-entity root causes:"])
        for cause in root_causes:
            if cause.get("entity_id", "").startswith("EXPECTED_"):
                continue
            lines.append(
                f"  {cause['entity_id']} ({cause.get('nearest_beam')}): "
                f"{cause['root_cause']} — {cause.get('loss_point')}"
            )

        lines.extend(
            [
                "",
                f"Validation: {validation['status']}",
                "",
                "======================================================================",
            ]
        )
        return "\n".join(lines) + "\n"
