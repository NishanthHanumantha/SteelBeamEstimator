"""Bind hybrid groups to existing deterministic rule families. Do not calculate cut length, DL, or steel."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import RULE_ANCHORAGE, RULE_CUT_LENGTH, RULE_DL, RULE_HOOK, RULE_SPACER, RULE_STIRRUP_ENG

DEFAULT_LONGITUDINAL_RULES = {
    "cut_length_rule_reference": RULE_CUT_LENGTH,
    "development_length_reference": RULE_DL,
    "anchorage_reference": RULE_ANCHORAGE,
    "hook_bend_reference": RULE_HOOK,
}


def default_rule_catalog() -> Dict[str, Any]:
    return {
        "longitudinal": dict(DEFAULT_LONGITUDINAL_RULES),
        "stirrup": {"stirrup_engineering_reference": RULE_STIRRUP_ENG},
        "spacer": {"spacer_engineering_reference": RULE_SPACER},
    }


def _present(value: Any) -> bool:
    return value not in (None, "", "UNAVAILABLE", "UNKNOWN")


def bind_longitudinal_rules(
    *,
    group: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    rule_catalog: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    catalog = rule_catalog if isinstance(rule_catalog, dict) else None
    families = (catalog or {}).get("longitudinal") if catalog else None
    if not families:
        return {
            "cut_length_rule_reference": None,
            "development_length_reference": None,
            "anchorage_reference": None,
            "hook_bend_reference": None,
            "instance_cut_length_reference": None,
            "missing": True,
            "reason": "MISSING_RULE_REFERENCE",
        }
    eng = group.get("deterministic_engineering") if isinstance(group.get("deterministic_engineering"), dict) else {}
    instance_cut = eng.get("cut_length_reference")
    if not _present(instance_cut):
        instance_cut = None
    dl_regions = (model or {}).get("development_length_regions") if isinstance(model, dict) else None
    dl_ref = families.get("development_length_reference")
    if isinstance(dl_regions, list) and dl_regions:
        dl_ref = {
            "rule_family": families.get("development_length_reference"),
            "kind": "EXISTING_DL_REGIONS",
            "region_count": len(dl_regions),
        }
    return {
        "cut_length_rule_reference": families.get("cut_length_rule_reference"),
        "development_length_reference": dl_ref,
        "anchorage_reference": families.get("anchorage_reference"),
        "hook_bend_reference": families.get("hook_bend_reference"),
        "instance_cut_length_reference": instance_cut,
        "missing": not all(
            families.get(k)
            for k in (
                "cut_length_rule_reference",
                "development_length_reference",
                "anchorage_reference",
                "hook_bend_reference",
            )
        ),
        "reason": "RULE_FAMILY_BOUND" if families.get("cut_length_rule_reference") else "MISSING_RULE_REFERENCE",
        "calculated": False,
    }


def bind_stirrup_engineering(
    *,
    item: Dict[str, Any],
    model: Optional[Dict[str, Any]],
    rule_catalog: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    families = (rule_catalog or {}).get("stirrup") if isinstance(rule_catalog, dict) else None
    if not families:
        return {
            "stirrup_engineering_reference": None,
            "missing": True,
            "reason": "MISSING_RULE_REFERENCE",
            "quantities_calculated": False,
        }
    objects = (model or {}).get("stirrups") if isinstance(model, dict) else None
    existing = item.get("engineering_calculation_reference") if isinstance(item.get("engineering_calculation_reference"), dict) else {}
    ref = {
        "rule_family": families.get("stirrup_engineering_reference"),
        "source": "DETERMINISTIC",
        "authority": "DETERMINISTIC_ENGINEERING",
        "existing_object_count": len(objects) if isinstance(objects, list) else 0,
        "existing_instance": existing or None,
        "quantities_calculated": False,
        "si_replaced": False,
    }
    return {
        "stirrup_engineering_reference": ref,
        "missing": False,
        "reason": "STIRRUP_ENGINEERING_REFERENCE_BOUND",
        "quantities_calculated": False,
    }


def bind_spacers(*, spacers: Dict[str, Any], rule_catalog: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    families = (rule_catalog or {}).get("spacer") if isinstance(rule_catalog, dict) else None
    source = (spacers or {}).get("source") or "DETERMINISTIC"
    groups = list((spacers or {}).get("groups") or [])
    return {
        "source": source,
        "binding_status": "BOUND",
        "rule_reference": (families or {}).get("spacer_engineering_reference") or RULE_SPACER,
        "group_count": len(groups),
        "groups": groups,
        "authority": "DETERMINISTIC_ENGINEERING",
        "reason": "SPACER_DETERMINISTIC_ONLY",
        "vision_matched": False,
    }


__all__ = [
    "bind_longitudinal_rules",
    "bind_spacers",
    "bind_stirrup_engineering",
    "default_rule_catalog",
]
