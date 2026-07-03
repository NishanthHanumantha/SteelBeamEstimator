"""Select active development length table from Table-2 steel grade."""

from typing import Any, Dict, Optional, Tuple


def steel_base_numeric(grade: str) -> str:
    cleaned = grade.upper().replace("FE", "").replace("D", "").strip()
    return cleaned


def steel_table_key(grade: str) -> str:
    """Map Fe550D → Fe550 for LD table lookup key."""
    cleaned = grade.upper().replace(" ", "")
    if cleaned.startswith("FY"):
        return f"Fe{steel_base_numeric(cleaned)}"
    if cleaned.startswith("FE"):
        return f"Fe{steel_base_numeric(cleaned)}"
    return grade


class LdTableSelector:
    """Bind project steel grade to the correct development length table."""

    def select(
        self,
        table2_steel: Optional[dict[str, Any]],
        ld_tables: Dict[str, Dict[str, Dict[int, int]]],
        materials_default: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        designation: Optional[str] = None
        base_grade: Optional[str] = None
        source = "UNKNOWN"

        if table2_steel:
            designation = table2_steel.get("grade")
            base_grade = table2_steel.get("base_grade") or steel_table_key(
                designation or ""
            )
            source = table2_steel.get("source", "TABLE_2")
        elif materials_default:
            designation = materials_default.get("grade")
            base_grade = steel_table_key(designation or "")
            source = "MATERIALS_DEFAULT"

        if not base_grade:
            return {
                "active_development_length_table": None,
                "active_development_length_grade": None,
                "matched_table_key": None,
                "selection_reason": "No steel grade found in Table-2 or materials",
                "resolved_tables": dict(ld_tables),
            }

        logical_key = steel_table_key(base_grade)
        physical_key, reason = self._match_physical_table(logical_key, ld_tables)

        resolved_tables = dict(ld_tables)
        if (
            physical_key
            and logical_key not in resolved_tables
            and physical_key in resolved_tables
        ):
            resolved_tables[logical_key] = resolved_tables[physical_key]
            reason = (
                f"Table-2 steel {designation} uses LD table {logical_key} "
                f"(sourced from {physical_key} grid in drawing)"
            )

        active_table = resolved_tables.get(logical_key)

        return {
            "active_development_length_table": active_table,
            "active_development_length_grade": designation,
            "active_development_length_base": base_grade,
            "matched_table_key": logical_key,
            "physical_table_key": physical_key,
            "selection_reason": reason,
            "selection_source": source,
            "all_table_keys": list(ld_tables.keys()),
            "resolved_tables": resolved_tables,
        }

    def _match_physical_table(
        self,
        logical_key: str,
        ld_tables: Dict[str, Any],
    ) -> Tuple[Optional[str], str]:
        if logical_key in ld_tables:
            return logical_key, f"Exact LD table {logical_key} found in drawing"

        numeric = steel_base_numeric(logical_key)
        for key in ld_tables:
            if steel_base_numeric(key) == numeric:
                return key, f"Matched LD table {key} for designated {logical_key}"

        available = sorted(
            ld_tables.keys(),
            key=lambda k: int(steel_base_numeric(k) or "0"),
        )
        for key in reversed(available):
            if int(steel_base_numeric(key) or "0") <= int(numeric or "0"):
                return key, (
                    f"Designated {logical_key} mapped to nearest drawing table {key}"
                )

        if available:
            return available[-1], f"Fallback to highest available LD table {available[-1]}"
        return None, "No development length tables available"
