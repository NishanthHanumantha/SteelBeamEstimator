"""Phase D.4 — validation for engineering object parsing."""

from typing import Any, Dict, List, Literal

ValidationStatus = Literal["PASS", "WARN", "FAIL"]


class EngineeringParserValidator:
    """Validate D.4 parsing coverage and object integrity."""

    def validate(
        self,
        ownership_records: List[dict[str, Any]],
        parse_result: Dict[str, List[dict[str, Any]]],
    ) -> Dict[str, Any]:
        owned = [
            r for r in ownership_records if r.get("ownership_status") == "OWNED"
        ]
        objects = parse_result["engineering_objects"]
        failed = parse_result["failed"]

        object_ids = [o.get("object_id") for o in objects]
        duplicates = len(object_ids) - len(set(object_ids))

        missing_owner = [
            o for o in objects
            if not o.get("detail_region_id") or not o.get("owner_sketch_id")
        ]

        longitudinal = parse_result["parsed_longitudinal_bars"]
        stirrups = parse_result["parsed_stirrups"]
        anchorage = parse_result["parsed_anchorage"]
        sfr = parse_result["parsed_sfr"]

        warnings: List[str] = []
        if failed:
            warnings.append(f"{len(failed)} parse failure(s)")
        if missing_owner:
            warnings.append(f"{len(missing_owner)} object(s) missing owner fields")
        if duplicates:
            warnings.append(f"{duplicates} duplicate object_id(s)")

        status: ValidationStatus = "PASS"
        if failed:
            status = "WARN"
        if len(failed) > len(owned) * 0.1:
            status = "FAIL"

        parser_ready = status != "FAIL" and not missing_owner

        return {
            "status": status,
            "owned_annotation_count": len(owned),
            "engineering_object_count": len(objects),
            "longitudinal_bar_count": len(longitudinal),
            "stirrup_count": len(stirrups),
            "anchorage_count": len(anchorage),
            "sfr_count": len(sfr),
            "failed_parse_count": len(failed),
            "duplicate_object_count": duplicates,
            "missing_owner_count": len(missing_owner),
            "warnings": warnings,
            "parser_ready": parser_ready,
            "failed_samples": [
                {
                    "object_id": o.get("object_id"),
                    "clean_text": o.get("clean_text"),
                    "error": o.get("parse_error"),
                }
                for o in failed[:10]
            ],
        }
