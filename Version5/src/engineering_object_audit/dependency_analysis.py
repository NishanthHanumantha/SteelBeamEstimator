"""Analyse prerequisite availability for engineering object creation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class DependencyAnalyzer:
    """Evaluate dependency graph for each reinforcement annotation."""

    DEPENDENCY_ORDER = ("geometry", "beam", "section", "role", "position", "specification")

    def analyze_item(self, item: dict[str, Any], indexes: dict[str, Any]) -> dict[str, Any]:
        beam_id = str(item.get("beam_association") or "")
        geometry_id = str(item.get("geometry_id") or "")
        context = (indexes.get("contexts_by_beam") or {}).get(beam_id, {})
        properties = (indexes.get("properties_by_geometry") or {}).get(geometry_id, [])
        text_object = (indexes.get("text_by_geometry") or {}).get(geometry_id, {})

        geometry_present = bool(
            context.get("clear_span_mm")
            or context.get("effective_span_mm")
            or context.get("geometry_association_id")
            or context.get("association_id")
            or context.get("beam_geometry_id")
        )
        beam_present = bool(beam_id)
        section_present = bool(
            context.get("beam_width_mm")
            and context.get("beam_depth_mm")
        ) or bool(context.get("beam_section_id"))
        role_present = bool(item.get("role") and item.get("role") != "UNKNOWN")
        position_present = role_present and item.get("role") not in {None, "", "UNKNOWN"}
        specification_present = bool(
            item.get("engineering_object_id")
            or any(
                str(prop.get("property_type") or "") in {"BAR_TYPE", "DIAMETER", "QUANTITY", "REINFORCEMENT_TYPE"}
                for prop in properties
            )
            or str(text_object.get("engineering_status") or "") not in {"", "GEOMETRY_ONLY"}
        )

        components = {
            "geometry": {"present": geometry_present, "source": "calculation_context"},
            "beam": {"present": beam_present, "source": "beam_association"},
            "section": {"present": section_present, "source": "calculation_context"},
            "role": {"present": role_present, "source": "classification"},
            "position": {"present": position_present, "source": "classification"},
            "specification": {
                "present": specification_present,
                "source": "engineering_properties"
                if properties
                else "engineering_object_id"
                if item.get("engineering_object_id")
                else "missing",
            },
        }
        first_missing = self._first_missing(components)
        return {
            "discovery_id": item.get("discovery_id"),
            "components": components,
            "first_missing_dependency": first_missing,
            "dependency_graph": [
                {
                    "dependency": name,
                    "present": components[name]["present"],
                    "source": components[name]["source"],
                }
                for name in self.DEPENDENCY_ORDER
            ],
        }

    def analyze_all(self, inventory: List[dict[str, Any]], indexes: dict[str, Any]) -> dict[str, Any]:
        records = [self.analyze_item(item, indexes) for item in inventory]
        missing_counts: Dict[str, int] = {}
        for record in records:
            missing = record.get("first_missing_dependency")
            if missing:
                missing_counts[missing] = missing_counts.get(missing, 0) + 1
        ranked = sorted(
            [{"dependency": key, "count": value} for key, value in missing_counts.items()],
            key=lambda item: item["count"],
            reverse=True,
        )
        return {
            "records": records,
            "by_discovery_id": {record["discovery_id"]: record for record in records},
            "top_dependency_failures": ranked,
        }

    @staticmethod
    def _first_missing(components: dict[str, dict[str, Any]]) -> Optional[str]:
        for name in DependencyAnalyzer.DEPENDENCY_ORDER:
            if not components.get(name, {}).get("present"):
                return name
        return None
