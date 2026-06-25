"""Phase D.3 — validate beam group integrity."""

from typing import Any, Dict, List, Set

from src.framing.beam_geometry import beam_mark_sort_key
from src.grouping.beam_group_types import BeamGroup, ValidationStatus
from src.utils.bbox_utils import horizontal_overlap_ratio


class BeamGroupValidator:
    """Ensure every beam belongs to exactly one valid group."""

    def validate(
        self,
        beam_groups: List[BeamGroup],
        expected_beam_marks: List[str],
    ) -> Dict[str, Any]:
        issues: List[str] = []
        warnings: List[str] = []

        all_beams: List[str] = []
        group_ids: Set[str] = set()
        beam_to_group: Dict[str, str] = {}

        for group in beam_groups:
            group_id = group["beam_group_id"]
            if group_id in group_ids:
                issues.append(f"Duplicate group id {group_id}")
            group_ids.add(group_id)

            members = group["members"]
            if not members:
                issues.append(f"Group {group_id} has no members")

            for mark in members:
                if mark in beam_to_group:
                    issues.append(
                        f"Beam {mark} appears in groups {beam_to_group[mark]} and {group_id}"
                    )
                beam_to_group[mark] = group_id
                all_beams.append(mark)

            if group["is_multi_beam"] and len(members) < 2:
                warnings.append(f"Group {group_id} flagged multi-beam but has one member")

            if len(members) >= 2:
                bboxes = [group["bounding_box"]]
                for member in group["member_details"]:
                    overlap = horizontal_overlap_ratio(
                        group["bounding_box"], member["cell_bbox"]
                    )
                    if overlap < 0.01:
                        warnings.append(
                            f"Group {group_id} member {member['beam_mark']} "
                            "has weak horizontal overlap with group bbox"
                        )

        expected = sorted({m.upper() for m in expected_beam_marks}, key=beam_mark_sort_key)
        missing = [m for m in expected if m not in beam_to_group]
        extra = [m for m in beam_to_group if m not in expected]

        if missing:
            issues.append(f"Missing beams from groups: {', '.join(missing)}")
        if extra:
            warnings.append(f"Unexpected beams in groups: {', '.join(extra)}")

        status: ValidationStatus = "FAIL" if issues else ("WARN" if warnings else "PASS")

        return {
            "status": status,
            "group_count": len(beam_groups),
            "multi_beam_group_count": sum(1 for g in beam_groups if g["is_multi_beam"]),
            "beam_count": len(all_beams),
            "issues": issues,
            "warnings": warnings,
            "missing_beams": missing,
        }
