"""W.6 production Hybrid stage: Vision + D.2 resolve + canonical R13 handoff."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PhaseW5_production_hybrid_shadow.adapter import run_hybrid_shadow
from PhaseW5_production_hybrid_shadow.config import MODE_OFF, MODE_PRODUCTION
from PhaseW5_production_hybrid_shadow.paths import ENGINE_ROOT, ensure_src_on_path
from PhaseW5_production_hybrid_shadow.settings import HybridSettings, api_key_status, load_settings

from .config import (
    CLASS_SKIPPED,
    COVERAGE_FILENAME,
    GATE_VERSION,
    HANDOFF_LEDGER_FILENAME,
    OBSERVABILITY_FILENAME,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    R13_REL,
    RESOLUTION_FILENAME,
)
from .coverage import build_coverage
from .handoff import apply_production_handoff
from .observability import classify_run, public_observability, public_summary
from .visuals import ensure_visuals

logger = logging.getLogger("steel_webapp.hybrid_production")


def output_dir(staging: Path) -> Path:
    return Path(staging) / "data" / "output" / OUTPUT_DIRNAME


def _dump(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _prime_api_key() -> bool:
    """Load ANTHROPIC_API_KEY from process env or dotenv. Never logs the value."""
    if api_key_status() == "PRESENT":
        return True
    try:
        from dotenv import load_dotenv
    except Exception:
        return False
    import os

    candidates = []
    override = (os.environ.get("ANTHROPIC_DOTENV_PATH") or "").strip()
    if override:
        candidates.append(Path(override))
    candidates.append(ENGINE_ROOT.parent / ".env")
    candidates.append(ENGINE_ROOT / ".env")
    seen = set()
    for path in candidates:
        resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        if path.is_file():
            load_dotenv(path, override=False)
            if api_key_status() == "PRESENT":
                return True
    return api_key_status() == "PRESENT"


def load_public_summary(staging: Path) -> Optional[Dict[str, Any]]:
    path = output_dir(staging) / OBSERVABILITY_FILENAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return public_summary(data)


def run_production_hybrid(
    *,
    run_id: str,
    staging: Path,
    client_override: Optional[Callable] = None,
    settings: Optional[HybridSettings] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Execute Hybrid as a production stage between R13 and VB1.

    HYBRID_MODE=off      → skip, no Claude, R13 unchanged
    HYBRID_MODE=shadow   → observe, no R13 patch
    HYBRID_MODE=production → Vision-preferred fields patched onto R13
    Failures never fabricate Vision results; deterministic R13 is kept.
    """
    staging = Path(staging)
    if settings is None:
        primed = _prime_api_key()
        cfg = load_settings()
    else:
        cfg = settings
        primed = cfg.api_key_status == "PRESENT"
    out = output_dir(staging)
    started_iso = datetime.now(timezone.utc).isoformat()

    if cfg.mode == MODE_OFF:
        payload = {
            "ok": True,
            "phase_id": PHASE_ID,
            "phase_name": PHASE_NAME,
            "gate_version": GATE_VERSION,
            "run_id": run_id,
            "hybrid_mode": MODE_OFF,
            "classification": CLASS_SKIPPED,
            "hybrid_status": "SKIPPED_MODE_OFF",
            "reason": "HYBRID_MODE_OFF",
            "production_authority_applied": False,
            "claude_invocation_count": 0,
            "request_count": 0,
            "started_at": started_iso,
        }
        return payload

    r13 = staging / R13_REL
    if not r13.is_file():
        payload = {
            "ok": False,
            "phase_id": PHASE_ID,
            "run_id": run_id,
            "hybrid_mode": cfg.mode,
            "classification": "HYBRID_UNAVAILABLE",
            "hybrid_status": "NO_ENGINEERING_CONTEXT",
            "reason": "R13_MISSING",
            "production_authority_applied": False,
            "claude_invocation_count": 0,
            "request_count": 0,
        }
        if persist:
            _dump(out / OBSERVABILITY_FILENAME, public_observability(
                run_id=run_id,
                mode=cfg.mode,
                shadow_result={"hybrid_status": "NO_ENGINEERING_CONTEXT", "reason": "R13_MISSING", "hybrid_started": True, "settings": cfg.public_dict(), "beams": []},
                handoff={"applied": False, "reason": "R13_MISSING"},
                classification="HYBRID_UNAVAILABLE",
                primed_key=primed,
            ))
        return payload

    from PhaseW5_production_hybrid_shadow.catalog import load_r13_catalog

    catalog = load_r13_catalog(staging)
    visual_prep = {"rendered": 0, "t1_available": 0}
    if catalog.get("ok"):
        visual_prep = ensure_visuals(
            staging, beam_ids=list(catalog.get("beam_ids") or [])
        )

    shadow = run_hybrid_shadow(
        run_id=run_id,
        staging=staging,
        client_override=client_override,
        settings=cfg,
        persist=True,
    )
    apply = cfg.mode == MODE_PRODUCTION
    try:
        handoff = apply_production_handoff(
            staging=staging,
            shadow_result=shadow,
            apply=apply,
        )
    except Exception as exc:
        logger.exception("Hybrid handoff failed run_id=%s", run_id)
        handoff = {
            "applied": False,
            "reason": "HANDOFF_EXCEPTION",
            "error_type": type(exc).__name__,
            "beams_patched": 0,
            "fields_patched": 0,
            "unresolved_vision_only": 0,
            "ledger": [],
        }

    classification = classify_run(mode=cfg.mode, shadow_result=shadow, handoff=handoff)
    observability = public_observability(
        run_id=run_id,
        mode=cfg.mode,
        shadow_result=shadow,
        handoff=handoff,
        classification=classification,
        primed_key=primed,
    )
    observability["visual_prep"] = visual_prep
    coverage = build_coverage(
        mode=cfg.mode,
        beam_ids=list(catalog.get("beam_ids") or []) if catalog.get("ok") else [],
        shadow_result=shadow,
        visual_prep=visual_prep,
    )
    observability["coverage"] = {
        k: coverage.get(k)
        for k in (
            "total_production_beams",
            "hybrid_eligible",
            "p2610_primary_evidence",
            "native_t1_crop",
            "generated_fallback_crop",
            "visual_context_unavailable",
            "evidence_packages_generated",
            "context_selected",
            "detail_selected",
            "w6_compatibility_path",
            "t1_compatibility_path",
            "fallback_path",
            "evidence_unavailable",
            "claude_invocations",
            "claude_attempted",
            "claude_success",
            "claude_failure",
            "explicitly_skipped",
            "deterministic_fallback",
            "hybrid_resolved",
            "unresolved",
            "unexplained",
            "identity_ok",
        )
    }
    resolution = {
        "phase_id": PHASE_ID,
        "gate_version": GATE_VERSION,
        "run_id": run_id,
        "hybrid_mode": cfg.mode,
        "classification": classification,
        "authority": {
            "vision_preferred": [
                "TARGET",
                "LAYER",
                "PHYSICAL_GROUPS",
                "BAR_COUNT",
                "DIAMETER",
                "SPECIFICATION",
                "ROLE",
                "SUPPORT_SCOPE",
                "STIRRUP_IDENTIFICATION",
            ],
            "deterministic": [
                "GEOMETRY",
                "SPACER",
                "CUT_LENGTH",
                "DEVELOPMENT_LENGTH",
                "ANCHORAGE",
                "HOOKS_BENDS",
                "STIRRUP_ENGINEERING_CALCULATION",
                "PIECE_GENERATION",
                "WEIGHT",
                "BBS",
                "WORKBOOK",
            ],
        },
        "handoff": {
            "applied": handoff.get("applied"),
            "reason": handoff.get("reason"),
            "r13_path": handoff.get("r13_path"),
            "pre_hybrid_path": handoff.get("pre_hybrid_path"),
            "beams_patched": handoff.get("beams_patched"),
            "fields_patched": handoff.get("fields_patched"),
        },
        "beams": [
            {
                "beam_id": row.get("beam_id"),
                "hybrid_status": row.get("hybrid_status"),
                "called": row.get("called"),
                "hybrid_interpretation": row.get("hybrid_interpretation"),
                "hybrid_semantic": row.get("hybrid_semantic"),
                "skip_reason": row.get("skip_reason"),
                "failure_category": row.get("failure_category"),
                "model": row.get("model"),
            }
            for row in (shadow.get("beams") or [])
            if isinstance(row, dict)
        ],
    }
    if persist:
        _dump(out / RESOLUTION_FILENAME, resolution)
        _dump(out / OBSERVABILITY_FILENAME, observability)
        _dump(
            out / HANDOFF_LEDGER_FILENAME,
            {
                "run_id": run_id,
                "applied": handoff.get("applied"),
                "reason": handoff.get("reason"),
                "ledger": handoff.get("ledger") or [],
            },
        )
        _dump(out / COVERAGE_FILENAME, coverage)
    result = {
        "ok": True,
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "gate_version": GATE_VERSION,
        "run_id": run_id,
        "engine_root": str(ENGINE_ROOT),
        "staging": str(staging),
        "hybrid_mode": cfg.mode,
        "classification": classification,
        "hybrid_status": classification,
        "reason": shadow.get("reason"),
        "production_authority_applied": bool(handoff.get("applied")),
        "handoff_reason": handoff.get("reason"),
        "claude_invocation_count": observability.get("claude_invocation_count"),
        "request_count": observability.get("claude_invocation_count"),
        "successful_invocation_count": observability.get("successful_invocation_count"),
        "failed_invocation_count": observability.get("failed_invocation_count"),
        "hybrid_latency_s": observability.get("hybrid_latency_s"),
        "model": observability.get("model"),
        "beams_patched": handoff.get("beams_patched"),
        "fields_patched": handoff.get("fields_patched"),
        "fallback_used": observability.get("fallback_used"),
        "visual_prep": visual_prep,
        "coverage": observability.get("coverage"),
        "observability": observability,
        "handoff": {k: handoff.get(k) for k in ("applied", "reason", "pre_hybrid_path", "r13_path", "beams_patched", "fields_patched")},
    }
    return result
