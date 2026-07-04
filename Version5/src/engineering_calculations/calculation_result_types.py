"""Engineering calculation result type constants — Phase I.2.2."""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet

PREFIX_CALCULATION_RESULT = "CALC_RESULT"
PREFIX_CALCULATION_RESULT_REGISTRY = "CALC_RESULT_REGISTRY"
NAMESPACE_CALCULATION_RESULT = "CALCULATION_RESULT"

CREATED_PHASE = "I.2.2"
FRAMEWORK_ENGINE_NAME = "CALCULATION_RESULT_FRAMEWORK"
SOURCE_ENGINE_VERSION = "I.2.2"
RESULT_STATUS_FRAMEWORK_INITIALIZED = "FRAMEWORK_INITIALIZED"


class CalculationResultState(str, Enum):
    """Result lifecycle state for engineering calculation outputs."""

    UNKNOWN = "UNKNOWN"
    READY = "READY"
    CALCULATED = "CALCULATED"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class CalculationType(str, Enum):
    """Supported engineering calculation categories."""

    DEVELOPMENT_LENGTH = "DEVELOPMENT_LENGTH"
    HOOK = "HOOK"
    BEND = "BEND"
    LAP_LENGTH = "LAP_LENGTH"
    CURTAILMENT = "CURTAILMENT"
    CUT_LENGTH = "CUT_LENGTH"
    SHAPE_CODE = "SHAPE_CODE"
    BAR_IDENTITY = "BAR_IDENTITY"
    BAR_GROUP = "BAR_GROUP"
    BBS = "BBS"
    BAR_SCHEDULE = "BAR_SCHEDULE"
    STEEL_WEIGHT = "STEEL_WEIGHT"
    BOQ = "BOQ"
    UNKNOWN = "UNKNOWN"


VALID_RESULT_STATES: FrozenSet[str] = frozenset(item.value for item in CalculationResultState)
VALID_CALCULATION_TYPES: FrozenSet[str] = frozenset(item.value for item in CalculationType)

FRAMEWORK_CALCULATION_TYPES: FrozenSet[CalculationType] = frozenset({
    CalculationType.DEVELOPMENT_LENGTH,
    CalculationType.HOOK,
    CalculationType.BEND,
    CalculationType.LAP_LENGTH,
    CalculationType.CURTAILMENT,
    CalculationType.CUT_LENGTH,
    CalculationType.BAR_SCHEDULE,
    CalculationType.STEEL_WEIGHT,
    CalculationType.BOQ,
})

REGISTRY_SCHEMA_KEYS: FrozenSet[str] = frozenset({
    "namespace",
    "phase",
    "registry_id",
    "result_count",
    "result_ids",
    "bar_count",
    "results_by_state",
    "results_by_calculation_type",
})


def parse_calculation_result_state(value: str | None) -> CalculationResultState:
    if not value:
        return CalculationResultState.UNKNOWN
    try:
        return CalculationResultState(str(value))
    except ValueError:
        return CalculationResultState.UNKNOWN


def parse_calculation_type(value: str | None) -> CalculationType:
    if not value:
        return CalculationType.UNKNOWN
    try:
        return CalculationType(str(value))
    except ValueError:
        return CalculationType.UNKNOWN
