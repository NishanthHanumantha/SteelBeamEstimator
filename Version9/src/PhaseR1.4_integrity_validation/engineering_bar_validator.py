"""Validate individual EngineeringBarModel entries."""
from __future__ import annotations
from typing import Any, Dict, List, Set

from .pipeline_data_loader import PipelineDataLoader
from .validation_models import RuleResult


class EngineeringBarValidator:

    MANDATORY_BAR_FIELDS = (
        "beam_id", "bar_role", "diameter_mm", "quantity", "zone",
    )

    def validate(
        self, loader: PipelineDataLoader, valid_roles: List[str]
    ) -> Dict[str, RuleResult]:
        bars = loader.engineering_bars()
        bar_ids_seen: Set[str] = set()
        duplicate_bar_ids: List[str] = []
        missing_fields = 0
        invalid_roles = 0
        zero_diameter = 0
        zero_quantity = 0
        null_beam_ids = 0
        record_sigs: Set[str] = set()
        duplicate_records = 0

        for beam in loader.engineering_beams():
            beam_id = beam.get("beam_id", "")
            for idx, bar in enumerate(beam.get("bars", [])):
                bar_id = f"{beam_id}::{idx}"
                if bar_id in bar_ids_seen:
                    duplicate_bar_ids.append(bar_id)
                bar_ids_seen.add(bar_id)

                for field in self.MANDATORY_BAR_FIELDS:
                    if bar.get(field) is None:
                        missing_fields += 1

                if not bar.get("beam_id"):
                    null_beam_ids += 1

                role = bar.get("bar_role", "")
                if role not in valid_roles:
                    invalid_roles += 1

                if float(bar.get("diameter_mm") or 0) <= 0:
                    zero_diameter += 1

                if int(bar.get("quantity") or 0) <= 0:
                    zero_quantity += 1

                geom = beam.get("geometry", {})
                if not geom:
                    missing_fields += 1

                sig = self._record_signature(beam_id, bar)
                if sig in record_sigs:
                    duplicate_records += 1
                record_sigs.add(sig)

        if len(duplicate_bar_ids) > 0:
            rule5_status = "ERROR"
            rule5_pass = False
            rule5_detail = f"duplicate_bar_ids={len(duplicate_bar_ids)}"
        elif duplicate_records > 0:
            rule5_status = "WARNING"
            rule5_pass = True
            rule5_detail = (
                f"expanded_duplicate_records={duplicate_records} "
                "(group expansion, not pipeline corruption)"
            )
        else:
            rule5_status = "PASS"
            rule5_pass = True
            rule5_detail = "no_duplicate_bar_ids"
        rule6_pass = missing_fields == 0
        rule7_pass = invalid_roles == 0
        rule8_pass = zero_diameter == 0
        rule9_pass = zero_quantity == 0

        return {
            "RULE_5": RuleResult(
                "RULE_5", rule5_status, rule5_detail, rule5_pass,
            ),
            "RULE_6": RuleResult(
                "RULE_6", "PASS" if rule6_pass else "ERROR",
                f"missing_mandatory_fields={missing_fields}", rule6_pass,
            ),
            "RULE_7": RuleResult(
                "RULE_7", "PASS" if rule7_pass else "WARNING",
                f"invalid_roles={invalid_roles}", rule7_pass,
            ),
            "RULE_8": RuleResult(
                "RULE_8", "PASS" if rule8_pass else "ERROR",
                f"zero_diameter={zero_diameter}", rule8_pass,
            ),
            "RULE_9": RuleResult(
                "RULE_9", "PASS" if rule9_pass else "ERROR",
                f"zero_quantity={zero_quantity}", rule9_pass,
            ),
            "_null_beam_ids": null_beam_ids,
        }

    @staticmethod
    def _record_signature(beam_id: str, bar: Dict[str, Any]) -> str:
        meta = bar.get("engineering_metadata", {})
        parts = (
            beam_id,
            bar.get("bar_role", ""),
            bar.get("bar_label", ""),
            str(bar.get("diameter_mm", "")),
            str(bar.get("quantity", "")),
            str(bar.get("zone", "")),
            str(meta.get("group_id", "")),
        )
        return "|".join(parts)
