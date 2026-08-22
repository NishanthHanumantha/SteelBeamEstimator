"""Shadow hybrid engineering binding. No calculations. No production. No beam-ID branches."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from .binding_status import decide_beam_status, decide_group_status
from .config import (
    STATUS_AMBIGUOUS,
    STATUS_BOUND,
    STATUS_INVALID,
    STATUS_MISSING_GEOM,
    STATUS_MISSING_RULE,
    STATUS_MISSING_SUPPORT,
    STATUS_PARTIAL,
    STATUS_UNSUPPORTED,
)
from .engineering_rule_binder import bind_longitudinal_rules, bind_spacers, bind_stirrup_engineering, default_rule_catalog
from .geometry_binder import bind_geometry
from .provenance import is_ambiguous_group, is_possible_duplicate, semantic_snapshot
from .support_binder import bind_support


def _field_value(rec: Any) -> Any:
    if isinstance(rec, dict) and "value" in rec:
        return rec.get("value")
    return rec


def _group_sort_key(row: Dict[str, Any]) -> tuple:
    sem = row.get("semantic") or {}
    return (
        str(row.get("origin") or ""),
        str(row.get("group_id") or ""),
        str(sem.get("layer") or ""),
        str(sem.get("specification") or ""),
        str(sem.get("role") or ""),
    )


def _semantic_valid(group: Dict[str, Any]) -> bool:
    layer = _field_value(group.get("layer"))
    role = _field_value(group.get("role"))
    if group.get("origin") not in (
        "MATCHED",
        "VISION_ONLY_GROUP",
        "DETERMINISTIC_ONLY_GROUP",
        "AMBIGUOUS",
        None,
        "",
    ) and not str(group.get("origin") or ""):
        return False
    if not isinstance(group, dict):
        return False
    if layer is None and role is None and _field_value(group.get("diameter")) is None:
        return False
    return True


def bind_group(
    *,
    beam_id: str,
    hybrid: Dict[str, Any],
    group: Dict[str, Any],
    geometry: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    rule_catalog: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    origin = str(group.get("origin") or "")
    semantic = semantic_snapshot(hybrid=hybrid, group=group)
    reasons: List[str] = []
    invalid = not _semantic_valid(group)
    ambiguous = is_ambiguous_group(group, hybrid)
    duplicate = is_possible_duplicate(group, hybrid)
    if duplicate:
        reasons.append("POSSIBLE_DUPLICATE_PRESERVED")
    if origin == "DETERMINISTIC_ONLY_GROUP":
        reasons.append("DETERMINISTIC_ONLY_PRESERVED")
    if origin == "VISION_ONLY_GROUP" and not ambiguous:
        reasons.append("VISION_ONLY_BINDING_ATTEMPTED")

    missing_geometry = not geometry.get("available")
    if missing_geometry:
        reasons.append(STATUS_MISSING_GEOM)

    support = bind_support(
        support_scope=semantic.get("support_scope"),
        model=model,
        span_mm=geometry.get("span_mm"),
    )
    rules = bind_longitudinal_rules(group=group, model=model, rule_catalog=rule_catalog)

    missing_support = bool(support.get("missing"))
    support_ambiguous = bool(support.get("ambiguous"))
    missing_rule = bool(rules.get("missing"))
    partial = bool(support.get("partial")) or (
        origin == "VISION_ONLY_GROUP" and rules.get("instance_cut_length_reference") is None and not missing_rule and not missing_geometry
    )
    if origin == "VISION_ONLY_GROUP" and rules.get("instance_cut_length_reference") is None and not missing_rule:
        reasons.append("VISION_ONLY_RULE_FAMILY_BOUND_INSTANCE_UNAVAILABLE")
        # Family is enough for compatibility; instance absence is diagnostic, not a hard miss.
        partial = False
    if support.get("reason"):
        reasons.append(str(support.get("reason")))
    if rules.get("reason"):
        reasons.append(str(rules.get("reason")))
    if support_ambiguous and not ambiguous:
        ambiguous = True
        reasons.append("AMBIGUOUS_SUPPORT_REFERENCE")
    if missing_support:
        reasons.append(STATUS_MISSING_SUPPORT)
    if missing_rule:
        reasons.append(STATUS_MISSING_RULE)
    if geometry.get("available"):
        reasons.append("GEOM_OK")
    if geometry.get("section_available"):
        reasons.append("SECTION_OK")

    unsupported = False
    if str(semantic.get("role") or "").upper() in ("UNKNOWN_UNSUPPORTED",):
        unsupported = True

    status = decide_group_status(
        invalid=invalid,
        ambiguous=ambiguous,
        unsupported=unsupported,
        missing_geometry=missing_geometry and not invalid and not ambiguous,
        missing_support=missing_support and not ambiguous,
        missing_rule=missing_rule and not ambiguous,
        partial=partial and not ambiguous,
    )
    if status == STATUS_BOUND and not geometry.get("section_available"):
        status = STATUS_PARTIAL
        reasons.append("SECTION_GEOMETRY_PARTIAL")
    binding = {
        "beam_geometry_reference": geometry.get("beam_geometry_reference"),
        "section_geometry_reference": geometry.get("section_geometry_reference"),
        "longitudinal_direction": geometry.get("longitudinal_direction") or "UNKNOWN",
        "span_reference": support.get("span_reference"),
        "support_reference": support.get("support_reference"),
        "cut_length_rule_reference": rules.get("cut_length_rule_reference"),
        "development_length_reference": rules.get("development_length_reference"),
        "anchorage_reference": rules.get("anchorage_reference"),
        "hook_bend_reference": rules.get("hook_bend_reference"),
        "instance_cut_length_reference": rules.get("instance_cut_length_reference"),
        "binding_status": status,
        "binding_reasons": reasons,
        "calculated": {
            "cut_length": False,
            "development_length": False,
            "anchorage": False,
            "hook_bend": False,
            "steel_weight": False,
        },
    }
    unresolved = []
    if missing_geometry:
        unresolved.append("beam_geometry_reference")
        unresolved.append("section_geometry_reference")
    elif not geometry.get("section_available"):
        unresolved.append("section_geometry_reference")
    if missing_support:
        unresolved.append("support_reference")
    if support_ambiguous:
        unresolved.append("support_reference")
    if missing_rule:
        unresolved.extend(
            [
                "cut_length_rule_reference",
                "development_length_reference",
                "anchorage_reference",
                "hook_bend_reference",
            ]
        )
    return {
        "beam_id": beam_id,
        "group_id": group.get("group_id"),
        "origin": origin,
        "ambiguous": ambiguous,
        "possible_duplicate": duplicate,
        "semantic": semantic,
        "engineering_binding": binding,
        "resolved_references": {
            k: binding.get(k)
            for k in (
                "beam_geometry_reference",
                "section_geometry_reference",
                "longitudinal_direction",
                "span_reference",
                "support_reference",
                "cut_length_rule_reference",
                "development_length_reference",
                "anchorage_reference",
                "hook_bend_reference",
            )
            if binding.get(k) not in (None,)
        },
        "unresolved_references": unresolved,
        "diagnostics": {
            "origin": origin,
            "status": status,
            "reasons": reasons,
            "possible_duplicate": duplicate,
            "ambiguous": ambiguous,
        },
    }


def bind_beam(
    *,
    hybrid: Dict[str, Any],
    catalog: Dict[str, Any],
    rule_catalog: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    beam_id = str(hybrid.get("beam_id") or "")
    rules = rule_catalog if rule_catalog is not None else default_rule_catalog()
    model = catalog.get(beam_id) if isinstance(catalog, dict) else None
    geometry = bind_geometry(beam_id=beam_id, catalog=catalog or {})
    groups_in = list(hybrid.get("reinforcement_groups") or [])
    bound_groups = [
        bind_group(
            beam_id=beam_id,
            hybrid=hybrid,
            group=g,
            geometry=geometry,
            model=model,
            rule_catalog=rules,
        )
        for g in groups_in
        if isinstance(g, dict)
    ]
    bound_groups.sort(key=_group_sort_key)

    stirrup_block = hybrid.get("stirrups") if isinstance(hybrid.get("stirrups"), dict) else {}
    stirrup_items = []
    for idx, item in enumerate(stirrup_block.get("items") or []):
        if not isinstance(item, dict):
            continue
        eng = bind_stirrup_engineering(item=item, model=model, rule_catalog=rules)
        ident = item.get("semantic_identification") if isinstance(item.get("semantic_identification"), dict) else {}
        stirrup_items.append(
            {
                "beam_id": beam_id,
                "group_id": f"STIRRUP-{idx + 1}",
                "origin": item.get("origin"),
                "semantic_identification": deepcopy(ident),
                "semantic_identification_authority": stirrup_block.get("semantic_identification_authority") or "VISION_PREFERRED",
                "engineering_calculation_authority": stirrup_block.get("engineering_calculation_authority") or "DETERMINISTIC_ENGINEERING",
                "engineering_binding": {
                    "stirrup_engineering_reference": eng.get("stirrup_engineering_reference"),
                    "binding_status": STATUS_MISSING_RULE if eng.get("missing") else STATUS_BOUND,
                    "binding_reasons": [eng.get("reason")],
                    "quantities_calculated": False,
                    "si_replaced": False,
                },
            }
        )

    spacers = bind_spacers(spacers=hybrid.get("spacers") if isinstance(hybrid.get("spacers"), dict) else {}, rule_catalog=rules)
    statuses = [g["engineering_binding"]["binding_status"] for g in bound_groups]
    overall = decide_beam_status(statuses)
    counts = {
        "total_groups": len(bound_groups),
        "bound_groups": sum(1 for s in statuses if s == STATUS_BOUND),
        "partially_bound_groups": sum(1 for s in statuses if s == STATUS_PARTIAL),
        "ambiguous_groups": sum(1 for s in statuses if s == STATUS_AMBIGUOUS),
        "unsupported_groups": sum(1 for s in statuses if s == STATUS_UNSUPPORTED),
        "invalid_groups": sum(1 for s in statuses if s == STATUS_INVALID),
        "missing_geometry_groups": sum(1 for s in statuses if s == STATUS_MISSING_GEOM),
        "missing_support_groups": sum(1 for s in statuses if s == STATUS_MISSING_SUPPORT),
        "missing_rule_groups": sum(1 for s in statuses if s == STATUS_MISSING_RULE),
    }

    def _cov(key: str, pred) -> str:
        if not bound_groups:
            return "NONE"
        n = sum(1 for g in bound_groups if pred(g))
        if n == len(bound_groups):
            return "AVAILABLE"
        if n == 0:
            return "MISSING"
        return "PARTIAL"

    compatibility = {
        "beam_id": beam_id,
        **counts,
        "beam_geometry_available": bool(geometry.get("available")),
        "section_geometry_available": bool(geometry.get("section_available")),
        "support_information_available": bool(
            isinstance(model, dict) and (model.get("support_zones") or [])
        ) or any(
            (g.get("engineering_binding") or {}).get("support_reference") for g in bound_groups
        ),
        "cut_length_compatibility": _cov("cut", lambda g: (g.get("engineering_binding") or {}).get("cut_length_rule_reference")),
        "development_length_compatibility": _cov("dl", lambda g: (g.get("engineering_binding") or {}).get("development_length_reference")),
        "anchorage_compatibility": _cov("anc", lambda g: (g.get("engineering_binding") or {}).get("anchorage_reference")),
        "hook_bend_compatibility": _cov("hk", lambda g: (g.get("engineering_binding") or {}).get("hook_bend_reference")),
        "overall_status": overall,
        "reasons": sorted({r for g in bound_groups for r in (g.get("engineering_binding") or {}).get("binding_reasons") or []}),
        "group_matching_preserved": deepcopy(hybrid.get("group_matching") or {}),
        "possible_duplicate_groups_preserved": deepcopy(hybrid.get("possible_duplicate_groups") or []),
        "spacers_deterministic_only": spacers.get("source") == "DETERMINISTIC",
        "stirrup_authority_split": {
            "semantic_identification_authority": stirrup_block.get("semantic_identification_authority") or "VISION_PREFERRED",
            "engineering_calculation_authority": stirrup_block.get("engineering_calculation_authority") or "DETERMINISTIC_ENGINEERING",
        },
        "calculations_performed": {
            "cut_length": False,
            "development_length": False,
            "steel_weight": False,
            "bbs": False,
        },
        "longest_bar_main_override": False,
    }
    return {
        "beam_id": beam_id,
        "target_identity": deepcopy(hybrid.get("target_identity")),
        "geometry": geometry,
        "groups": bound_groups,
        "stirrups": stirrup_items,
        "spacers": spacers,
        "compatibility": compatibility,
        "source_categories": {
            "matched": sum(1 for g in bound_groups if g.get("origin") == "MATCHED"),
            "vision_only": sum(1 for g in bound_groups if g.get("origin") == "VISION_ONLY_GROUP"),
            "deterministic_only": sum(1 for g in bound_groups if g.get("origin") == "DETERMINISTIC_ONLY_GROUP"),
            "ambiguous": sum(1 for g in bound_groups if g.get("ambiguous")),
            "possible_duplicates": sum(1 for g in bound_groups if g.get("possible_duplicate")),
        },
    }


def bind_population(
    *,
    hybrids: List[Dict[str, Any]],
    catalog: Dict[str, Any],
    rule_catalog: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    rows = []
    for hybrid in hybrids:
        if not isinstance(hybrid, dict):
            continue
        rows.append(bind_beam(hybrid=hybrid, catalog=catalog, rule_catalog=rule_catalog))
    rows.sort(key=lambda r: str(r.get("beam_id") or ""))
    return rows


__all__ = ["bind_beam", "bind_group", "bind_population"]
