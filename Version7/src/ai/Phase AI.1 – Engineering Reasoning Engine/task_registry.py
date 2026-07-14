"""Task registry for engineering reasoning capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from reasoning_models import RESULT_MODEL_MAP


@dataclass(frozen=True)
class ReasoningTaskDefinition:
    task_type: str
    prompt_template: str
    schema_name: str
    context_task_type: str
    priority: str
    result_model: str
    template_version: str
    required_context: Tuple[str, ...]
    description: str


TASK_REGISTRY: Dict[str, ReasoningTaskDefinition] = {
    "BEAM_REASONING": ReasoningTaskDefinition(
        task_type="BEAM_REASONING",
        prompt_template="BEAM_REASONING",
        schema_name="BEAM_REASONING",
        context_task_type="BEAM_REASONING",
        priority="Critical",
        result_model="BeamReasoningResult",
        template_version="1.0",
        required_context=("beams", "calculation_context"),
        description="Beam-level engineering reasoning.",
    ),
    "ANNOTATION_CLASSIFICATION": ReasoningTaskDefinition(
        task_type="ANNOTATION_CLASSIFICATION",
        prompt_template="ANNOTATION_INTERPRETER",
        schema_name="ANNOTATION_INTERPRETER",
        context_task_type="ANNOTATION_INTERPRETER",
        priority="High",
        result_model="AnnotationReasoningResult",
        template_version="1.0",
        required_context=("geometry", "beams"),
        description="Drawing annotation classification and interpretation.",
    ),
    "REINFORCEMENT_INTERPRETATION": ReasoningTaskDefinition(
        task_type="REINFORCEMENT_INTERPRETATION",
        prompt_template="REINFORCEMENT_PARSER",
        schema_name="REINFORCEMENT_PARSER",
        context_task_type="REINFORCEMENT_PARSER",
        priority="High",
        result_model="ReinforcementReasoningResult",
        template_version="1.0",
        required_context=("reinforcement", "beams"),
        description="Reinforcement annotation interpretation.",
    ),
    "QA_REASONING": ReasoningTaskDefinition(
        task_type="QA_REASONING",
        prompt_template="QA_VALIDATOR",
        schema_name="QA_VALIDATOR",
        context_task_type="QA_VALIDATOR",
        priority="High",
        result_model="QAReasoningResult",
        template_version="1.0",
        required_context=("beam_schedule", "calculation_context"),
        description="QA reasoning over engineering artifacts.",
    ),
    "GENERAL_ENGINEERING_REASONING": ReasoningTaskDefinition(
        task_type="GENERAL_ENGINEERING_REASONING",
        prompt_template="BEAM_REASONING",
        schema_name="BASE_RESPONSE",
        context_task_type="GENERAL_ENGINEERING",
        priority="Medium",
        result_model="EngineeringReasoningResult",
        template_version="1.0",
        required_context=("beams", "general_notes"),
        description="General cross-domain engineering reasoning.",
    ),
}


class TaskRegistry:
    """Resolve reasoning task definitions."""

    @staticmethod
    def get(task_type: str) -> ReasoningTaskDefinition:
        key = task_type.upper()
        definition = TASK_REGISTRY.get(key)
        if definition is None:
            raise KeyError(f"Unsupported reasoning task type: {task_type}")
        return definition

    @staticmethod
    def all_task_types() -> List[str]:
        return sorted(TASK_REGISTRY.keys())

    @staticmethod
    def result_model_for(task_type: str) -> str:
        definition = TaskRegistry.get(task_type)
        if definition.result_model not in RESULT_MODEL_MAP:
            raise KeyError(f"Result model not mapped: {definition.result_model}")
        return definition.result_model
