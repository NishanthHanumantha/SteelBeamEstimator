"""E.2 artefact reuse, historical-failure retry eligibility, and fingerprint invalidation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .config import (
    PROV_API_FAILED,
    PROV_BLOCKED,
    PROV_NEW,
    PROV_RETRIED,
    PROV_REUSED,
    PROV_SCHEMA_FAILED,
    PROV_UNUSABLE,
)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def live_result_path(out_root: Path, beam_id: str) -> Path:
    return Path(out_root) / "live_results" / f"{beam_id}.json"


def historical_failure_eligible(hist: Optional[Dict[str, Any]]) -> bool:
    """Historical API failure is never a permanent Vision block."""
    if not isinstance(hist, dict):
        return True
    if hist.get("usable") is True and hist.get("extracted"):
        return False
    reason = str(hist.get("unusable_reason") or hist.get("error_class") or hist.get("failure_category") or "").upper()
    if "API" in reason or "CREDIT" in reason or "AUTH" in reason or "RATE" in reason:
        return True
    return True


def e2_result_reusable(row: Optional[Dict[str, Any]], *, source_sha: Optional[str]) -> bool:
    if not isinstance(row, dict):
        return False
    if not row.get("complete"):
        return False
    stored = (row.get("visual") or {}).get("sha256")
    if source_sha and stored and str(stored).lower() != str(source_sha).lower():
        return False
    if row.get("failure_category") == "API_FAILED" and not row.get("semantic_usable"):
        return False
    if row.get("called") and row.get("complete"):
        if row.get("semantic_usable"):
            return True
        if row.get("failure_category") in ("SCHEMA_FAILED", "SEMANTIC_UNUSABLE", "TARGET_NOT_IDENTIFIED"):
            return True
    return False


def decide_action(
    *,
    eligible: bool,
    e2_row: Optional[Dict[str, Any]],
    source_sha: Optional[str],
    historical: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not eligible:
        return {"action": "BLOCK", "provenance": PROV_BLOCKED, "reuse": False}
    if e2_result_reusable(e2_row, source_sha=source_sha):
        return {"action": "REUSE", "provenance": PROV_REUSED, "reuse": True}
    hist_failed = False
    if isinstance(historical, dict):
        reason = str(historical.get("unusable_reason") or historical.get("error_class") or "").upper()
        hist_failed = "API" in reason or historical.get("usable") is False
    if hist_failed and historical_failure_eligible(historical):
        return {"action": "LIVE", "provenance": PROV_RETRIED, "reuse": False}
    return {"action": "LIVE", "provenance": PROV_NEW, "reuse": False}


def provenance_from_live(fail: str, *, intended: str) -> str:
    if fail == "API_FAILED":
        return PROV_API_FAILED
    if fail == "SCHEMA_FAILED":
        return PROV_SCHEMA_FAILED
    if fail in ("SEMANTIC_UNUSABLE", "TARGET_NOT_IDENTIFIED"):
        return PROV_UNUSABLE
    return intended


def load_e2_row(out_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    return _load(live_result_path(out_root, beam_id))


def save_e2_row(out_root: Path, row: Dict[str, Any]) -> None:
    path = live_result_path(out_root, str(row.get("beam_id")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=2, default=str), encoding="utf-8")


__all__ = [
    "decide_action",
    "e2_result_reusable",
    "historical_failure_eligible",
    "load_e2_row",
    "live_result_path",
    "provenance_from_live",
    "save_e2_row",
]
