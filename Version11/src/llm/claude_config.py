"""Centralized Anthropic Claude configuration."""

from __future__ import annotations

from pathlib import Path


class ClaudeConfig:
    """Single source of truth for Claude provider settings."""

    PHASE = "Phase LLM.1"
    MODEL_VERSION = "6.1.0"

    MODEL_NAME = "claude-sonnet-4-5"
    MAX_OUTPUT_TOKENS = 4096
    TEMPERATURE = 0
    TIMEOUT_SECONDS = 120
    MAX_RETRIES = 3
    API_KEY_ENV = "ANTHROPIC_API_KEY"
    DOTENV_PATH = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\.env")

    # Obsolete — not supported at runtime (retained for migration documentation only).
    OBSOLETE_ENV_VARS = (
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "OPENAI_MODEL",
        "DEEPSEEK_MODEL",
        "LLM_PROVIDER",
        "MODEL_PROVIDER",
        "ANTROPIC_API_KEY",
    )
