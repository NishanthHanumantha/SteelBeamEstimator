"""Validation for Phase D.1 raw annotation extraction."""

from typing import Any, List, TypedDict

from src.annotations.raw_annotation_extractor import RawAnnotationRecord


class DuplicateTextEntry(TypedDict):
    sketch_id: str
    text: str
    x: float
    y: float


class AnnotationValidationSummary(TypedDict):
    total_sketches: int
    processed_sketches: int
    total_annotations: int
    empty_sketches: int


class AnnotationValidation(TypedDict):
    total_sketches: int
    processed_sketches: int
    total_annotations: int
    empty_sketches: List[str]
    duplicate_texts: List[DuplicateTextEntry]
    summary: AnnotationValidationSummary
    status: str


class AnnotationValidator:
    """Validate raw annotation extraction results."""

    def validate(
        self,
        expected_sketch_ids: List[str],
        records: List[RawAnnotationRecord],
        extraction_failed: bool = False,
    ) -> AnnotationValidation:
        processed_ids = [record["sketch_id"] for record in records]
        empty_sketches = sorted(
            record["sketch_id"] for record in records if record["annotation_count"] == 0
        )
        duplicate_texts = self._find_duplicate_texts(records)
        total_annotations = sum(record["annotation_count"] for record in records)

        missing = sorted(set(expected_sketch_ids) - set(processed_ids))
        if missing:
            empty_sketches = sorted(set(empty_sketches) | set(missing))

        status = (
            "FAIL"
            if extraction_failed
            or len(processed_ids) != len(expected_sketch_ids)
            else "PASS"
        )

        summary = AnnotationValidationSummary(
            total_sketches=len(expected_sketch_ids),
            processed_sketches=len(processed_ids),
            total_annotations=total_annotations,
            empty_sketches=len(empty_sketches),
        )

        return AnnotationValidation(
            total_sketches=len(expected_sketch_ids),
            processed_sketches=len(processed_ids),
            total_annotations=total_annotations,
            empty_sketches=empty_sketches,
            duplicate_texts=duplicate_texts,
            summary=summary,
            status=status,
        )

    def _find_duplicate_texts(
        self, records: List[RawAnnotationRecord]
    ) -> List[DuplicateTextEntry]:
        duplicates: List[DuplicateTextEntry] = []
        for record in records:
            seen: set[tuple[str, float, float]] = set()
            for item in record["texts"]:
                key = (item["text"], item["x"], item["y"])
                if key in seen:
                    duplicates.append(
                        DuplicateTextEntry(
                            sketch_id=record["sketch_id"],
                            text=item["text"],
                            x=item["x"],
                            y=item["y"],
                        )
                    )
                else:
                    seen.add(key)
        duplicates.sort(
            key=lambda entry: (
                entry["sketch_id"],
                entry["text"],
                entry["x"],
                entry["y"],
            )
        )
        return duplicates
