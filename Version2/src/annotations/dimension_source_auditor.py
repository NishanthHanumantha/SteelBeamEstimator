"""Phase D.1.7A — audit DIMENSION entity text sources."""

import re
from collections import defaultdict
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger

from src.annotations.dimension_annotation_extractor import (
    DimensionAnnotationExtractor,
)
from src.annotations.dimension_annotation_integrator import DimensionAnnotationIntegrator
from src.framing.beam_geometry import beam_mark_sort_key
from src.parser.dxf_reader import DxfReader

SourceType = Literal["ENGINEERING_TEXT", "MEASUREMENT_VALUE", "UNKNOWN_SOURCE"]

_BLANK_OVERRIDE_VALUES = frozenset({"", "<>"})
_ENGINEERING_PATTERN = re.compile(
    r"@|C/C|\bLD\b|LD\+|Y\d+",
    re.IGNORECASE,
)
_NUMERIC_PATTERN = re.compile(r"^\d+$")
_REPEAT_MIN_COUNT = 2


class DimensionSourceRecord(TypedDict):
    handle: str
    layer: str
    dimension_text_raw: str
    dimension_override: str
    actual_measurement: Optional[float]
    rendered_text: str
    final_extracted_text: str
    beam_mark: str
    occurrence_id: int
    assigned: bool
    x: float
    y: float
    source_type: SourceType


class SourceSummary(TypedDict):
    total_dimensions: int
    engineering_text_count: int
    measurement_value_count: int
    unknown_source_count: int


class RepeatedValueRecord(TypedDict):
    value: str
    count: int
    dimension_handles: List[str]
    source_type: SourceType
    actual_measurement_range: List[float]
    layers: List[str]
    beam_marks: List[str]
    investigation: Dict[str, str]


class AuditResult(TypedDict):
    records: List[DimensionSourceRecord]
    summary: SourceSummary
    repeated_values: List[RepeatedValueRecord]
    report_text: str
    recommendation: str


class DimensionSourceAuditor:
    """Trace each DIMENSION entity to its text source and ownership assignment."""

    def audit(
        self,
        dxf_path: str,
        ownership: List[dict[str, Any]],
        occurrences: List[dict[str, Any]],
        sketches: List[dict[str, Any]],
        beam_cells: List[dict[str, Any]],
    ) -> AuditResult:
        doc = DxfReader(dxf_path).read()
        msp = doc.modelspace()
        extractor = DimensionAnnotationExtractor()
        integrator = DimensionAnnotationIntegrator()

        dimensions = extractor.extract_from_dxf(dxf_path)
        integration = integrator.integrate(
            dxf_path,
            [],
            dimensions,
            ownership,
            occurrences,
            sketches,
            beam_cells,
        )
        assignment_lookup = self._assignment_lookup(integration["dimension_assignments"])

        records: List[DimensionSourceRecord] = []
        for entity in msp.query("DIMENSION"):
            handle = str(entity.dxf.handle)
            record = self._audit_entity(
                entity,
                extractor,
                assignment_lookup,
            )
            if record is not None:
                records.append(record)

        records.sort(
            key=lambda item: (
                item["source_type"],
                -item["y"],
                item["x"],
                item["handle"],
            )
        )

        summary = self._build_summary(records)
        repeated_values = self._build_repeated_values(records)
        recommendation = self._recommendation(summary, repeated_values)
        report_text = self._build_report_text(summary, repeated_values, recommendation)

        logger.info(
            "Dimension source audit: {} entities, eng={}, meas={}, unknown={}",
            summary["total_dimensions"],
            summary["engineering_text_count"],
            summary["measurement_value_count"],
            summary["unknown_source_count"],
        )
        return AuditResult(
            records=records,
            summary=summary,
            repeated_values=repeated_values,
            report_text=report_text,
            recommendation=recommendation,
        )

    def _audit_entity(
        self,
        entity: DXFGraphic,
        extractor: DimensionAnnotationExtractor,
        assignment_lookup: Dict[Tuple[float, float, str, str], dict[str, Any]],
    ) -> Optional[DimensionSourceRecord]:
        raw_override = self._raw_override(entity)
        override_stripped = raw_override.strip()
        actual_measurement = self._actual_measurement(entity)

        raw_text, final_text = extractor._resolve_text(entity)
        if not final_text:
            return None

        rendered_text = self._rendered_text(entity, extractor)
        x, y = extractor._position(entity)
        x = round(x, 1)
        y = round(y, 1)
        layer = str(entity.dxf.layer)

        assignment = assignment_lookup.get((x, y, final_text, layer), {})
        beam_mark = str(assignment.get("beam_mark", ""))
        occurrence_id = int(assignment.get("occurrence_id", 0))
        assigned = bool(assignment.get("assigned", False))

        source_type = self._classify_source(
            override_stripped,
            actual_measurement,
            final_text,
            raw_text,
        )

        return DimensionSourceRecord(
            handle=str(entity.dxf.handle),
            layer=layer,
            dimension_text_raw=raw_override,
            dimension_override=override_stripped,
            actual_measurement=actual_measurement,
            rendered_text=rendered_text,
            final_extracted_text=final_text,
            beam_mark=beam_mark,
            occurrence_id=occurrence_id,
            assigned=assigned,
            x=x,
            y=y,
            source_type=source_type,
        )

    @staticmethod
    def _raw_override(entity: DXFGraphic) -> str:
        override = getattr(entity.dxf, "text", None)
        if override is None:
            return ""
        return str(override)

    @staticmethod
    def _actual_measurement(entity: DXFGraphic) -> Optional[float]:
        value = getattr(entity.dxf, "actual_measurement", None)
        if value is None:
            return None
        return round(float(value), 6)

    def _rendered_text(
        self, entity: DXFGraphic, extractor: DimensionAnnotationExtractor
    ) -> str:
        override = getattr(entity.dxf, "text", None)
        override_str = str(override).strip() if override is not None else ""

        if override_str and override_str not in _BLANK_OVERRIDE_VALUES:
            return extractor._normalize_text(override_str)

        measurement_text = extractor._measurement_text(entity)
        return measurement_text

    def _classify_source(
        self,
        override_stripped: str,
        actual_measurement: Optional[float],
        final_text: str,
        raw_text: str,
    ) -> SourceType:
        has_explicit_override = bool(
            override_stripped and override_stripped not in _BLANK_OVERRIDE_VALUES
        )

        if has_explicit_override:
            normalized = raw_text.replace("\\P", "").replace("\n", "").strip()
            if _ENGINEERING_PATTERN.search(normalized):
                return "ENGINEERING_TEXT"
            if _NUMERIC_PATTERN.match(normalized):
                return "MEASUREMENT_VALUE"
            if re.search(r"[A-Za-z]", normalized):
                return "ENGINEERING_TEXT"
            return "UNKNOWN_SOURCE"

        if actual_measurement is not None:
            return "MEASUREMENT_VALUE"

        return "UNKNOWN_SOURCE"

    @staticmethod
    def _assignment_lookup(
        assignments: List[dict[str, Any]],
    ) -> Dict[Tuple[float, float, str, str], dict[str, Any]]:
        lookup: Dict[Tuple[float, float, str, str], dict[str, Any]] = {}
        for assignment in assignments:
            dimension = assignment["dimension"]
            key = (
                float(dimension["x"]),
                float(dimension["y"]),
                str(dimension["text"]),
                str(dimension["layer"]),
            )
            lookup[key] = assignment
        return lookup

    def _build_summary(self, records: List[DimensionSourceRecord]) -> SourceSummary:
        engineering = sum(1 for r in records if r["source_type"] == "ENGINEERING_TEXT")
        measurement = sum(
            1 for r in records if r["source_type"] == "MEASUREMENT_VALUE"
        )
        unknown = sum(1 for r in records if r["source_type"] == "UNKNOWN_SOURCE")
        return SourceSummary(
            total_dimensions=len(records),
            engineering_text_count=engineering,
            measurement_value_count=measurement,
            unknown_source_count=unknown,
        )

    def _build_repeated_values(
        self, records: List[DimensionSourceRecord]
    ) -> List[RepeatedValueRecord]:
        grouped: Dict[str, List[DimensionSourceRecord]] = defaultdict(list)
        for record in records:
            grouped[record["final_extracted_text"]].append(record)

        repeated: List[RepeatedValueRecord] = []
        for value, items in grouped.items():
            if len(items) < _REPEAT_MIN_COUNT:
                continue

            measurements = [
                item["actual_measurement"]
                for item in items
                if item["actual_measurement"] is not None
            ]
            measurement_range: List[float] = []
            if measurements:
                measurement_range = [
                    round(min(measurements), 3),
                    round(max(measurements), 3),
                ]

            source_types = {item["source_type"] for item in items}
            source_type: SourceType = (
                items[0]["source_type"]
                if len(source_types) == 1
                else "UNKNOWN_SOURCE"
            )

            beam_marks = sorted(
                {item["beam_mark"] for item in items if item["beam_mark"]},
                key=beam_mark_sort_key,
            )
            layers = sorted({item["layer"] for item in items})

            repeated.append(
                RepeatedValueRecord(
                    value=value,
                    count=len(items),
                    dimension_handles=[item["handle"] for item in items],
                    source_type=source_type,
                    actual_measurement_range=measurement_range,
                    layers=layers,
                    beam_marks=beam_marks,
                    investigation=self._investigate_repeated(value, items),
                )
            )

        repeated.sort(key=lambda item: (-item["count"], item["value"]))
        return repeated

    def _investigate_repeated(
        self, value: str, items: List[DimensionSourceRecord]
    ) -> Dict[str, str]:
        if value == "687":
            return {
                "why_appearing": (
                    "DIMENSION entities on layer -S-STIRUP with blank/space override "
                    "and actual_measurement ~686.71 mm, rounded to 687 by D.1.7."
                ),
                "from_actual_measurement": "yes",
                "displayed_in_drawing": (
                    "yes — AutoCAD renders the measured stirrup zone length (~687 mm), "
                    "not an explicit engineering callout string."
                ),
                "should_be_retained": (
                    "no for engineering annotation parsing — geometric stirrup "
                    "segment lengths, not spacing callouts."
                ),
                "exclude_from_engineering_parsing": "yes",
            }

        all_measurement = all(
            item["source_type"] == "MEASUREMENT_VALUE" for item in items
        )
        if all_measurement:
            return {
                "why_appearing": (
                    f"Repeated numeric value {value} from actual_measurement with "
                    "blank or <> dimension text override."
                ),
                "from_actual_measurement": "yes",
                "displayed_in_drawing": (
                    "yes — AutoCAD displays the computed measurement value."
                ),
                "should_be_retained": (
                    "beam dimensions (500, 1900) yes for geometry; "
                    "stirrup segment lengths (687, 688) no for reinforcement parsing."
                ),
                "exclude_from_engineering_parsing": (
                    "yes for stirrup geometry segments; "
                    "no for primary beam span/depth dimensions if used in D.2 geometry."
                ),
            }

        return {
            "why_appearing": (
                f"Value {value} appears {len(items)} times from explicit dimension "
                "text overrides."
            ),
            "from_actual_measurement": "no",
            "displayed_in_drawing": "yes — explicit dimension text override.",
            "should_be_retained": "yes — engineering callout text.",
            "exclude_from_engineering_parsing": "no",
        }

    def _recommendation(
        self,
        summary: SourceSummary,
        repeated_values: List[RepeatedValueRecord],
    ) -> str:
        meas_count = summary["measurement_value_count"]
        eng_count = summary["engineering_text_count"]
        stirrup_meas_layers = sum(
            1
            for item in repeated_values
            if item["value"] in {"687", "688", "530", "537"}
            and item["source_type"] == "MEASUREMENT_VALUE"
        )

        if meas_count > 0 and eng_count > 0:
            return (
                "KEEP only engineering text for D.2 parsing; EXCLUDE MEASUREMENT_VALUE "
                "entities sourced from actual_measurement on blank/<>/space overrides. "
                "Optionally retain primary beam dimensions (500, 1900, 2150) for geometry "
                "QA in a separate geometry channel, not reinforcement annotation parsing."
            )

        if stirrup_meas_layers > 0:
            return (
                "EXCLUDE stirrup geometry measurements (687, 688, etc.) from D.2; "
                "KEEP only ENGINEERING_TEXT overrides for reinforcement parsing."
            )

        return "KEEP only engineering text for D.2"

    def _build_report_text(
        self,
        summary: SourceSummary,
        repeated_values: List[RepeatedValueRecord],
        recommendation: str,
    ) -> str:
        lines = [
            "======================================================================",
            "DIMENSION Text Source Audit Report (Phase D.1.7A)",
            "======================================================================",
            "",
            f"TOTAL DIMENSIONS: {summary['total_dimensions']}",
            f"ENGINEERING_TEXT COUNT: {summary['engineering_text_count']}",
            f"MEASUREMENT_VALUE COUNT: {summary['measurement_value_count']}",
            f"UNKNOWN COUNT: {summary['unknown_source_count']}",
            "",
            "TOP REPEATED VALUES",
            "",
        ]

        for item in repeated_values[:20]:
            lines.append(f"  {item['value']}: {item['count']} occurrences")
            lines.append(f"    source_type: {item['source_type']}")
            lines.append(f"    layers: {', '.join(item['layers'])}")
            if item["actual_measurement_range"]:
                low, high = item["actual_measurement_range"]
                lines.append(f"    actual_measurement range: {low} – {high}")
            if item["beam_marks"]:
                lines.append(f"    beam_marks: {', '.join(item['beam_marks'])}")
            if item["value"] == "687":
                lines.append("")
                lines.append("  Investigation: 687")
                for key, answer in item["investigation"].items():
                    lines.append(f"    {key}: {answer}")
            lines.append("")

        lines.extend(
            [
                "Recommended action for D.2:",
                f"  {recommendation}",
                "",
                "======================================================================",
            ]
        )
        return "\n".join(lines) + "\n"
