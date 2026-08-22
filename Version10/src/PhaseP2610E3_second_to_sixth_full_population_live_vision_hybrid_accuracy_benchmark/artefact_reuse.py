"""E.2 Fifth reuse + E.3 checkpoint reuse. Incompatible artefacts fail closed."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark.artefact_reuse import (
    e2_result_reusable,
    historical_failure_eligible,
    provenance_from_live as e2_provenance_from_live,
)

from .config import (
    FIFTH_SET_KEY,
    P2610E2_OUTPUT_DIRNAME,
    PROV_NEW,
    PROV_NOT_AVAILABLE,
    PROV_RETRIED,
    PROV_REUSED,
    PROV_UNUSABLE,
)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sha_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def e3_live_result_path(out_root: Path, set_key: str, beam_id: str) -> Path:
    return Path(out_root) / "live_results" / str(set_key) / f"{beam_id}.json"


def e2_output_root(v10: Path) -> Path:
    return Path(v10) / "data" / "output" / P2610E2_OUTPUT_DIRNAME


def e2_live_result_path(v10: Path, beam_id: str) -> Path:
    return e2_output_root(v10) / "live_results" / f"{beam_id}.json"


def load_e3_row(out_root: Path, set_key: str, beam_id: str) -> Optional[Dict[str, Any]]:
    return _load(e3_live_result_path(out_root, set_key, beam_id))


def save_e3_row(out_root: Path, set_key: str, row: Dict[str, Any]) -> None:
    path = e3_live_result_path(out_root, set_key, str(row.get("beam_id")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=2, default=str), encoding="utf-8")


def load_e2_row(v10: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    return _load(e2_live_result_path(v10, beam_id))


def contract_compatible(v10: Path) -> Dict[str, Any]:
    contract = (
        Path(v10)
        / "data"
        / "output"
        / "PhaseP2610D1_vision_semantic_contract_hybrid_foundation"
        / "hybrid_authority_contract.json"
    )
    e2_results = e2_output_root(v10) / "P2.6.10-E.2_RESULTS.json"
    present = contract.exists() and e2_results.exists()
    e2 = _load(e2_results) if e2_results.exists() else {}
    live_ok = str((e2 or {}).get("live_completion") or "") == "COMPLETE_LIVE_BENCHMARK"
    return {
        "ok": bool(present and live_ok),
        "contract_present": contract.exists(),
        "e2_results_present": e2_results.exists(),
        "e2_live_completion": (e2 or {}).get("live_completion"),
        "contract_sha256": _sha_file(contract),
        "reason": None if (present and live_ok) else "E2_ARTEFACT_INCOMPATIBLE",
    }


def fifth_population_compatible(*, current_ids, e2_ids) -> Dict[str, Any]:
    cur = {str(x) for x in (current_ids or [])}
    old = {str(x) for x in (e2_ids or [])}
    return {
        "ok": bool(cur) and cur == old,
        "current_count": len(cur),
        "e2_count": len(old),
        "only_current": sorted(cur - old),
        "only_e2": sorted(old - cur),
    }


def e2_fifth_ids(v10: Path) -> list:
    pop = _load(e2_output_root(v10) / "benchmark_population_manifest.json") or {}
    ids = pop.get("model_beam_ids") or []
    return [str(x) for x in ids] if ids else []


def row_reusable(row: Optional[Dict[str, Any]], *, source_sha: Optional[str]) -> bool:
    if not isinstance(row, dict):
        return False
    if row.get("failure_category") == "LIVE_DISABLED":
        return False
    if not row.get("complete"):
        return False
    stored = (row.get("visual") or {}).get("sha256")
    if source_sha and stored and str(stored).lower() != str(source_sha).lower():
        return False
    if row.get("failure_category") == "API_FAILED" and not row.get("semantic_usable"):
        return False
    completed_negative = row.get("failure_category") in (
        "SCHEMA_FAILED",
        "SEMANTIC_UNUSABLE",
        "TARGET_NOT_IDENTIFIED",
    )
    if row.get("semantic_usable") or completed_negative:
        if row.get("extracted") is not None or row.get("called") or row.get("action") == "REUSE":
            return True
    return e2_result_reusable(row, source_sha=source_sha)


def provenance_from_live(fail: str, *, intended: str) -> str:
    mapped = e2_provenance_from_live(fail, intended=intended)
    remap = {
        "VISION_REUSED": PROV_REUSED,
        "VISION_UNUSABLE": PROV_UNUSABLE,
        "VISION_BLOCKED_NOT_READY": PROV_NOT_AVAILABLE,
    }
    return remap.get(mapped, mapped)


def decide_action(
    *,
    set_key: str,
    eligible: bool,
    e3_row: Optional[Dict[str, Any]],
    e2_row: Optional[Dict[str, Any]],
    source_sha: Optional[str],
    historical: Optional[Dict[str, Any]],
    e2_reuse_allowed: bool,
) -> Dict[str, Any]:
    if not eligible:
        return {"action": "BLOCK", "provenance": PROV_NOT_AVAILABLE, "reuse": False, "reuse_source": None}
    if row_reusable(e3_row, source_sha=source_sha):
        return {
            "action": "REUSE",
            "provenance": PROV_REUSED,
            "reuse": True,
            "reuse_source": "E3_CHECKPOINT",
        }
    if set_key == FIFTH_SET_KEY and e2_reuse_allowed and row_reusable(e2_row, source_sha=source_sha):
        return {
            "action": "REUSE",
            "provenance": PROV_REUSED,
            "reuse": True,
            "reuse_source": "E2_FIFTH_LIVE",
        }
    hist_failed = False
    if isinstance(historical, dict):
        reason = str(historical.get("unusable_reason") or historical.get("error_class") or "").upper()
        hist_failed = "API" in reason or historical.get("usable") is False
    if hist_failed and historical_failure_eligible(historical):
        return {"action": "LIVE", "provenance": PROV_RETRIED, "reuse": False, "reuse_source": None}
    return {"action": "LIVE", "provenance": PROV_NEW, "reuse": False, "reuse_source": None}


__all__ = [
    "contract_compatible",
    "decide_action",
    "e2_fifth_ids",
    "e2_output_root",
    "fifth_population_compatible",
    "historical_failure_eligible",
    "load_e2_row",
    "load_e3_row",
    "provenance_from_live",
    "row_reusable",
    "save_e3_row",
]
