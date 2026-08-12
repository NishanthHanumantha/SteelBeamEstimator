"""Metrics for P2.5.1 Quantity Intent Schema (coverage, not accuracy)."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Sequence

from .config import (
    STATUS_COMPOSITE,
    STATUS_EXPLICIT,
    STATUS_INVALID,
    STATUS_SPACING_BASED,
    STATUS_UNRESOLVED,
    VALIDATION_PASS,
)
from .models import QuantityIntent


def compute_metrics(
    *,
    intents: Sequence[QuantityIntent],
    eligible_annotation_count: int,
) -> Dict[str, Any]:
    n = len(intents)
    explicit = sum(1 for i in intents if i.quantity_status == STATUS_EXPLICIT)
    composite = sum(1 for i in intents if i.quantity_status == STATUS_COMPOSITE)
    spacing = sum(1 for i in intents if i.quantity_status == STATUS_SPACING_BASED)
    unresolved = sum(1 for i in intents if i.quantity_status == STATUS_UNRESOLVED)
    invalid = sum(1 for i in intents if i.quantity_status == STATUS_INVALID)
    provenance_ok = sum(
        1 for i in intents if i.evidence_links and i.evidence_links.has_provenance
    )
    validation_pass = sum(1 for i in intents if i.validation_status == VALIDATION_PASS)

    def pct(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round(100.0 * num / den, 2)

    role_dist = Counter(i.reinforcement_role for i in intents)
    sem_dist = Counter(i.semantic_type for i in intents)
    qty_dist = Counter(
        i.quantity_value for i in intents if i.quantity_value is not None
    )
    dia_dist = Counter(
        int(i.diameter_value_mm)
        for i in intents
        if i.diameter_value_mm is not None and float(i.diameter_value_mm).is_integer()
    )
    unresolved_patterns = Counter(
        i.raw_text for i in intents if i.quantity_status == STATUS_UNRESOLVED
    )

    return {
        "eligible_annotations": eligible_annotation_count,
        "quantity_intents_generated": n,
        "explicit_quantity": explicit,
        "composite_quantity": composite,
        "spacing_stirrup": spacing,
        "unresolved": unresolved,
        "invalid": invalid,
        "QUANTITY_INTENT_COVERAGE": pct(n, eligible_annotation_count),
        "EXPLICIT_QUANTITY_RATE": pct(explicit, n),
        "UNRESOLVED_QUANTITY_RATE": pct(unresolved, n),
        "PROVENANCE_COVERAGE": pct(provenance_ok, n),
        "VALIDATION_PASS_RATE": pct(validation_pass, n),
        "COMPOSITE_RATE": pct(composite, n),
        "SPACING_BASED_RATE": pct(spacing, n),
        "role_distribution": dict(role_dist),
        "semantic_distribution": dict(sem_dist),
        "quantity_distribution": {str(k): v for k, v in qty_dist.items()},
        "diameter_distribution": {str(k): v for k, v in dia_dist.items()},
        "top_unresolved_patterns": unresolved_patterns.most_common(20),
    }
