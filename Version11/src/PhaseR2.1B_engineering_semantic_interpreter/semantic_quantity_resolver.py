"""
semantic_quantity_resolver.py — Preserve engineering quantity without multiplying.
MODEL_VERSION: 7.11.0

Rules:
  - Quantity is the raw parsed count from the annotation (e.g. "2-Y10" → 2).
  - O.E.F. modifier means "1 per face" — quantity stays 2 (2 bars total across both faces).
  - BOTH FACE modifier means the set appears on both faces — preserved as-is.
  - NO multiplication happens here. The future calculation engine decides multipliers.
"""
from __future__ import annotations

from typing import List

from .semantic_models import SemanticContext, SemanticModifier


class SemanticQuantityResolver:
    """
    Extract and validate the engineering quantity from the annotation context.

    Returns (quantity: int, notes: list[str]).
    """

    def resolve(
        self,
        ctx: SemanticContext,
        modifiers: List[SemanticModifier],
    ) -> tuple:
        notes = []
        qty = ctx.quantity

        if qty == 0 and ctx.is_reinforcement:
            # Fallback: attempt to read from bar_label e.g. "2Y10"
            import re
            m = re.match(r"(\d+)[YRTyrt]", ctx.bar_label)
            if m:
                qty = int(m.group(1))
                notes.append(f"Quantity from bar_label fallback: {qty}")

        mod_names = [m.canonical for m in modifiers]

        if "ONE_EACH_FACE" in mod_names:
            notes.append(
                f"O.E.F. modifier: quantity={qty} means {qty} bars, "
                "1 per face — NOT multiplied here"
            )
        elif "BOTH_FACES" in mod_names:
            notes.append(
                f"BOTH FACE modifier: quantity={qty} bars on both faces — "
                "NOT multiplied here"
            )
        else:
            notes.append(f"Quantity: {qty}")

        return qty, notes
