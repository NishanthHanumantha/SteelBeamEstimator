"""Resolution strategy definitions — Phase G.5.3.2 / confidence G.5.3.3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.property_parser.property_parser_types import PARSE_STATUS_PARSED
from src.property_resolver.confidence_model import compute_resolution_confidence
from src.property_resolver.property_resolver_types import (
    RESOLUTION_CONFLICT,
    RESOLUTION_DIRECT,
    RESOLUTION_HIGHEST_CONFIDENCE,
    RESOLUTION_IDENTICAL,
    RESOLUTION_MAJORITY,
    RESOLUTION_UNKNOWN,
    RESOLUTION_WEIGHTED_MAJORITY,
)


@dataclass(frozen=True)
class ResolutionOutcome:
    strategy: str
    selected: Optional[dict[str, Any]]
    resolved_value: Any
    unit: str
    resolution_confidence: float
    conflicting_values: List[Any] = field(default_factory=list)
    alternative_property_ids: List[str] = field(default_factory=list)
    resolution_notes: str = ""


def normalize_value_key(prop: dict[str, Any]) -> str:
    norm = prop.get("normalized_value")
    if norm is not None:
        return str(norm).strip()
    parsed = prop.get("parsed_value")
    if parsed is not None:
        return str(parsed).strip()
    return ""


def parsed_properties(group: List[dict[str, Any]]) -> List[dict[str, Any]]:
    return [p for p in group if p.get("parse_status") == PARSE_STATUS_PARSED]


def alternative_property_ids(
    all_ids: List[str],
    selected_id: str = "",
) -> List[str]:
    """All property IDs in the group except the selected winner."""
    return [pid for pid in all_ids if pid and pid != selected_id]


def apply_resolution_strategy(group: List[dict[str, Any]]) -> ResolutionOutcome:
    all_ids = [str(p.get("property_id", "")) for p in group if p.get("property_id")]
    parsed = parsed_properties(group)

    if not parsed:
        first = group[0] if group else {}
        return ResolutionOutcome(
            strategy=RESOLUTION_UNKNOWN,
            selected=first or None,
            resolved_value=None,
            unit=str(first.get("unit", "")),
            resolution_confidence=0.0,
            conflicting_values=[],
            alternative_property_ids=alternative_property_ids(all_ids),
            resolution_notes="no parsed properties in group",
        )

    if len(parsed) == 1:
        prop = parsed[0]
        selected_id = str(prop.get("property_id", ""))
        conf, note = compute_resolution_confidence(
            RESOLUTION_DIRECT,
            prop,
            [prop],
            parsed,
        )
        return ResolutionOutcome(
            strategy=RESOLUTION_DIRECT,
            selected=prop,
            resolved_value=prop.get("normalized_value", prop.get("parsed_value")),
            unit=str(prop.get("unit", "")),
            resolution_confidence=conf,
            conflicting_values=[],
            alternative_property_ids=alternative_property_ids(all_ids, selected_id),
            resolution_notes=f"single parsed property; {note}",
        )

    value_groups: Dict[str, List[dict[str, Any]]] = {}
    for prop in parsed:
        key = normalize_value_key(prop)
        value_groups.setdefault(key, []).append(prop)

    distinct = len(value_groups)
    conflicting_values = sorted({normalize_value_key(p) for p in parsed if normalize_value_key(p)})

    if distinct == 1:
        winners = parsed
        best = max(parsed, key=lambda p: float(p.get("confidence", 0.0)))
        selected_id = str(best.get("property_id", ""))
        conf, note = compute_resolution_confidence(
            RESOLUTION_IDENTICAL,
            best,
            winners,
            parsed,
        )
        return ResolutionOutcome(
            strategy=RESOLUTION_IDENTICAL,
            selected=best,
            resolved_value=best.get("normalized_value", best.get("parsed_value")),
            unit=str(best.get("unit", "")),
            resolution_confidence=conf,
            conflicting_values=[],
            alternative_property_ids=alternative_property_ids(all_ids, selected_id),
            resolution_notes=f"all parsed values identical; {note}",
        )

    counts = {key: len(props) for key, props in value_groups.items()}
    max_count = max(counts.values())
    plurality_winners = [key for key, count in counts.items() if count == max_count]

    if len(plurality_winners) == 1 and max_count >= 2:
        win_key = plurality_winners[0]
        winners = value_groups[win_key]
        best = max(winners, key=lambda p: float(p.get("confidence", 0.0)))
        selected_id = str(best.get("property_id", ""))
        conf, note = compute_resolution_confidence(
            RESOLUTION_MAJORITY,
            best,
            winners,
            parsed,
            distinct_count=distinct,
        )
        return ResolutionOutcome(
            strategy=RESOLUTION_MAJORITY,
            selected=best,
            resolved_value=best.get("normalized_value", best.get("parsed_value")),
            unit=str(best.get("unit", "")),
            resolution_confidence=conf,
            conflicting_values=[v for v in conflicting_values if v != win_key],
            alternative_property_ids=alternative_property_ids(all_ids, selected_id),
            resolution_notes=f"plurality winner count={max_count}; {note}",
        )

    weights: Dict[str, float] = {}
    for key, props in value_groups.items():
        weights[key] = sum(float(p.get("confidence", 0.0)) for p in props)
    max_weight = max(weights.values())
    weight_winners = [key for key, weight in weights.items() if weight == max_weight]

    if len(weight_winners) == 1:
        win_key = weight_winners[0]
        winners = value_groups[win_key]
        best = max(winners, key=lambda p: float(p.get("confidence", 0.0)))
        selected_id = str(best.get("property_id", ""))
        total_weight = sum(weights.values())
        weighted_support = max_weight / total_weight if total_weight else 0.0
        conf, note = compute_resolution_confidence(
            RESOLUTION_WEIGHTED_MAJORITY,
            best,
            winners,
            parsed,
            distinct_count=distinct,
            weighted_support=weighted_support,
        )
        return ResolutionOutcome(
            strategy=RESOLUTION_WEIGHTED_MAJORITY,
            selected=best,
            resolved_value=best.get("normalized_value", best.get("parsed_value")),
            unit=str(best.get("unit", "")),
            resolution_confidence=conf,
            conflicting_values=[v for v in conflicting_values if v != win_key],
            alternative_property_ids=alternative_property_ids(all_ids, selected_id),
            resolution_notes=f"weighted sum={max_weight:.4f}; {note}",
        )

    best = max(parsed, key=lambda p: float(p.get("confidence", 0.0)))
    top_conf = float(best.get("confidence", 0.0))
    top_props = [p for p in parsed if float(p.get("confidence", 0.0)) == top_conf]
    top_values = {normalize_value_key(p) for p in top_props}

    if len(top_props) == 1 and len(top_values) == 1:
        conf, note = compute_resolution_confidence(
            RESOLUTION_HIGHEST_CONFIDENCE,
            best,
            [best],
            parsed,
            distinct_count=distinct,
        )
        selected_id = str(best.get("property_id", ""))
        return ResolutionOutcome(
            strategy=RESOLUTION_HIGHEST_CONFIDENCE,
            selected=best,
            resolved_value=best.get("normalized_value", best.get("parsed_value")),
            unit=str(best.get("unit", "")),
            resolution_confidence=conf,
            conflicting_values=[v for v in conflicting_values if v != normalize_value_key(best)],
            alternative_property_ids=alternative_property_ids(all_ids, selected_id),
            resolution_notes=f"unique highest confidence={top_conf:.4f}; {note}",
        )

    conf, note = compute_resolution_confidence(
        RESOLUTION_CONFLICT,
        best,
        parsed,
        parsed,
        distinct_count=distinct,
        value_groups=value_groups,
    )
    selected_id = str(best.get("property_id", ""))
    return ResolutionOutcome(
        strategy=RESOLUTION_CONFLICT,
        selected=best,
        resolved_value=best.get("normalized_value", best.get("parsed_value")),
        unit=str(best.get("unit", "")),
        resolution_confidence=conf,
        conflicting_values=conflicting_values,
        alternative_property_ids=alternative_property_ids(all_ids, selected_id),
        resolution_notes=f"unresolvable conflict among {distinct} values; {note}",
    )
