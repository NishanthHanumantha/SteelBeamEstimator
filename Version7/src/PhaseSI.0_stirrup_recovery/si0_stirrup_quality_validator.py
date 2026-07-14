"""
Stirrup Quality Validator — Phase SI.0 MODULE 8

Validates the UPDATED beam models after recovery.

RULE_1: Every STIRRUP object has spacing_mm > 0
RULE_2: Every STIRRUP object has diameter_mm > 0
RULE_3: Every STIRRUP object has leg count (quantity) >= 2
RULE_4: Every STIRRUP bar_label contains '@'
RULE_5: Invalid labels (2Y16, 2Y20, etc.) must not remain
RULE_6: Benchmark beams B1/B2/B8/B9/B10 labels must be unchanged
RULE_7: Recovery report was generated
"""
import re
from typing import List, Tuple, Dict, Any

_INVALID_RE = re.compile(r"^(\d+)Y(\d+)$", re.IGNORECASE)
BENCHMARK_EXPECTED = {
    "B1": "2L-Y10@100",
    "B2": "2L-Y8@100/200/100",
    "B8": "2L-Y8@100",
    "B9": "2L-Y8@100",
    "B10": "2L-Y8@100",
}


def validate_updated_models(
    updated_models: List[Dict[str, Any]],
    recovery_results_generated: bool = True,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    for model in updated_models:
        beam_id  = model.get("beam_id", "?")
        stirrups = model.get("stirrups") or []

        for bar in stirrups:
            label   = str(bar.get("bar_label") or "")
            spacing = bar.get("spacing_mm")
            dia     = bar.get("diameter_mm")
            qty     = bar.get("quantity")

            # RULE_5: longitudinal label must not remain
            if _INVALID_RE.fullmatch(label.replace(" ", "")):
                errors.append(
                    f"RULE_5: {beam_id} still has invalid stirrup label '{label}'"
                )
                continue   # skip further checks — clearly wrong

            # RULE_4: must contain @
            if "@" not in label:
                errors.append(
                    f"RULE_4: {beam_id} stirrup label '{label}' has no '@'"
                )

            # RULE_1: spacing
            if spacing is None or float(spacing) <= 0:
                errors.append(
                    f"RULE_1: {beam_id} stirrup has missing/zero spacing_mm"
                )

            # RULE_2: diameter
            if dia is None or float(dia) <= 0:
                errors.append(
                    f"RULE_2: {beam_id} stirrup has missing/zero diameter_mm"
                )

            # RULE_3: leg count
            if qty is None or int(qty) < 2:
                errors.append(
                    f"RULE_3: {beam_id} stirrup has leg count < 2"
                )

        # RULE_6: benchmark beams unchanged
        if beam_id in BENCHMARK_EXPECTED:
            expected = BENCHMARK_EXPECTED[beam_id]
            if stirrups:
                actual = str(stirrups[0].get("bar_label") or "")
                if actual != expected:
                    errors.append(
                        f"RULE_6: Benchmark {beam_id} label changed: "
                        f"expected '{expected}', got '{actual}'"
                    )

    # RULE_7: report generated
    if not recovery_results_generated:
        errors.append("RULE_7: Recovery report was not generated")

    passed = len(errors) == 0
    return passed, errors
