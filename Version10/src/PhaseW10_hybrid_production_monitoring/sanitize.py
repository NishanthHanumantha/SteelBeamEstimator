"""Strip secrets from monitoring payloads. Never persist API keys."""
from __future__ import annotations

import re
from typing import Any

_SECRET_KEYS = ("api_key", "authorization", "anthropic", "sk-ant")
_SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]+)|(ANTHROPIC_API_KEY\s*=\s*\S+)|(api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: sanitize(v)
            for k, v in value.items()
            if not any(s in str(k).lower() for s in _SECRET_KEYS)
        }
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        if "sk-ant-" in value.lower() or "api_key" in value.lower():
            return _SECRET_RE.sub("[REDACTED]", value)
        return value
    return value
