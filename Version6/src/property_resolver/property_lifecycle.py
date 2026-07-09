"""Engineering property lifecycle definitions — Phase G.5.3.4."""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

from src.property_parser.property_parser_types import (
    PROP_BAR_LENGTH,
    PROP_BAR_MARK,
    PROP_BAR_TYPE,
    PROP_BLOCK,
    PROP_CALLOUT,
    PROP_CUT_LENGTH,
    PROP_DIAMETER,
    PROP_END_OFFSET,
    PROP_HOOK,
    PROP_HOOK_DIRECTION,
    PROP_LEADER,
    PROP_LEVEL,
    PROP_NOTE,
    PROP_QUANTITY,
    PROP_REINFORCEMENT_CODE,
    PROP_SHAPE_CODE,
    PROP_SPACING,
    PROP_START_OFFSET,
    PROP_TEXT,
    PROP_UNKNOWN,
    PROP_ZONE,
)


class EngineeringPropertyLifecycle(str, Enum):
    TEXT_DERIVED = "TEXT_DERIVED"
    GEOMETRY_DERIVED = "GEOMETRY_DERIVED"
    SHAPE_DERIVED = "SHAPE_DERIVED"
    CALCULATED = "CALCULATED"
    BOQ_DERIVED = "BOQ_DERIVED"
    SYSTEM = "SYSTEM"
    UNKNOWN = "UNKNOWN"


class PipelineAvailabilityStage(str, Enum):
    PHASE_G = "PHASE_G"
    PHASE_H = "PHASE_H"
    PHASE_I = "PHASE_I"
    PHASE_J = "PHASE_J"


LIFECYCLE_AVAILABLE_FROM: Dict[EngineeringPropertyLifecycle, PipelineAvailabilityStage] = {
    EngineeringPropertyLifecycle.TEXT_DERIVED: PipelineAvailabilityStage.PHASE_G,
    EngineeringPropertyLifecycle.GEOMETRY_DERIVED: PipelineAvailabilityStage.PHASE_H,
    EngineeringPropertyLifecycle.SHAPE_DERIVED: PipelineAvailabilityStage.PHASE_I,
    EngineeringPropertyLifecycle.CALCULATED: PipelineAvailabilityStage.PHASE_I,
    EngineeringPropertyLifecycle.BOQ_DERIVED: PipelineAvailabilityStage.PHASE_J,
    EngineeringPropertyLifecycle.SYSTEM: PipelineAvailabilityStage.PHASE_G,
    EngineeringPropertyLifecycle.UNKNOWN: PipelineAvailabilityStage.PHASE_G,
}

PHASE_ORDER: Dict[str, int] = {
    PipelineAvailabilityStage.PHASE_G.value: 0,
    PipelineAvailabilityStage.PHASE_H.value: 1,
    PipelineAvailabilityStage.PHASE_I.value: 2,
    PipelineAvailabilityStage.PHASE_J.value: 3,
}

LIFECYCLE_DEFER_REASON: Dict[EngineeringPropertyLifecycle, str] = {
    EngineeringPropertyLifecycle.GEOMETRY_DERIVED: "Requires beam geometry.",
    EngineeringPropertyLifecycle.SHAPE_DERIVED: "Requires bar shape interpretation.",
    EngineeringPropertyLifecycle.CALCULATED: "Requires engineering calculations.",
    EngineeringPropertyLifecycle.BOQ_DERIVED: "Requires BOQ aggregation.",
}

PROPERTY_TYPE_LIFECYCLE: Dict[str, EngineeringPropertyLifecycle] = {
    PROP_BAR_TYPE: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_DIAMETER: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_QUANTITY: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_REINFORCEMENT_CODE: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_TEXT: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_BAR_MARK: EngineeringPropertyLifecycle.TEXT_DERIVED,
    "MARK": EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_LEVEL: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_LEADER: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_BLOCK: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_NOTE: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_CALLOUT: EngineeringPropertyLifecycle.TEXT_DERIVED,
    PROP_ZONE: EngineeringPropertyLifecycle.SYSTEM,
    PROP_BAR_LENGTH: EngineeringPropertyLifecycle.GEOMETRY_DERIVED,
    PROP_CUT_LENGTH: EngineeringPropertyLifecycle.GEOMETRY_DERIVED,
    PROP_START_OFFSET: EngineeringPropertyLifecycle.GEOMETRY_DERIVED,
    PROP_END_OFFSET: EngineeringPropertyLifecycle.GEOMETRY_DERIVED,
    "BAR_LOCATION": EngineeringPropertyLifecycle.GEOMETRY_DERIVED,
    PROP_SPACING: EngineeringPropertyLifecycle.GEOMETRY_DERIVED,
    PROP_HOOK: EngineeringPropertyLifecycle.SHAPE_DERIVED,
    PROP_HOOK_DIRECTION: EngineeringPropertyLifecycle.SHAPE_DERIVED,
    "BEND": EngineeringPropertyLifecycle.SHAPE_DERIVED,
    PROP_SHAPE_CODE: EngineeringPropertyLifecycle.SHAPE_DERIVED,
    "SKETCH": EngineeringPropertyLifecycle.SHAPE_DERIVED,
    PROP_UNKNOWN: EngineeringPropertyLifecycle.UNKNOWN,
}

VALID_LIFECYCLES: FrozenSet[str] = frozenset(item.value for item in EngineeringPropertyLifecycle)
