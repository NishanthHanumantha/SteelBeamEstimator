"""Registry of task-aware engineering context definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

PHASE = "Phase LLM.3"
MODEL_VERSION = "6.3.0"
DEFAULT_TOKEN_BUDGET = 6000


@dataclass(frozen=True)
class SectionDefinition:
    section_name: str
    priority: str
    required_objects: Tuple[str, ...]


@dataclass(frozen=True)
class TaskContextDefinition:
    task_type: str
    sections: Tuple[SectionDefinition, ...]
    token_budget: int
    description: str


PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


TASK_REGISTRY: Dict[str, TaskContextDefinition] = {
    "BEAM_REASONING": TaskContextDefinition(
        task_type="BEAM_REASONING",
        description="Beam reasoning context package.",
        token_budget=DEFAULT_TOKEN_BUDGET,
        sections=(
            SectionDefinition("beam", "Critical", ("beams",)),
            SectionDefinition("calculation_context", "Critical", ("calculation_context",)),
            SectionDefinition("reinforcement", "High", ("reinforcement",)),
            SectionDefinition("general_notes", "High", ("general_notes",)),
            SectionDefinition("geometry", "Medium", ("geometry",)),
            SectionDefinition("supports", "Medium", ("supports",)),
            SectionDefinition("dimensions", "Medium", ("dimensions",)),
            SectionDefinition("material_properties", "Low", ("material_properties",)),
            SectionDefinition("engineering_graph", "Low", ("engineering_graph",)),
        ),
    ),
    "REINFORCEMENT_PARSER": TaskContextDefinition(
        task_type="REINFORCEMENT_PARSER",
        description="Reinforcement parser context package.",
        token_budget=DEFAULT_TOKEN_BUDGET,
        sections=(
            SectionDefinition("reinforcement", "Critical", ("reinforcement",)),
            SectionDefinition("beam", "High", ("beams",)),
            SectionDefinition("general_notes", "High", ("general_notes",)),
            SectionDefinition("calculation_context", "Medium", ("calculation_context",)),
            SectionDefinition("geometry", "Medium", ("geometry",)),
        ),
    ),
    "ANNOTATION_INTERPRETER": TaskContextDefinition(
        task_type="ANNOTATION_INTERPRETER",
        description="Annotation interpreter context package.",
        token_budget=DEFAULT_TOKEN_BUDGET,
        sections=(
            SectionDefinition("geometry", "Critical", ("geometry",)),
            SectionDefinition("beam", "High", ("beams",)),
            SectionDefinition("reinforcement", "High", ("reinforcement",)),
            SectionDefinition("general_notes", "Medium", ("general_notes",)),
        ),
    ),
    "QA_VALIDATOR": TaskContextDefinition(
        task_type="QA_VALIDATOR",
        description="QA validator context package.",
        token_budget=DEFAULT_TOKEN_BUDGET,
        sections=(
            SectionDefinition("beam_schedule", "Critical", ("beam_schedule",)),
            SectionDefinition("reinforcement", "High", ("reinforcement",)),
            SectionDefinition("calculation_context", "High", ("calculation_context",)),
            SectionDefinition("general_notes", "Medium", ("general_notes",)),
            SectionDefinition("engineering_graph", "Low", ("engineering_graph",)),
        ),
    ),
    "GENERAL_ENGINEERING": TaskContextDefinition(
        task_type="GENERAL_ENGINEERING",
        description="General engineering context package.",
        token_budget=DEFAULT_TOKEN_BUDGET,
        sections=(
            SectionDefinition("beam", "High", ("beams",)),
            SectionDefinition("reinforcement", "High", ("reinforcement",)),
            SectionDefinition("general_notes", "High", ("general_notes",)),
            SectionDefinition("calculation_context", "Medium", ("calculation_context",)),
            SectionDefinition("geometry", "Medium", ("geometry",)),
            SectionDefinition("supports", "Medium", ("supports",)),
            SectionDefinition("dimensions", "Medium", ("dimensions",)),
            SectionDefinition("material_properties", "Low", ("material_properties",)),
            SectionDefinition("engineering_graph", "Low", ("engineering_graph",)),
            SectionDefinition("beam_schedule", "Low", ("beam_schedule",)),
        ),
    ),
}


class ContextRegistry:
    """Resolve task-aware context definitions."""

    @staticmethod
    def get(task_type: str) -> TaskContextDefinition:
        key = task_type.upper()
        definition = TASK_REGISTRY.get(key)
        if definition is None:
            raise KeyError(f"Unsupported context task type: {task_type}")
        return definition

    @staticmethod
    def all_task_types() -> List[str]:
        return sorted(TASK_REGISTRY.keys())
