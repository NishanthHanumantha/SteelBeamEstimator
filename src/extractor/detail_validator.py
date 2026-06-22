"""Validate reinforcement detail extraction (Phase 3B.3)."""

import re
from typing import Dict, List, Pattern, Tuple

from loguru import logger

from src.extractor.detail_text_filter import SIDE_FACE_PATTERN, is_decimal_dimension_noise

ValidationRule = tuple[str, Pattern[str], int]

B1_RULES: List[ValidationRule] = [
    ("2-Y16", re.compile(r"2-Y16", re.I), 1),
    ("2-Y20", re.compile(r"2-Y20", re.I), 1),
    ("2-Y12", re.compile(r"2-Y12", re.I), 1),
    ("2L-Y10@100", re.compile(r"2L-Y10@100", re.I), 1),
    ("1900", re.compile(r"^1900$"), 2),
    ("4-Y8 SIDE FACE", re.compile(r"4-Y8.*SIDE\s+FACE", re.I), 1),
]

CONTAMINANT_PATTERNS: List[Pattern[str]] = [
    re.compile(r"FRAMING\s+PLAN", re.I),
    re.compile(r"SCALE\s*1\s*:", re.I),
    re.compile(r"GENERAL\s+NOTES", re.I),
    re.compile(r"^NOTE:", re.I),
]


def _check_duplicate_across_blocks(blocks: List[dict]) -> List[str]:
    violations: List[str] = []
    owners: Dict[Tuple[str, float, float], str] = {}

    for block in blocks:
        if block.get("status") == "SKETCH_NOT_FOUND":
            continue
        mark = block["beam_mark"]
        for item in block.get("texts", []):
            key = (
                item["text"].strip().upper(),
                round(item["x"], 1),
                round(item["y"], 1),
            )
            owner = owners.get(key)
            if owner is not None and owner != mark:
                violations.append(
                    f"Annotation '{item['text']}' at ({item['x']}, {item['y']}) "
                    f"shared by {owner} and {mark}"
                )
            else:
                owners[key] = mark

    return violations


def _check_decimal_noise(blocks: List[dict]) -> List[str]:
    violations: List[str] = []
    for block in blocks:
        if block.get("status") == "SKETCH_NOT_FOUND":
            continue
        mark = block["beam_mark"]
        for item in block.get("texts", []):
            if is_decimal_dimension_noise(item["text"]):
                violations.append(
                    f"{mark}: decimal dimension noise '{item['text']}'"
                )
    return violations


B1_SFR_POSITION = (6267.2, 22833.2)
B1_SFR_POSITION_TOLERANCE_MM = 50.0


def _is_b1_side_face_annotation(item: dict) -> bool:
    if not SIDE_FACE_PATTERN.search(item["text"]):
        return False
    if not re.search(r"\d+-Y\d+", item["text"], re.IGNORECASE):
        return False
    return (
        abs(item["x"] - B1_SFR_POSITION[0]) <= B1_SFR_POSITION_TOLERANCE_MM
        and abs(item["y"] - B1_SFR_POSITION[1]) <= B1_SFR_POSITION_TOLERANCE_MM
    )


def _check_b3_no_b1_sfr(blocks: List[dict]) -> List[str]:
    violations: List[str] = []
    b3 = next((b for b in blocks if b["beam_mark"] == "B3"), None)
    if b3 is None or b3.get("status") == "SKETCH_NOT_FOUND":
        return violations

    for item in b3.get("texts", []):
        if _is_b1_side_face_annotation(item):
            violations.append(
                f"B3: contains B1 side-face reinforcement '{item['text']}' "
                f"at ({item['x']}, {item['y']})"
            )
    return violations


def validate_detail_blocks(blocks: List[dict]) -> dict:
    block_map: Dict[str, dict] = {
        block["beam_mark"]: block for block in blocks
    }

    checks: dict = {}
    violations: List[str] = []

    for block in blocks:
        checks[block["beam_mark"]] = {
            "status": block.get("status"),
            "bbox": block.get("bbox"),
            "annotation_count": block.get(
                "annotation_count", len(block.get("texts", []))
            ),
        }

    violations.extend(_check_duplicate_across_blocks(blocks))
    violations.extend(_check_decimal_noise(blocks))
    violations.extend(_check_b3_no_b1_sfr(blocks))

    b1 = block_map.get("B1")
    if b1 is None:
        violations.append("B1: block not found")
    elif b1.get("status") == "SKETCH_NOT_FOUND":
        violations.append("B1: sketch not found")
    else:
        texts = [item["text"] for item in b1.get("texts", [])]
        b1_checks = {}
        for label, pattern, expected_count in B1_RULES:
            count = sum(1 for text in texts if pattern.search(text))
            b1_checks[label] = {
                "expected": expected_count,
                "found": count,
                "passed": count >= expected_count,
            }
            if count < expected_count:
                violations.append(
                    f"B1: expected {expected_count} x '{label}', found {count}"
                )
        for text in texts:
            for pattern in CONTAMINANT_PATTERNS:
                if pattern.search(text):
                    violations.append(f"B1: contaminant text '{text}'")
        checks["B1"] = {**checks.get("B1", {}), **b1_checks}

    if block_map.get("B3") is None:
        violations.append("B3: block not found")
    elif block_map["B3"].get("status") == "SKETCH_NOT_FOUND":
        violations.append("B3: sketch not found")
    else:
        b3_count = block_map["B3"].get(
            "annotation_count", len(block_map["B3"].get("texts", []))
        )
        checks["B3"] = {
            **checks.get("B3", {}),
            "annotation_count": b3_count,
            "passed": b3_count > 0,
        }
        if b3_count == 0:
            violations.append("B3: no reinforcement annotations found")

    passed = not violations
    if passed:
        logger.info("Detail validation PASSED")
    else:
        logger.warning("Detail validation FAILED")

    return {"passed": passed, "checks": checks, "violations": violations}
