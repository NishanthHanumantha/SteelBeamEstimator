"""Environment-driven Hybrid shadow settings. Never logs secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .config import (
    ALLOWED_MODES,
    AUTHORITATIVE_ENABLED,
    DEFAULT_EVIDENCE_TIMEOUT_S,
    DEFAULT_MAX_LIVE_CALLS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_WALL_S,
    DEFAULT_PER_CALL_TIMEOUT_S,
    DEFAULT_TOTAL_BEAM_TIMEOUT_S,
    ENV_API_KEY,
    ENV_DOTENV_PATH,
    ENV_HYBRID_MODE,
    ENV_EVIDENCE_TIMEOUT_S,
    ENV_MAX_LIVE_CALLS,
    ENV_MAX_RETRIES,
    ENV_MAX_WALL_S,
    ENV_MODEL,
    ENV_PER_CALL_TIMEOUT_S,
    ENV_TOTAL_BEAM_TIMEOUT_S,
    MODE_AUTHORITATIVE,
    MODE_OFF,
    MODE_PRODUCTION,
    MODE_SHADOW,
)


def hybrid_mode() -> str:
    raw = (os.environ.get(ENV_HYBRID_MODE) or MODE_OFF).strip().lower()
    aliases = {
        "false": MODE_OFF,
        "0": MODE_OFF,
        "no": MODE_OFF,
        "disabled": MODE_OFF,
        "none": MODE_OFF,
        "true": MODE_SHADOW,
        "1": MODE_SHADOW,
        "yes": MODE_SHADOW,
        "on": MODE_SHADOW,
    }
    raw = aliases.get(raw, raw)
    if raw not in ALLOWED_MODES:
        return MODE_OFF
    return raw


def _positive_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def _positive_float(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def api_key_status() -> str:
    value = os.environ.get(ENV_API_KEY)
    if value is None:
        return "ABSENT"
    if not str(value).strip():
        return "EMPTY"
    return "PRESENT"


def api_key_available() -> bool:
    return api_key_status() == "PRESENT"


@dataclass(frozen=True)
class HybridSettings:
    mode: str
    api_key_status: str
    model_override: Optional[str]
    max_live_calls: int
    max_wall_s: float
    per_call_timeout_s: float
    dotenv_override: Optional[str]
    authoritative_enabled: bool = AUTHORITATIVE_ENABLED
    max_retries: int = DEFAULT_MAX_RETRIES
    total_beam_timeout_s: float = DEFAULT_TOTAL_BEAM_TIMEOUT_S
    evidence_timeout_s: float = DEFAULT_EVIDENCE_TIMEOUT_S

    @property
    def shadow_requested(self) -> bool:
        return self.mode == MODE_SHADOW

    @property
    def production_requested(self) -> bool:
        return self.mode == MODE_PRODUCTION

    @property
    def live_calls_allowed(self) -> bool:
        return self.mode in (MODE_SHADOW, MODE_PRODUCTION) and self.api_key_status == "PRESENT"

    def public_dict(self) -> dict:
        return {
            "mode": self.mode,
            "api_key_status": self.api_key_status,
            "model_override": self.model_override,
            "max_live_calls": self.max_live_calls,
            "max_wall_s": self.max_wall_s,
            "per_call_timeout_s": self.per_call_timeout_s,
            "max_retries": self.max_retries,
            "total_beam_timeout_s": self.total_beam_timeout_s,
            "evidence_timeout_s": self.evidence_timeout_s,
            "dotenv_override_configured": bool(self.dotenv_override),
            "authoritative_enabled": self.authoritative_enabled,
            "live_calls_allowed": self.live_calls_allowed,
            "production_authority": (
                "semantic_only" if self.mode == MODE_PRODUCTION else "none"
            ),
        }


def _defaults_for_mode(mode: str) -> tuple[int, float]:
    if mode == MODE_PRODUCTION:
        return 0, 0.0
    return DEFAULT_MAX_LIVE_CALLS, DEFAULT_MAX_WALL_S


def load_settings() -> HybridSettings:
    dotenv = (os.environ.get(ENV_DOTENV_PATH) or "").strip() or None
    model = (os.environ.get(ENV_MODEL) or "").strip() or None
    mode = hybrid_mode()
    default_calls, default_wall = _defaults_for_mode(mode)
    return HybridSettings(
        mode=mode,
        api_key_status=api_key_status(),
        model_override=model,
        max_live_calls=_positive_int(ENV_MAX_LIVE_CALLS, default_calls),
        max_wall_s=_positive_float(ENV_MAX_WALL_S, default_wall),
        per_call_timeout_s=_positive_float(
            ENV_PER_CALL_TIMEOUT_S, DEFAULT_PER_CALL_TIMEOUT_S
        ),
        dotenv_override=dotenv,
        max_retries=_positive_int(ENV_MAX_RETRIES, DEFAULT_MAX_RETRIES),
        total_beam_timeout_s=_positive_float(
            ENV_TOTAL_BEAM_TIMEOUT_S, DEFAULT_TOTAL_BEAM_TIMEOUT_S
        ),
        evidence_timeout_s=_positive_float(
            ENV_EVIDENCE_TIMEOUT_S, DEFAULT_EVIDENCE_TIMEOUT_S
        ),
    )


def health_payload(settings: Optional[HybridSettings] = None) -> dict:
    cfg = settings or load_settings()
    key_present = cfg.api_key_status == "PRESENT"
    return {
        "mode": cfg.mode,
        "enabled": cfg.mode != MODE_OFF,
        "api_key_configured": key_present,
        "api_key_status": cfg.api_key_status,
        "authoritative_enabled": False,
        "production_authority": (
            "semantic_only" if cfg.mode == MODE_PRODUCTION else "none"
        ),
        "production_excel_invokes_claude": False,
        "shadow_may_invoke_claude": cfg.mode == MODE_SHADOW and key_present,
        "production_may_invoke_claude": cfg.mode == MODE_PRODUCTION and key_present,
        "max_live_calls": cfg.max_live_calls,
        "max_wall_s": cfg.max_wall_s,
        "per_call_timeout_s": cfg.per_call_timeout_s,
        "max_retries": cfg.max_retries,
        "total_beam_timeout_s": cfg.total_beam_timeout_s,
        "evidence_timeout_s": cfg.evidence_timeout_s,
        "live_calls_allowed": cfg.live_calls_allowed,
    }
