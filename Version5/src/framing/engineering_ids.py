"""Global engineering ID namespace utilities."""

from __future__ import annotations

import re
from typing import Optional


NS_SEPARATOR = "::"

RULE_PROJECT = "RULE::PROJECT"
RULE_ESTIMATOR = "RULE::ESTIMATOR"
GENERAL_NOTES_ID = "KNOWLEDGE::GENERAL_NOTES"
GENERAL_NOTES_DOC_ID = "GN-001"
KNOWLEDGE_PROJECT_DEFAULTS = "KNOWLEDGE::PROJECT_DEFAULTS"
SERVICES_ID = "ENGINEERING_SERVICES"
DEFAULT_PROJECT_SLUG = "SOBHA_GALERA"
DEFAULT_FLOOR_SLUG = "GROUND_FLOOR"


def floor_id(slug: str = DEFAULT_FLOOR_SLUG) -> str:
    return f"FLOOR::{slug}"


def floor_slug_from_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip().upper())
    return cleaned.strip("_") or DEFAULT_FLOOR_SLUG


def project_id(slug: str = DEFAULT_PROJECT_SLUG) -> str:
    return f"PROJECT::{slug}"


def beam_id(mark: str) -> str:
    return f"BEAM::{mark}"


def section_id(mark: str) -> str:
    return f"SECTION::{mark}"


def length_id(mark: str) -> str:
    return f"LENGTH::{mark}"


def ecs_id(mark: str) -> str:
    return f"ECS::{mark}"


def context_id(mark: str) -> str:
    return f"CTX::{mark}"


def support_beam_id(mark: str) -> str:
    return f"SUPPORT::{mark}"


def column_id(index_or_id: str) -> str:
    raw = str(index_or_id).replace("COLUMN_", "").replace("COLUMN::", "")
    return f"COLUMN::{raw}"


def wall_id(index_or_id: str) -> str:
    raw = str(index_or_id).replace("WALL_", "").replace("WALL::", "")
    return f"WALL::{raw}"


def support_structural_id(support_type: str, support_id: Optional[str]) -> Optional[str]:
    if not support_id:
        return None
    st = str(support_type).upper()
    sid = str(support_id)
    if sid.startswith("BEAM::") or sid.startswith("COLUMN::") or sid.startswith("WALL::"):
        return sid
    if st == "BEAM" and sid.startswith("B"):
        return beam_id(sid)
    if st == "COLUMN" and sid.startswith("COLUMN_"):
        return column_id(sid)
    if st == "WALL" and sid.startswith("WALL_"):
        return wall_id(sid)
    if st == "COLUMN":
        return column_id(sid)
    if st == "WALL":
        return wall_id(sid)
    return f"SUPPORT::{st}::{sid}"


def legacy_section_id(mark: str) -> str:
    return f"SECTION_{mark}"


def legacy_length_id(mark: str) -> str:
    return f"LM_{mark}"


def legacy_ecs_id(mark: str) -> str:
    return f"ECS_{mark}"


def legacy_project_rules_id() -> str:
    return "PROJECT_RULES"


def slug_from_project_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip().upper())
    return cleaned.strip("_") or DEFAULT_PROJECT_SLUG


def to_namespaced(legacy_id: str, beam_mark: Optional[str] = None) -> str:
    """Convert legacy graph IDs to namespaced authoritative IDs."""
    lid = str(legacy_id)
    if NS_SEPARATOR in lid:
        return lid
    if lid == "PROJECT_RULES":
        return RULE_PROJECT
    if lid.startswith("SECTION_"):
        return section_id(lid.replace("SECTION_", ""))
    if lid.startswith("LM_"):
        return length_id(lid.replace("LM_", ""))
    if lid.startswith("ECS_"):
        return ecs_id(lid.replace("ECS_", ""))
    if lid.startswith("COLUMN_"):
        return column_id(lid)
    if lid.startswith("WALL_"):
        return wall_id(lid)
    if lid.startswith("B") and lid[1:].isdigit():
        return beam_id(lid)
    if beam_mark and lid == beam_mark:
        return beam_id(lid)
    return lid


def alias_map_for_beam(mark: str) -> dict[str, str]:
    return {
        "beam_id": beam_id(mark),
        "section_id": section_id(mark),
        "length_id": length_id(mark),
        "ecs_id": ecs_id(mark),
        "context_id": context_id(mark),
        "legacy_section_id": legacy_section_id(mark),
        "legacy_length_id": legacy_length_id(mark),
        "legacy_ecs_id": legacy_ecs_id(mark),
        "legacy_beam_id": mark,
    }
