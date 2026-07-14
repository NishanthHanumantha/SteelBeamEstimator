"""Registry of version-controlled prompt templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from src.llm.prompts.prompt_models import TemplateNotFoundError

PHASE = "Phase LLM.1.1"
MODEL_VERSION = "6.1.1"

PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "prompts"


@dataclass(frozen=True)
class RegistryEntry:
    """Maps a logical template name to a repository path."""

    template_name: str
    relative_path: str
    version: str
    description: str

    @property
    def absolute_path(self) -> Path:
        return PROMPTS_ROOT / self.relative_path


PROMPT_REGISTRY: Dict[str, RegistryEntry] = {
    "ENGINEERING_SYSTEM": RegistryEntry(
        template_name="ENGINEERING_SYSTEM",
        relative_path="system/engineering_system.md",
        version="1.0",
        description="System instructions for engineering reasoning tasks.",
    ),
    "ENGINEERING_RULES": RegistryEntry(
        template_name="ENGINEERING_RULES",
        relative_path="system/engineering_rules.md",
        version="1.0",
        description="Global engineering rule context for AI modules.",
    ),
    "BEAM_REASONING": RegistryEntry(
        template_name="BEAM_REASONING",
        relative_path="engineering/beam_reasoning.md",
        version="1.0",
        description="Beam-level engineering reasoning template.",
    ),
    "REINFORCEMENT_PARSER": RegistryEntry(
        template_name="REINFORCEMENT_PARSER",
        relative_path="engineering/reinforcement_parser.md",
        version="1.0",
        description="Reinforcement annotation parsing template.",
    ),
    "ANNOTATION_INTERPRETER": RegistryEntry(
        template_name="ANNOTATION_INTERPRETER",
        relative_path="engineering/annotation_interpreter.md",
        version="1.0",
        description="Drawing annotation interpretation template.",
    ),
    "QA_VALIDATOR": RegistryEntry(
        template_name="QA_VALIDATOR",
        relative_path="engineering/qa_validator.md",
        version="1.0",
        description="QA validation prompt template.",
    ),
    "JSON_RESPONSE_RULES": RegistryEntry(
        template_name="JSON_RESPONSE_RULES",
        relative_path="shared/json_response_rules.md",
        version="1.0",
        description="Shared JSON response formatting rules.",
    ),
    "OUTPUT_CONSTRAINTS": RegistryEntry(
        template_name="OUTPUT_CONSTRAINTS",
        relative_path="shared/output_constraints.md",
        version="1.0",
        description="Shared output constraint rules.",
    ),
    "SAMPLE_PROMPT": RegistryEntry(
        template_name="SAMPLE_PROMPT",
        relative_path="examples/sample_prompt.md",
        version="1.0",
        description="Example template for integration testing.",
    ),
}


class PromptRegistry:
    """Resolve template names to repository entries."""

    @staticmethod
    def get(template_name: str) -> RegistryEntry:
        key = template_name.upper()
        entry = PROMPT_REGISTRY.get(key)
        if entry is None:
            raise TemplateNotFoundError(f"Template not registered: {template_name}")
        if not entry.absolute_path.exists():
            raise TemplateNotFoundError(f"Template file missing: {entry.absolute_path}")
        return entry

    @staticmethod
    def all_entries() -> Dict[str, RegistryEntry]:
        return dict(PROMPT_REGISTRY)
