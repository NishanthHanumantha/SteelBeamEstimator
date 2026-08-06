"""Engineering-oriented resolution confidence model — Phase G.5.3.3."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from src.property_parser.property_parser_types import PARSE_STATUS_PARSED
from src.property_resolver.property_resolver_types import (
    RESOLUTION_CONFLICT,
    RESOLUTION_DIRECT,
    RESOLUTION_HIGHEST_CONFIDENCE,
    RESOLUTION_IDENTICAL,
    RESOLUTION_MAJORITY,
    RESOLUTION_UNKNOWN,
    RESOLUTION_WEIGHTED_MAJORITY,
)

CONFIDENCE_MODEL_VERSION = "1.0.0"
AGREEMENT_BONUS = 0.05
CONSISTENCY_BONUS = 0.05
SOURCE_DIVERSITY_BONUS_MAX = 0.05
PARSED_VALUE_QUALITY_BONUS = 0.03
CONFLICT_CONFIDENCE_CAP = 0.60


def clamp_confidence(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return round(max(0.0, min(1.0, value)), 4)


def mean_confidence(props: List[dict[str, Any]]) -> float:
    if not props:
        return 0.0
    return sum(float(prop.get("confidence", 0.0)) for prop in props) / len(props)


def source_category(prop: dict[str, Any]) -> str:
    metadata = prop.get("metadata", {}) or {}
    source_type = str(metadata.get("candidate_source_type", "")).upper().strip()
    if source_type:
        return source_type
    entity = str(prop.get("source_entity_id", ""))
    if entity.startswith("LDR::"):
        return "LEADER"
    if entity.startswith("TXT::") or entity.startswith("TEXT::"):
        return "TEXT"
    if entity.startswith("BLOCK::"):
        return "BLOCK"
    if entity.startswith("SKETCH::"):
        return "SKETCH"
    if "::" in entity:
        return entity.split("::", 1)[0]
    return "UNKNOWN"


def source_diversity_bonus(props: List[dict[str, Any]]) -> Tuple[float, str]:
    categories = {source_category(prop) for prop in props}
    meaningful = {category for category in categories if category not in ("", "UNKNOWN")}
    if len(meaningful) <= 1:
        return 0.0, ""
    bonus = min(SOURCE_DIVERSITY_BONUS_MAX, 0.025 * (len(meaningful) - 1))
    return bonus, f"source_diversity={sorted(meaningful)}"


def parsed_value_quality_bonus(prop: Optional[dict[str, Any]]) -> Tuple[float, str]:
    if not prop or prop.get("parse_status") != PARSE_STATUS_PARSED:
        return 0.0, ""
    parsed = prop.get("parsed_value")
    normalized = prop.get("normalized_value")
    if parsed is not None and normalized is not None and str(normalized).strip():
        return PARSED_VALUE_QUALITY_BONUS, "parsed_value_quality"
    return 0.0, ""


def consistency_bonus(all_parsed: List[dict[str, Any]], winners: List[dict[str, Any]]) -> Tuple[float, str]:
    if len(all_parsed) >= 2 and len(winners) == len(all_parsed):
        return CONSISTENCY_BONUS, "full_consistency"
    return 0.0, ""


def apply_confidence_bonuses(
    base: float,
    selected: Optional[dict[str, Any]],
    winners: List[dict[str, Any]],
    all_parsed: List[dict[str, Any]],
    include_consistency: bool = True,
) -> Tuple[float, str]:
    bonus_total = base
    notes: List[str] = [f"base={base:.4f}"]

    diversity, diversity_note = source_diversity_bonus(winners)
    bonus_total += diversity
    if diversity_note:
        notes.append(diversity_note)

    quality, quality_note = parsed_value_quality_bonus(selected)
    bonus_total += quality
    if quality_note:
        notes.append(quality_note)

    if include_consistency:
        consistency, consistency_note = consistency_bonus(all_parsed, winners)
        bonus_total += consistency
        if consistency_note:
            notes.append(consistency_note)

    return clamp_confidence(bonus_total), "; ".join(notes)


def confidence_unknown() -> Tuple[float, str]:
    return 0.0, "no parsed properties"


def confidence_direct(
    selected: dict[str, Any],
    all_parsed: List[dict[str, Any]],
) -> Tuple[float, str]:
    base = float(selected.get("confidence", 0.0))
    confidence, note = apply_confidence_bonuses(
        base,
        selected,
        [selected],
        all_parsed,
        include_consistency=False,
    )
    return confidence, f"direct={base:.4f}; {note}"


def confidence_identical(
    selected: dict[str, Any],
    winners: List[dict[str, Any]],
    all_parsed: List[dict[str, Any]],
) -> Tuple[float, str]:
    base = mean_confidence(winners) + AGREEMENT_BONUS
    confidence, note = apply_confidence_bonuses(
        base,
        selected,
        winners,
        all_parsed,
        include_consistency=True,
    )
    return confidence, f"mean_conf+agreement={base:.4f}; {note}"


def confidence_majority(
    selected: dict[str, Any],
    winners: List[dict[str, Any]],
    all_parsed: List[dict[str, Any]],
) -> Tuple[float, str]:
    winner_ratio = len(winners) / len(all_parsed) if all_parsed else 0.0
    agreement = winner_ratio
    avg_winner = mean_confidence(winners)
    base = avg_winner * (0.75 + 0.25 * agreement)
    confidence, note = apply_confidence_bonuses(
        base,
        selected,
        winners,
        all_parsed,
        include_consistency=False,
    )
    return confidence, (
        f"avg_winner={avg_winner:.4f} agreement={agreement:.4f} "
        f"formula=avg*(0.75+0.25*agreement); {note}"
    )


def confidence_weighted_majority(
    selected: dict[str, Any],
    winners: List[dict[str, Any]],
    all_parsed: List[dict[str, Any]],
    weighted_support: float,
) -> Tuple[float, str]:
    avg_winner = mean_confidence(winners)
    base = weighted_support * avg_winner
    confidence, note = apply_confidence_bonuses(
        base,
        selected,
        winners,
        all_parsed,
        include_consistency=False,
    )
    return confidence, (
        f"weighted_support={weighted_support:.4f} avg_winner={avg_winner:.4f}; {note}"
    )


def confidence_highest_confidence(
    selected: dict[str, Any],
    all_parsed: List[dict[str, Any]],
) -> Tuple[float, str]:
    confidences = sorted(
        (float(prop.get("confidence", 0.0)) for prop in all_parsed),
        reverse=True,
    )
    top = confidences[0] if confidences else 0.0
    second = confidences[1] if len(confidences) > 1 else 0.0
    if top > 0.0:
        margin = min(1.0, (top - second) / top)
        uniqueness_factor = 0.85 + 0.15 * margin
    else:
        uniqueness_factor = 0.85
    base = top * uniqueness_factor
    confidence, note = apply_confidence_bonuses(
        base,
        selected,
        [selected],
        all_parsed,
        include_consistency=False,
    )
    return confidence, (
        f"top={top:.4f} uniqueness={uniqueness_factor:.4f}; {note}"
    )


def confidence_conflict(
    all_parsed: List[dict[str, Any]],
    distinct_count: int,
    value_groups: Dict[str, List[dict[str, Any]]],
) -> Tuple[float, str]:
    if distinct_count <= 1:
        return clamp_confidence(0.5), "single_distinct_value_conflict"

    if distinct_count == 2:
        low, high = 0.40, 0.55
    elif distinct_count == 3:
        low, high = 0.30, 0.45
    else:
        low, high = 0.20, 0.35

    counts = [len(props) for props in value_groups.values()]
    total = sum(counts)
    top_share = max(counts) / total if total else 0.0
    base = low + (high - low) * top_share
    confidence = clamp_confidence(min(CONFLICT_CONFIDENCE_CAP, base))
    return confidence, (
        f"distinct={distinct_count} top_share={top_share:.4f} "
        f"range=[{low:.2f},{high:.2f}] cap={CONFLICT_CONFIDENCE_CAP:.2f}"
    )


def compute_resolution_confidence(
    strategy: str,
    selected: Optional[dict[str, Any]],
    winners: List[dict[str, Any]],
    all_parsed: List[dict[str, Any]],
    distinct_count: int = 1,
    value_groups: Optional[Dict[str, List[dict[str, Any]]]] = None,
    weighted_support: float = 0.0,
) -> Tuple[float, str]:
    if strategy == RESOLUTION_UNKNOWN:
        return confidence_unknown()
    if not selected:
        return 0.0, "no selected property"

    if strategy == RESOLUTION_DIRECT:
        return confidence_direct(selected, all_parsed)
    if strategy == RESOLUTION_IDENTICAL:
        return confidence_identical(selected, winners, all_parsed)
    if strategy == RESOLUTION_MAJORITY:
        return confidence_majority(selected, winners, all_parsed)
    if strategy == RESOLUTION_WEIGHTED_MAJORITY:
        return confidence_weighted_majority(
            selected,
            winners,
            all_parsed,
            weighted_support,
        )
    if strategy == RESOLUTION_HIGHEST_CONFIDENCE:
        return confidence_highest_confidence(selected, all_parsed)
    if strategy == RESOLUTION_CONFLICT:
        groups = value_groups or {}
        return confidence_conflict(all_parsed, distinct_count, groups)

    base = mean_confidence(winners) if winners else 0.0
    return clamp_confidence(base), f"fallback mean={base:.4f}"
