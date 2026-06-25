"""Validate drawing region assignments against estimator expectations."""

import re
from typing import Any, Dict, List, Optional, Pattern

from loguru import logger

from src.regions.text_normalizer import normalize_drawing_text

CheckRule = tuple[str, Pattern[str], bool]


BEAM_REINFORCEMENT_REQUIRED: List[CheckRule] = [
    ("2-Y16", re.compile(r"2-Y16", re.IGNORECASE), True),
    ("2-Y20", re.compile(r"2-Y20", re.IGNORECASE), True),
    ("2-Y12", re.compile(r"2-Y12", re.IGNORECASE), True),
    (
        "2L-Y10@100",
        re.compile(r"2L-Y10@\s*(?:\\P)?100", re.IGNORECASE),
        True,
    ),
    ("Ld", re.compile(r"^Ld$", re.IGNORECASE), True),
    ("1900", re.compile(r"1899|1900"), True),
    ("2150", re.compile(r"2150"), True),
    ("500", re.compile(r"(?<![\d.])\b500\b(?![\d.])"), False),
]

FRAMING_PLAN_REQUIRED: List[CheckRule] = [
    ("B1", re.compile(r"\bB1\b", re.IGNORECASE), True),
    ("B2", re.compile(r"\bB2\b", re.IGNORECASE), True),
    ("B3", re.compile(r"\bB3\b", re.IGNORECASE), True),
    ("B4", re.compile(r"\bB4\b", re.IGNORECASE), True),
]

FRAMING_PLAN_FORBIDDEN: List[tuple[str, Pattern[str]]] = [
    ("2-Y16", re.compile(r"2-Y16", re.IGNORECASE)),
    ("2L-Y10@100", re.compile(r"2L-Y10@\s*(?:\\P)?100", re.IGNORECASE)),
    ("Ld", re.compile(r"^Ld$", re.IGNORECASE)),
]


class RegionValidator:
    """Validate region content against structural estimator rules."""

    def validate(
        self,
        entities: List[dict[str, Any]],
        assignments: Dict[str, str],
    ) -> dict[str, Any]:
        all_texts = self._all_drawing_texts(entities)
        region_texts = self._collect_region_texts(entities, assignments)
        region_entities = self._collect_region_entities(entities, assignments)

        reinf_checks = self._check_patterns(
            "beam_reinforcement",
            region_texts.get("beam_reinforcement", []),
            BEAM_REINFORCEMENT_REQUIRED,
            all_texts,
        )

        framing_checks = self._check_patterns(
            "framing_plan",
            region_texts.get("framing_plan", []),
            FRAMING_PLAN_REQUIRED,
            all_texts,
        )
        framing_checks["beam_layout_geometry"] = {
            "found": self._has_line_geometry(region_entities.get("framing_plan", [])),
            "region": "framing_plan",
            "required": True,
            "present_in_drawing": True,
        }

        framing_forbidden = self._check_forbidden_patterns(
            region_texts.get("framing_plan", []),
            FRAMING_PLAN_FORBIDDEN,
        )

        required_results = [
            item["found"]
            for item in reinf_checks.values()
            if item.get("required", True)
        ]
        required_results.extend(
            item["found"]
            for item in framing_checks.values()
            if item.get("required", True)
        )

        all_passed = all(required_results) and not framing_forbidden["violations_found"]

        result = {
            "passed": all_passed,
            "beam_reinforcement_checks": reinf_checks,
            "framing_plan_checks": framing_checks,
            "framing_plan_forbidden": framing_forbidden,
        }

        if all_passed:
            logger.info("Region validation PASSED")
        else:
            logger.warning("Region validation FAILED — see validation output")

        return result

    def _all_drawing_texts(self, entities: List[dict[str, Any]]) -> List[str]:
        texts: List[str] = []
        for entity in entities:
            if entity.get("entity_type") not in {"TEXT", "MTEXT", "DIMENSION"}:
                continue
            text = normalize_drawing_text(str(entity.get("clean_text", "")))
            if text:
                texts.append(text)
        return texts

    def _collect_region_texts(
        self,
        entities: List[dict[str, Any]],
        assignments: Dict[str, str],
    ) -> Dict[str, List[str]]:
        texts: Dict[str, List[str]] = {}
        for entity in entities:
            handle = str(entity.get("handle", ""))
            region = assignments.get(handle, "unassigned")
            if entity.get("entity_type") not in {"TEXT", "MTEXT", "DIMENSION"}:
                continue
            text = normalize_drawing_text(str(entity.get("clean_text", "")))
            if text:
                texts.setdefault(region, []).append(text)
        return texts

    def _collect_region_entities(
        self,
        entities: List[dict[str, Any]],
        assignments: Dict[str, str],
    ) -> Dict[str, List[dict[str, Any]]]:
        grouped: Dict[str, List[dict[str, Any]]] = {}
        for entity in entities:
            handle = str(entity.get("handle", ""))
            region = assignments.get(handle, "unassigned")
            grouped.setdefault(region, []).append(entity)
        return grouped

    def _check_patterns(
        self,
        region_name: str,
        texts: List[str],
        rules: List[CheckRule],
        all_texts: List[str],
    ) -> Dict[str, dict[str, Any]]:
        combined = " | ".join(texts)
        results: Dict[str, dict[str, Any]] = {}

        for label, pattern, required in rules:
            present_in_drawing = any(
                pattern.search(text) for text in all_texts
            )
            found = any(pattern.search(text) for text in texts) or pattern.search(
                combined
            )

            if not present_in_drawing and not required:
                results[label] = {
                    "found": True,
                    "region": region_name,
                    "required": required,
                    "present_in_drawing": False,
                    "skipped": True,
                }
                continue

            results[label] = {
                "found": bool(found),
                "region": region_name,
                "required": required,
                "present_in_drawing": present_in_drawing,
                "skipped": False,
            }

        return results

    def _check_forbidden_patterns(
        self,
        texts: List[str],
        rules: List[tuple[str, Pattern[str]]],
    ) -> dict[str, Any]:
        violations = []
        for label, pattern in rules:
            for text in texts:
                if pattern.search(text):
                    violations.append(label)
                    break

        return {
            "violations_found": bool(violations),
            "violations": violations,
        }

    def _has_line_geometry(self, entities: List[dict[str, Any]]) -> bool:
        return any(
            entity.get("entity_type") in {"LINE", "LWPOLYLINE", "POLYLINE"}
            for entity in entities
        )
