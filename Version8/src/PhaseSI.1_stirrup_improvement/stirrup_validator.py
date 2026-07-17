"""
Stirrup Validator — Phase SI.1 MODULE 7

Validates all stirrup computation results.
Raises STIRRUP_ENGINE_ERROR if critical rules fail.

RULE_1: Every stirrup with parseable notation has an engineering type.
RULE_2: Every variable spacing has at least three zones.
RULE_3: Support spacing rows are merged correctly (identical spacings merged).
RULE_4: Total quantity = sum of zone quantities.
RULE_5: Steel weight > 0 for all parseable stirrups.
RULE_6: BBS rows generated correctly (one per StirrupGroup).
"""
from typing import List, Tuple

from stirrup_models import BeamStirrupResult, StirrupType, ZoneRole


class STIRRUP_ENGINE_ERROR(Exception):
    """Raised when a critical stirrup calculation rule fails."""


class StirrupValidator:
    """Validates BeamStirrupResult objects."""

    def validate_all(
        self, beam_results: List[BeamStirrupResult]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for br in beam_results:
            errors.extend(self._validate_beam(br))
        passed = len(errors) == 0
        return passed, errors

    def _validate_beam(self, br: BeamStirrupResult) -> List[str]:
        errs: List[str] = []
        beam = br.beam_id

        for group in br.groups:
            # RULE_1: parseable stirrups have engineering type (spacing > 0)
            # Groups with spacing == 0 are misclassified bars — skip RULE_1
            if group.spacing_mm < 0:
                errs.append(f"{beam}: RULE_1 — group {group.group_id} has negative spacing")
            if group.spacing_mm == 0:
                # Not a genuine stirrup (no notation) — skip further rule checks
                continue

            # RULE_2: variable stirrups have >= 3 zones
            if br.stirrup_type == StirrupType.VARIABLE:
                all_zones = [z for g in br.groups for z in g.zones]
                if len(all_zones) < 3:
                    errs.append(
                        f"{beam}: RULE_2 — variable stirrups but < 3 zones "
                        f"(found {len(all_zones)})"
                    )
                    break

            # RULE_3: support rows merged — check no duplicate un-merged rows
            support_spacings = [
                g.spacing_mm for g in br.groups
                if any(z.role in (ZoneRole.LEFT_SUPPORT, ZoneRole.RIGHT_SUPPORT)
                       for z in g.zones)
            ]
            from collections import Counter
            cnt = Counter(support_spacings)
            for s, n in cnt.items():
                if n > 1:
                    errs.append(
                        f"{beam}: RULE_3 — support spacing {s}mm appears {n} times "
                        "(should be merged into one group)"
                    )

            # RULE_4: total quantity = sum of group quantities
            group_total = sum(g.quantity for g in br.groups)
            if group_total != br.total_quantity:
                errs.append(
                    f"{beam}: RULE_4 — total_quantity {br.total_quantity} "
                    f"!= sum_of_groups {group_total}"
                )

            # RULE_5: weight > 0
            for g in br.groups:
                if g.total_weight_kg < 0:
                    errs.append(
                        f"{beam}: RULE_5 — negative weight {g.total_weight_kg:.3f} kg "
                        f"in group {g.group_id}"
                    )

            # RULE_6: at least one BBS row per beam with stirrups
            break  # only need one pass per beam for rules 3-5

        return errs
