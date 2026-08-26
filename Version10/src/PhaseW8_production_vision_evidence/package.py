"""Write run-isolated Hybrid evidence packages. No secrets."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    CLASS_COMPATIBILITY,
    CLASS_FALLBACK,
    CLASS_PRIMARY,
    CLASS_UNAVAILABLE,
    SOURCE_P2610_PRIMARY,
    SOURCE_T1_COMPAT,
    SOURCE_W6_COMPAT,
)
from .generator import DxfSession, build_beam_evidence, evidence_root, manifest_path

logger = logging.getLogger("steel_webapp.hybrid_production")

_SECRET_KEYS = ("api_key", "authorization", "anthropic", "sk-ant")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _sanitize(v)
            for k, v in value.items()
            if not any(s in str(k).lower() for s in _SECRET_KEYS)
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, str) and ("sk-ant-" in value.lower() or "api_key" in value.lower()):
        return "[REDACTED]"
    return value


def _dump_manifest(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_sanitize(payload), indent=2, default=str),
        encoding="utf-8",
    )


def prepare_production_evidence(staging: Path, *, beam_ids: List[str]) -> Dict[str, Any]:
    """
    Generate evidence packages for Hybrid-eligible beams.

    Writes hybrid_evidence/<beam_id>/{context,detail}/selected.png and
    evidence_manifest.json. W.6 envelope rendering is an explicit fallback.
    """
    staging = Path(staging)
    session = DxfSession(staging)
    by_id: Dict[str, Dict[str, Any]] = {}
    counts = {
        "p2610_primary": 0,
        "w6_compatibility": 0,
        "t1_compatibility": 0,
        "fallback": 0,
        "unavailable": 0,
        "context_selected": 0,
        "detail_selected": 0,
        "multiple_detail_beams": 0,
        "distinct_context_detail": 0,
    }
    run_id = Path(staging).name
    evidence_timeout_s = 120.0
    try:
        from PhaseW5_production_hybrid_shadow.settings import load_settings as _load_hybrid

        evidence_timeout_s = float(getattr(_load_hybrid(), "evidence_timeout_s", 120.0) or 0)
    except Exception:
        evidence_timeout_s = 120.0
    try:
        from PhaseW11_hybrid_reliability.bounded import TimeoutExpired, run_with_timeout
        from PhaseW11_hybrid_reliability.config import (
            PHASE_EVIDENCE,
            STATUS_EVIDENCE_TIMEOUT,
        )
        from PhaseW11_hybrid_reliability.progress import write_progress
    except Exception:
        TimeoutExpired = TimeoutError  # type: ignore[misc,assignment]

        def run_with_timeout(fn, timeout_s):  # type: ignore[no-redef]
            return fn()

        PHASE_EVIDENCE = "EVIDENCE_GENERATION"
        STATUS_EVIDENCE_TIMEOUT = "EVIDENCE_TIMEOUT"

        def write_progress(*_a, **_k):  # type: ignore[no-redef]
            return None

    total_n = len(beam_ids)
    for i, bid in enumerate(beam_ids, 1):
        write_progress(
            staging,
            run_id=run_id,
            phase=PHASE_EVIDENCE,
            beam_id=str(bid),
            index=i,
            total=total_n,
        )
        try:
            rec = run_with_timeout(
                lambda b=str(bid): build_beam_evidence(
                    staging=staging, beam_id=b, session=session
                ),
                evidence_timeout_s,
            )
        except (TimeoutExpired, TimeoutError):
            logger.warning(
                "W.8 evidence timed out beam_id=%s timeout_s=%s",
                bid,
                evidence_timeout_s,
            )
            rec = {
                "ok": False,
                "available": False,
                "beam_id": str(bid),
                "evidence_class": CLASS_UNAVAILABLE,
                "visual_source": None,
                "context_path": None,
                "detail_path": None,
                "path": None,
                "fallback_status": CLASS_UNAVAILABLE,
                "fallback_reason": STATUS_EVIDENCE_TIMEOUT,
                "manifest": {
                    "beam_id": str(bid),
                    "available": False,
                    "evidence_class": CLASS_UNAVAILABLE,
                    "fallback_status": CLASS_UNAVAILABLE,
                    "fallback_reason": STATUS_EVIDENCE_TIMEOUT,
                    "timeout_status": STATUS_EVIDENCE_TIMEOUT,
                },
                "reason": STATUS_EVIDENCE_TIMEOUT,
                "timeout_status": STATUS_EVIDENCE_TIMEOUT,
            }
        _dump_manifest(manifest_path(staging, str(bid)), rec.get("manifest") or {})
        by_id[str(bid)] = rec
        cls = rec.get("evidence_class")
        src = rec.get("visual_source")
        if cls == CLASS_PRIMARY or src == SOURCE_P2610_PRIMARY:
            counts["p2610_primary"] += 1
        elif src == SOURCE_W6_COMPAT or cls == CLASS_FALLBACK:
            counts["w6_compatibility"] += 1
            counts["fallback"] += 1
        elif src == SOURCE_T1_COMPAT or cls == CLASS_COMPATIBILITY:
            counts["t1_compatibility"] += 1
        elif cls == CLASS_UNAVAILABLE:
            counts["unavailable"] += 1
        else:
            counts["unavailable"] += 1
        if rec.get("available") and rec.get("context_path"):
            counts["context_selected"] += 1
        if rec.get("available") and rec.get("detail_path"):
            counts["detail_selected"] += 1
        man = rec.get("manifest") or {}
        if man.get("context_and_detail_distinct"):
            counts["distinct_context_detail"] += 1
        logger.info(
            "W.8 evidence beam_id=%s class=%s source=%s fallback=%s reason=%s",
            bid,
            rec.get("evidence_class"),
            rec.get("visual_source"),
            rec.get("fallback_status"),
            rec.get("fallback_reason") or rec.get("reason"),
        )
    generated = sum(1 for r in by_id.values() if r.get("available"))
    report = {
        "ok": True,
        "phase": "W.8",
        "dxf": str(session.dxf) if session.dxf else None,
        "dxf_error": session.error,
        "evidence_root": str(evidence_root(staging)),
        "beam_count": len(beam_ids),
        "evidence_packages_generated": generated,
        "p2610_primary": counts["p2610_primary"],
        "w6_compatibility": counts["w6_compatibility"],
        "t1_compatibility": counts["t1_compatibility"],
        "fallback": counts["fallback"],
        "unavailable": counts["unavailable"],
        "context_selected": counts["context_selected"],
        "detail_selected": counts["detail_selected"],
        "multiple_detail_beams": counts["multiple_detail_beams"],
        "distinct_context_detail": counts["distinct_context_detail"],
        "source": "W8_P2610_EVIDENCE",
        "rendered": counts["p2610_primary"],
        "t1_available": counts["t1_compatibility"],
        "render_failed": counts["unavailable"],
        "by_id": {
            bid: {
                "available": rec.get("available"),
                "evidence_class": rec.get("evidence_class"),
                "visual_source": rec.get("visual_source"),
                "fallback_status": rec.get("fallback_status"),
                "fallback_reason": rec.get("fallback_reason"),
                "reason": rec.get("reason"),
            }
            for bid, rec in by_id.items()
        },
    }
    identity_eligible = len(beam_ids)
    identity_accounted = generated + counts["unavailable"]
    report["coverage_identity"] = {
        "eligible_hybrid_beams": identity_eligible,
        "beams_with_valid_evidence": generated,
        "explicitly_unavailable_beams": counts["unavailable"],
        "eligible_equals_valid_plus_unavailable": identity_eligible == identity_accounted,
    }
    return report


__all__ = ["prepare_production_evidence"]
