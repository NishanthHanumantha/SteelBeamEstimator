"""Calculation dependency type constants — Phase I.4.6."""

from __future__ import annotations

from typing import Dict, FrozenSet, List, TypedDict

PREFIX_DEPENDENCY_GRAPH = "CALC_DEPENDENCY"
PREFIX_DEPENDENCY_REGISTRY = "CALC_DEPENDENCY_REGISTRY"
NAMESPACE_CALCULATION_DEPENDENCY = "CALCULATION_DEPENDENCY"

CREATED_PHASE = "I.4.6"
PHASE_LABEL = "Phase I.4.6"

CATEGORY_DEVELOPMENT_LENGTH = "DEVELOPMENT_LENGTH"
CATEGORY_HOOK_LENGTH = "HOOK_LENGTH"
CATEGORY_LAP_LENGTH = "LAP_LENGTH"
CATEGORY_CUT_LENGTH = "CUT_LENGTH"
CATEGORY_SHAPE_CODE = "SHAPE_CODE"
CATEGORY_BAR_IDENTITY = "BAR_IDENTITY"
CATEGORY_BAR_GROUP = "BAR_GROUP"
CATEGORY_BBS = "BBS"
CATEGORY_STEEL_WEIGHT = "STEEL_WEIGHT"
CATEGORY_BEAM_SUMMARY = "BEAM_SUMMARY"
CATEGORY_QUANTITY = "QUANTITY"
CATEGORY_MATERIAL = "MATERIAL"
CATEGORY_BEAM_SCHEDULE = "BEAM_SCHEDULE"
CATEGORY_ENGINEERING_REPORT = "ENGINEERING_REPORT"
CATEGORY_EXCEL_EXPORT = "EXCEL_EXPORT"


class DependencyNodeSpec(TypedDict):
    sequence: int
    depends_on: List[str]
    calculation_type: str
    index_category: str


DEPENDENCY_NODE_SPECS: Dict[str, DependencyNodeSpec] = {
    CATEGORY_DEVELOPMENT_LENGTH: {
        "sequence": 1,
        "depends_on": [],
        "calculation_type": "DEVELOPMENT_LENGTH",
        "index_category": CATEGORY_DEVELOPMENT_LENGTH,
    },
    CATEGORY_HOOK_LENGTH: {
        "sequence": 2,
        "depends_on": [],
        "calculation_type": "HOOK",
        "index_category": CATEGORY_HOOK_LENGTH,
    },
    CATEGORY_LAP_LENGTH: {
        "sequence": 3,
        "depends_on": [CATEGORY_DEVELOPMENT_LENGTH],
        "calculation_type": "LAP_LENGTH",
        "index_category": CATEGORY_LAP_LENGTH,
    },
    CATEGORY_CUT_LENGTH: {
        "sequence": 4,
        "depends_on": [
            CATEGORY_DEVELOPMENT_LENGTH,
            CATEGORY_HOOK_LENGTH,
            CATEGORY_LAP_LENGTH,
        ],
        "calculation_type": "CUT_LENGTH",
        "index_category": CATEGORY_CUT_LENGTH,
    },
    CATEGORY_SHAPE_CODE: {
        "sequence": 5,
        "depends_on": [CATEGORY_CUT_LENGTH],
        "calculation_type": "UNKNOWN",
        "index_category": CATEGORY_SHAPE_CODE,
    },
    CATEGORY_BAR_IDENTITY: {
        "sequence": 6,
        "depends_on": [
            CATEGORY_CUT_LENGTH,
            CATEGORY_SHAPE_CODE,
            CATEGORY_HOOK_LENGTH,
            CATEGORY_DEVELOPMENT_LENGTH,
            CATEGORY_LAP_LENGTH,
        ],
        "calculation_type": "BAR_IDENTITY",
        "index_category": CATEGORY_BAR_IDENTITY,
    },
    CATEGORY_BAR_GROUP: {
        "sequence": 7,
        "depends_on": [CATEGORY_BAR_IDENTITY],
        "calculation_type": "BAR_GROUP",
        "index_category": CATEGORY_BAR_GROUP,
    },
    CATEGORY_BBS: {
        "sequence": 8,
        "depends_on": [CATEGORY_BAR_GROUP],
        "calculation_type": "BBS",
        "index_category": CATEGORY_BBS,
    },
    CATEGORY_STEEL_WEIGHT: {
        "sequence": 9,
        "depends_on": [CATEGORY_BBS],
        "calculation_type": "STEEL_WEIGHT",
        "index_category": CATEGORY_STEEL_WEIGHT,
    },
    CATEGORY_BEAM_SUMMARY: {
        "sequence": 10,
        "depends_on": [CATEGORY_STEEL_WEIGHT],
        "calculation_type": "UNKNOWN",
        "index_category": CATEGORY_BEAM_SUMMARY,
    },
    CATEGORY_QUANTITY: {
        "sequence": 11,
        "depends_on": [CATEGORY_BEAM_SUMMARY],
        "calculation_type": "QUANTITY",
        "index_category": CATEGORY_QUANTITY,
    },
    CATEGORY_MATERIAL: {
        "sequence": 12,
        "depends_on": [CATEGORY_QUANTITY],
        "calculation_type": "MATERIAL",
        "index_category": CATEGORY_MATERIAL,
    },
    CATEGORY_BEAM_SCHEDULE: {
        "sequence": 13,
        "depends_on": [CATEGORY_MATERIAL],
        "calculation_type": "BEAM_SCHEDULE",
        "index_category": CATEGORY_BEAM_SCHEDULE,
    },
    CATEGORY_ENGINEERING_REPORT: {
        "sequence": 14,
        "depends_on": [CATEGORY_BEAM_SCHEDULE],
        "calculation_type": "ENGINEERING_REPORT",
        "index_category": CATEGORY_ENGINEERING_REPORT,
    },
    CATEGORY_EXCEL_EXPORT: {
        "sequence": 15,
        "depends_on": [CATEGORY_ENGINEERING_REPORT],
        "calculation_type": "EXCEL_EXPORT",
        "index_category": CATEGORY_EXCEL_EXPORT,
    },
}

ALL_DEPENDENCY_CATEGORIES: FrozenSet[str] = frozenset(DEPENDENCY_NODE_SPECS.keys())

CALCULATION_TYPE_TO_DEPENDENCY_CATEGORY: Dict[str, str] = {
    spec["calculation_type"]: category
    for category, spec in DEPENDENCY_NODE_SPECS.items()
    if spec["calculation_type"] != "UNKNOWN"
}

INDEX_CATEGORY_TO_DEPENDENCY_CATEGORY: Dict[str, str] = {
    spec["index_category"]: category
    for category, spec in DEPENDENCY_NODE_SPECS.items()
}
