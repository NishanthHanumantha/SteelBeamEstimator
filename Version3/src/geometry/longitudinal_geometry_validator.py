"""Phase D.4.2 — validation for longitudinal geometry resolution."""

from typing import Any, Dict, List


class LongitudinalGeometryValidator:
    """Verify longitudinal bars received geometry-based resolution."""

    def validate(
        self,
        enriched_objects: List[dict[str, Any]],
        resolutions: List[dict[str, Any]],
    ) -> dict[str, Any]:
        longitudinal = [
            obj
            for obj in enriched_objects
            if obj.get("engineering_type") == "LONGITUDINAL_BAR"
            and obj.get("parser_status") == "SUCCESS"
        ]
        failures: List[str] = []
        duplicate_attachments: Dict[str, List[str]] = {}

        for obj in longitudinal:
            object_id = str(obj.get("object_id", ""))
            geo = obj.get("geometry_resolution") or {}
            if not obj.get("resolved_position"):
                failures.append(f"{object_id}: missing resolved_position")
            continuity = obj.get("resolved_continuity")
            if continuity is None:
                failures.append(f"{object_id}: missing resolved_continuity")
            if geo.get("coverage_ratio") is None:
                failures.append(f"{object_id}: missing coverage_ratio")
            if not geo.get("attached_entity_id"):
                failures.append(f"{object_id}: missing geometry attachment")
            entity_id = geo.get("attached_entity_id")
            if entity_id:
                duplicate_attachments.setdefault(str(entity_id), []).append(object_id)

        valid_duplicates = sum(
            1
            for ids in duplicate_attachments.values()
            if len(ids) > 1
        )

        status = "PASS" if not failures else "FAIL"
        return {
            "status": status,
            "longitudinal_bar_count": len(longitudinal),
            "resolution_record_count": len(resolutions),
            "failure_count": len(failures),
            "failures": failures[:50],
            "duplicate_attachment_groups": valid_duplicates,
            "checks": {
                "all_have_resolved_position": all(
                    o.get("resolved_position") for o in longitudinal
                ),
                "all_have_resolved_continuity": all(
                    o.get("resolved_continuity") is not None for o in longitudinal
                ),
                "all_have_attachment": all(
                    (o.get("geometry_resolution") or {}).get("attached_entity_id")
                    for o in longitudinal
                ),
            },
        }
