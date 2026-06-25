"""Phase D.3 — validate group annotation expansion."""

from typing import Any, Dict, List, Set

from src.framing.beam_geometry import beam_mark_sort_key
from src.grouping.beam_group_types import ExpandedAnnotation, GroupOwnershipRecord, ValidationStatus


class GroupAnnotationValidator:
    """Validate shared annotation expansion integrity."""

    def validate(
        self,
        ownership_records: List[GroupOwnershipRecord],
        expanded: List[ExpandedAnnotation],
    ) -> Dict[str, Any]:
        issues: List[str] = []
        warnings: List[str] = []

        group_records = [r for r in ownership_records if r["ownership_mode"] == "GROUP"]
        expanded_ids: Set[str] = set()
        source_ids: Set[str] = set()

        for record in group_records:
            source_ids.add(record["annotation_id"])
            expected_members = set(record["member_beams"])
            actual_members = {
                e["beam_mark"]
                for e in expanded
                if e["shared_annotation_id"] == record["annotation_id"]
            }
            if actual_members != expected_members:
                issues.append(
                    f"Annotation {record['annotation_id']}: expected members "
                    f"{sorted(expected_members)} got {sorted(actual_members)}"
                )

        for entry in expanded:
            expanded_ids.add(entry["shared_annotation_id"])
            if not entry.get("shared_annotation_id"):
                issues.append("Expanded annotation missing shared_annotation_id")
            if entry.get("expanded_from_group") and not entry.get("beam_group_id"):
                issues.append(f"Group expansion missing beam_group_id for {entry['beam_mark']}")
            ref = entry.get("original_annotation_reference", {})
            if not ref.get("clean_text"):
                warnings.append(f"Expanded {entry['beam_mark']} missing original reference text")

        orphans = source_ids - expanded_ids
        if orphans:
            issues.append(f"Orphan group annotations not expanded: {sorted(orphans)}")

        duplicate_keys = [
            (e["shared_annotation_id"], e["beam_mark"]) for e in expanded
        ]
        if len(duplicate_keys) != len(set(duplicate_keys)):
            issues.append("Duplicate expansion for same annotation and beam")

        status: ValidationStatus = "FAIL" if issues else ("WARN" if warnings else "PASS")
        return {
            "status": status,
            "group_annotation_count": len(group_records),
            "expanded_annotation_count": len(expanded),
            "issues": issues,
            "warnings": warnings,
        }
