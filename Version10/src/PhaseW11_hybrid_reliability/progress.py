"""Fail-safe Hybrid progress heartbeat. Never records secrets."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import (
    PHASE_COMPLETE,
    PHASE_EVIDENCE,
    PHASE_FALLBACK,
    PHASE_VISION,
    PROGRESS_FILENAME,
)

logger = logging.getLogger("steel_webapp.hybrid_reliability")

_SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]+)|(ANTHROPIC_API_KEY\s*=\s*\S+)|(api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)

W6_OUTPUT_REL = "data/output/PhaseW6_hybrid_semantic_resolution"


def progress_path(staging: Path) -> Path:
    return Path(staging) / W6_OUTPUT_REL / PROGRESS_FILENAME


def progress_label(
    *,
    phase: str,
    beam_id: Optional[str] = None,
    index: Optional[int] = None,
    total: Optional[int] = None,
    extra: Optional[str] = None,
) -> str:
    if extra:
        return extra
    n = f" ({index} of {total})" if index and total else ""
    bid = f" {beam_id}" if beam_id else ""
    if phase == PHASE_EVIDENCE:
        return f"Preparing visual evidence... Processing beam{bid}{n}"
    if phase == PHASE_VISION:
        return f"Resolving reinforcement semantics... Processing beam{bid}{n}"
    if phase == PHASE_FALLBACK:
        return "Vision call timed out — continuing with deterministic fallback..."
    if phase == PHASE_COMPLETE:
        return "Completing deterministic engineering..."
    return "Resolving reinforcement semantics..."


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _sanitize(v)
            for k, v in value.items()
            if "api_key" not in str(k).lower() and "authorization" not in str(k).lower()
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, str):
        return _SECRET_RE.sub("[REDACTED]", value)
    return value


def write_progress(
    staging: Path,
    *,
    run_id: str,
    phase: str,
    beam_id: Optional[str] = None,
    index: Optional[int] = None,
    total: Optional[int] = None,
    extra: Optional[str] = None,
    started_at: Optional[str] = None,
    beam_started_at: Optional[str] = None,
    status: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort progress write. Must never fail the Hybrid stage."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            "run_id": run_id,
            "phase": phase,
            "beam_id": beam_id,
            "index": index,
            "total": total,
            "label": progress_label(
                phase=phase,
                beam_id=beam_id,
                index=index,
                total=total,
                extra=extra,
            ),
            "status": status,
            "updated_at": now,
            "started_at": started_at,
            "beam_started_at": beam_started_at or now,
        }
        if extra_fields:
            payload.update(extra_fields)
        path = progress_path(staging)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_sanitize(payload), indent=2, default=str),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("W.11 progress write failed error_type=%s", type(exc).__name__)


def load_progress(staging: Path) -> Optional[Dict[str, Any]]:
    path = progress_path(staging)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data
