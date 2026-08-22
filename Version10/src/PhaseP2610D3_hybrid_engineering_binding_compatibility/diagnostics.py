"""Population diagnostics and engineering-binding coverage. Not accuracy."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .config import (
    BEAM_AMBIGUOUS,
    BEAM_COMPATIBLE,
    BEAM_INCOMPATIBLE,
    BEAM_PARTIAL,
    STATUS_AMBIGUOUS,
    STATUS_BOUND,
    STATUS_INVALID,
    STATUS_MISSING_GEOM,
    STATUS_MISSING_RULE,
    STATUS_MISSING_SUPPORT,
    STATUS_PARTIAL,
    STATUS_UNSUPPORTED,
)

REQUIRED_KEYS = (
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


def _ref_bound(bind: Dict[str, Any], key: str) -> bool:
    val = bind.get(key)
    if key == "longitudinal_direction":
        return val in ("HORIZONTAL", "VERTICAL", "OTHER", "UNKNOWN")
    if key == "support_reference":
        if isinstance(val, dict) and val.get("kind") == "NOT_REQUIRED":
            return True
        return val not in (None, "", "UNAVAILABLE")
    return val not in (None, "", "UNAVAILABLE")


def group_coverage(group: Dict[str, Any]) -> Dict[str, Any]:
    bind = group.get("engineering_binding") or {}
    bound_n = sum(1 for k in REQUIRED_KEYS if _ref_bound(bind, k))
    total = len(REQUIRED_KEYS)
    return {
        "bound": bound_n,
        "total": total,
        "engineering_binding_coverage": round(bound_n / total, 4) if total else 0.0,
        "by_key": {k: _ref_bound(bind, k) for k in REQUIRED_KEYS},
    }


def _origin_bucket(group: Dict[str, Any]) -> str:
    if group.get("ambiguous"):
        return "ambiguous"
    origin = str(group.get("origin") or "")
    if origin == "MATCHED":
        return "matched"
    if origin == "VISION_ONLY_GROUP":
        return "vision_only"
    if origin == "DETERMINISTIC_ONLY_GROUP":
        return "deterministic_only"
    return "other"


def build_diagnostics(bound_beams: List[Dict[str, Any]]) -> Dict[str, Any]:
    beam_status = Counter()
    group_status = Counter()
    origins = Counter()
    dup_preserved = 0
    amb_unresolved = 0
    matched_bound = 0
    vo_bound = 0
    do_bound = 0
    cov_all = {"bound": 0, "total": 0}
    cov_by_origin = {
        "matched": {"bound": 0, "total": 0},
        "vision_only": {"bound": 0, "total": 0},
        "deterministic_only": {"bound": 0, "total": 0},
        "all": {"bound": 0, "total": 0},
    }
    ref_hits = Counter()
    ref_tot = Counter()
    failure_reasons = Counter()
    all_groups: List[Dict[str, Any]] = []
    for beam in bound_beams:
        compat = beam.get("compatibility") or {}
        beam_status[compat.get("overall_status") or BEAM_INCOMPATIBLE] += 1
        for g in beam.get("groups") or []:
            all_groups.append(g)
            st = (g.get("engineering_binding") or {}).get("binding_status")
            group_status[st] += 1
            bucket = _origin_bucket(g)
            origins[bucket] += 1
            if g.get("possible_duplicate"):
                dup_preserved += 1
            if g.get("ambiguous"):
                amb_unresolved += 1
            if st == STATUS_BOUND:
                if bucket == "matched":
                    matched_bound += 1
                elif bucket == "vision_only":
                    vo_bound += 1
                elif bucket == "deterministic_only":
                    do_bound += 1
            cov = group_coverage(g)
            cov_all["bound"] += cov["bound"]
            cov_all["total"] += cov["total"]
            cov_by_origin["all"]["bound"] += cov["bound"]
            cov_by_origin["all"]["total"] += cov["total"]
            if bucket in cov_by_origin:
                cov_by_origin[bucket]["bound"] += cov["bound"]
                cov_by_origin[bucket]["total"] += cov["total"]
            bind = g.get("engineering_binding") or {}
            for k in REQUIRED_KEYS:
                ref_tot[k] += 1
                if _ref_bound(bind, k):
                    ref_hits[k] += 1
            st = (g.get("engineering_binding") or {}).get("binding_status")
            if st and st not in (STATUS_BOUND,):
                failure_reasons[str(st)] += 1
            for r in bind.get("binding_reasons") or []:
                if r in (
                    STATUS_MISSING_GEOM,
                    STATUS_MISSING_SUPPORT,
                    STATUS_MISSING_RULE,
                    STATUS_AMBIGUOUS,
                    STATUS_UNSUPPORTED,
                    STATUS_INVALID,
                    "AMBIGUOUS_SUPPORT_REFERENCE",
                    "VISION_ONLY_RULE_FAMILY_BOUND_INSTANCE_UNAVAILABLE",
                ):
                    failure_reasons[str(r)] += 1

    def _ratio(part: Dict[str, int]) -> float:
        return round(part["bound"] / part["total"], 4) if part["total"] else 0.0

    coverage = {
        "label": "ENGINEERING_BINDING_COVERAGE",
        "note": "COMPATIBILITY COVERAGE, NOT ACCURACY. Not estimator truth. Not production promotion.",
        "formula": "fully_bound_required_references / total_required_references",
        "all_groups": _ratio(cov_by_origin["all"]),
        "matched_groups": _ratio(cov_by_origin["matched"]),
        "vision_only_groups": _ratio(cov_by_origin["vision_only"]),
        "deterministic_only_groups": _ratio(cov_by_origin["deterministic_only"]),
        "counts": cov_by_origin,
        "engineering_reference_coverage": {
            "geometry": round(ref_hits["beam_geometry_reference"] / ref_tot["beam_geometry_reference"], 4) if ref_tot["beam_geometry_reference"] else 0.0,
            "section_geometry": round(ref_hits["section_geometry_reference"] / ref_tot["section_geometry_reference"], 4) if ref_tot["section_geometry_reference"] else 0.0,
            "direction": round(ref_hits["longitudinal_direction"] / ref_tot["longitudinal_direction"], 4) if ref_tot["longitudinal_direction"] else 0.0,
            "support": round(ref_hits["support_reference"] / ref_tot["support_reference"], 4) if ref_tot["support_reference"] else 0.0,
            "cut_length_rule": round(ref_hits["cut_length_rule_reference"] / ref_tot["cut_length_rule_reference"], 4) if ref_tot["cut_length_rule_reference"] else 0.0,
            "development_length_rule": round(ref_hits["development_length_reference"] / ref_tot["development_length_reference"], 4) if ref_tot["development_length_reference"] else 0.0,
            "anchorage": round(ref_hits["anchorage_reference"] / ref_tot["anchorage_reference"], 4) if ref_tot["anchorage_reference"] else 0.0,
            "hook_bend": round(ref_hits["hook_bend_reference"] / ref_tot["hook_bend_reference"], 4) if ref_tot["hook_bend_reference"] else 0.0,
        },
    }
    return {
        "benchmark_population_count": len(bound_beams),
        "beam_compatibility": {
            BEAM_COMPATIBLE: beam_status[BEAM_COMPATIBLE],
            BEAM_PARTIAL: beam_status[BEAM_PARTIAL],
            BEAM_AMBIGUOUS: beam_status[BEAM_AMBIGUOUS],
            BEAM_INCOMPATIBLE: beam_status[BEAM_INCOMPATIBLE],
        },
        "group_binding": {
            "total": len(all_groups),
            STATUS_BOUND: group_status[STATUS_BOUND],
            STATUS_PARTIAL: group_status[STATUS_PARTIAL],
            STATUS_AMBIGUOUS: group_status[STATUS_AMBIGUOUS],
            STATUS_MISSING_GEOM: group_status[STATUS_MISSING_GEOM],
            STATUS_MISSING_SUPPORT: group_status[STATUS_MISSING_SUPPORT],
            STATUS_MISSING_RULE: group_status[STATUS_MISSING_RULE],
            STATUS_UNSUPPORTED: group_status[STATUS_UNSUPPORTED],
            STATUS_INVALID: group_status[STATUS_INVALID],
        },
        "source_categories": {
            "matched_groups": origins["matched"],
            "matched_groups_bound": matched_bound,
            "vision_only_groups": origins["vision_only"],
            "vision_only_groups_bound": vo_bound,
            "deterministic_only_groups": origins["deterministic_only"],
            "deterministic_only_groups_bound": do_bound,
            "ambiguous_groups_unresolved": amb_unresolved,
            "possible_duplicates_preserved": dup_preserved,
        },
        "coverage": coverage,
        "top_unresolved_categories": failure_reasons.most_common(12),
        "calculations_performed": {
            "cut_length": False,
            "development_length": False,
            "steel_weight": False,
            "bbs": False,
        },
    }


__all__ = ["REQUIRED_KEYS", "build_diagnostics", "group_coverage"]
