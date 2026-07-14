"""Prompt helper definitions for engineering reasoning tasks."""

from __future__ import annotations

REASONING_CONSTRAINTS = (
    "Engineering reasoning constraints:\n"
    "- Never calculate quantities.\n"
    "- Never calculate reinforcement.\n"
    "- Never modify engineering objects.\n"
    "- Never modify engineering calculations or rules.\n"
    "- Never replace deterministic engineering algorithms.\n"
    "- Explain, interpret, classify, summarize, and detect ambiguity only.\n"
    "- Provide confidence-backed recommendations.\n"
    "- Respect the deterministic engineering pipeline as the single source of truth.\n"
    "- Return valid JSON only with no markdown fences or commentary."
)

TASK_PROMPT_GUIDANCE = {
    "BEAM_REASONING": (
        "Analyze the supplied beam engineering context and explain engineering reasoning only. "
        "Do not modify quantities or calculations."
    ),
    "ANNOTATION_CLASSIFICATION": (
        "Interpret drawing annotations using supplied geometry and reinforcement context. "
        "Classify and explain only; do not infer missing engineering data."
    ),
    "REINFORCEMENT_INTERPRETATION": (
        "Interpret reinforcement annotations using supplied context. "
        "Explain parsed meaning only; do not calculate bar quantities."
    ),
    "QA_REASONING": (
        "Review supplied engineering artifacts for QA reasoning. "
        "Identify issues and explain validation reasoning only."
    ),
    "GENERAL_ENGINEERING_REASONING": (
        "Provide general engineering reasoning across supplied context sections. "
        "Summarize and explain only; do not modify deterministic outputs."
    ),
}


def build_reasoning_variables(task_type: str) -> dict[str, str]:
    """Return deterministic prompt helper variables for a reasoning task."""
    key = task_type.upper()
    return {
        "reasoning_constraints": REASONING_CONSTRAINTS,
        "task_guidance": TASK_PROMPT_GUIDANCE.get(
            key,
            TASK_PROMPT_GUIDANCE["GENERAL_ENGINEERING_REASONING"],
        ),
    }
