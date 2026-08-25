"""ESTIMATED Claude usage cost. Never presented as billed exact."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import (
    COST_BASIS,
    ESTIMATED_INPUT_USD_PER_MTOK,
    ESTIMATED_OUTPUT_USD_PER_MTOK,
)


def _tokens(usage: Optional[Dict[str, Any]], key: str) -> int:
    if not isinstance(usage, dict):
        return 0
    try:
        return max(0, int(usage.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def estimate_cost_usd(*, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
    input_tokens = max(0, int(input_tokens or 0))
    output_tokens = max(0, int(output_tokens or 0))
    usd = (
        (input_tokens / 1_000_000.0) * ESTIMATED_INPUT_USD_PER_MTOK
        + (output_tokens / 1_000_000.0) * ESTIMATED_OUTPUT_USD_PER_MTOK
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(usd, 6),
        "cost_basis": COST_BASIS,
        "input_usd_per_mtok": ESTIMATED_INPUT_USD_PER_MTOK,
        "output_usd_per_mtok": ESTIMATED_OUTPUT_USD_PER_MTOK,
    }


def usage_from_audit(audit: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    usage = (audit or {}).get("usage") if isinstance(audit, dict) else None
    inp = _tokens(usage, "input_tokens")
    out = _tokens(usage, "output_tokens")
    if inp == 0 and isinstance(audit, dict):
        try:
            inp = int(audit.get("estimated_input_tokens") or 0)
        except (TypeError, ValueError):
            inp = 0
    if out == 0 and isinstance(audit, dict):
        try:
            out = int(audit.get("estimated_output_tokens") or 0)
        except (TypeError, ValueError):
            out = 0
    payload = estimate_cost_usd(input_tokens=inp, output_tokens=out)
    payload["latency_s"] = (audit or {}).get("latency_s") if isinstance(audit, dict) else None
    payload["model"] = (audit or {}).get("model") if isinstance(audit, dict) else None
    return payload
