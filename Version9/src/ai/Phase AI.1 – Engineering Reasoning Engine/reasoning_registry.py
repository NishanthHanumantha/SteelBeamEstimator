"""Registry of engineering reasoning capabilities."""

from __future__ import annotations

from typing import Dict, List

from reasoning_models import MODEL_VERSION, PHASE, RESULT_MODEL_MAP
from task_registry import TASK_REGISTRY, ReasoningTaskDefinition, TaskRegistry

__all__ = [
    "MODEL_VERSION",
    "PHASE",
    "RESULT_MODEL_MAP",
    "TASK_REGISTRY",
    "ReasoningRegistry",
    "ReasoningTaskDefinition",
    "TaskRegistry",
]


class ReasoningRegistry:
    """Expose registered reasoning tasks and result models."""

    @staticmethod
    def all_tasks() -> List[ReasoningTaskDefinition]:
        return [TASK_REGISTRY[key] for key in sorted(TASK_REGISTRY.keys())]

    @staticmethod
    def get(task_type: str) -> ReasoningTaskDefinition:
        return TaskRegistry.get(task_type)

    @staticmethod
    def registered_sections(task_type: str) -> List[str]:
        return list(TaskRegistry.get(task_type).required_context)

    @staticmethod
    def result_models() -> Dict[str, str]:
        return {
            task_type: TASK_REGISTRY[task_type].result_model
            for task_type in sorted(TASK_REGISTRY.keys())
        }
