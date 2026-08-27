"""Production Hybrid shadow adapter. Never writes Excel or mutates engineering artefacts."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .catalog import load_r13_catalog, load_steel_fingerprint
from .comparison import classify_beam, summarize_classifications
from .config import (
    EXCEL_REL,
    GATE_VERSION,
    HYBRID_ERROR,
    HYBRID_UNAVAILABLE,
    MODE_AUTHORITATIVE,
    MODE_OFF,
    MODE_PRODUCTION,
    MODE_SHADOW,
    OUTPUT_DIRNAME,
    PHASE_ID,
    PHASE_NAME,
    PRODUCTION_WRITE,
    STATUS_AUTHORITATIVE_FORBIDDEN,
    STATUS_COMPLETE,
    STATUS_ERROR,
    STATUS_KEY_ABSENT,
    STATUS_NO_ENGINEERING,
    STATUS_PARTIAL_BUDGET,
    STATUS_SKIPPED_OFF,
)
from .cost import estimate_cost_usd, usage_from_audit
from .live_invoke import call_shadow_beam
from .paths import ENGINE_ROOT, ensure_src_on_path
from .semantic import resolve_semantic
from .settings import HybridSettings, load_settings
from .visual_sources import discover_visuals

try:
    from PhaseW11_hybrid_reliability.bounded import TimeoutExpired, run_with_timeout
    from PhaseW11_hybrid_reliability.config import PHASE_FALLBACK, PHASE_VISION, STATUS_VISION_TIMEOUT
    from PhaseW11_hybrid_reliability.progress import write_progress
except Exception:  # pragma: no cover - fail-safe if W.11 package missing
    TimeoutExpired = TimeoutError  # type: ignore[misc,assignment]

    def run_with_timeout(fn, timeout_s):  # type: ignore[no-redef]
        return fn()

    PHASE_FALLBACK = "DETERMINISTIC_FALLBACK"
    PHASE_VISION = "CLAUDE_VISION"
    STATUS_VISION_TIMEOUT = "VISION_TIMEOUT"

    def write_progress(*_a, **_k):  # type: ignore[no-redef]
        return None

logger = logging.getLogger("steel_webapp.hybrid_shadow")


def output_dir(staging: Path) -> Path:
    return Path(staging) / "data" / "output" / OUTPUT_DIRNAME


def _excel_fingerprint(staging: Path) -> Dict[str, Any]:
    path = Path(staging) / EXCEL_REL
    if not path.is_file():
        return {"present": False, "path": str(path)}
    return {
        "present": True,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "mtime_ns": path.stat().st_mtime_ns,
    }


def _dump(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _copy_live_diagnostics(row: Dict[str, Any], live: Optional[Dict[str, Any]]) -> None:
    """Persist API/parse diagnostics. Never copies secrets; live.audit is already sanitized."""
    if not isinstance(live, dict):
        return
    audit = live.get("audit") if isinstance(live.get("audit"), dict) else {}
    parsed = live.get("parsed") if isinstance(live.get("parsed"), dict) else {}
    row["api_success"] = bool(live.get("api_success"))
    row["schema_valid"] = live.get("schema_valid")
    row["semantic_usable"] = bool(live.get("semantic_usable"))
    row["parse_status"] = parsed.get("call_status")
    if live.get("error_type"):
        row["error_type"] = live.get("error_type")
    elif audit.get("error_type") and not row.get("error_type"):
        row["error_type"] = audit.get("error_type")
    err = audit.get("error")
    if err and not row.get("api_error"):
        row["api_error"] = str(err)[:400]
    if audit.get("retry_after_s") is not None:
        row["retry_after_s"] = audit.get("retry_after_s")
    if live.get("retry_count") is not None:
        row["retry_count"] = live.get("retry_count")
    if live.get("attempts") is not None:
        row["attempts"] = live.get("attempts")


def _looks_like_rate_limit(row: Dict[str, Any], live: Optional[Dict[str, Any]]) -> bool:
    et = str(row.get("error_type") or "")
    err = str(row.get("api_error") or "").lower()
    audit = (live or {}).get("audit") if isinstance(live, dict) else {}
    if isinstance(audit, dict):
        et = et or str(audit.get("error_type") or "")
        err = err or str(audit.get("error") or "").lower()
    return (
        "RateLimit" in et
        or "429" in err
        or "rate limit" in err
        or "rate_limit" in err
    )


def _empty_result(
    *,
    run_id: str,
    staging: Path,
    settings: HybridSettings,
    status: str,
    reason: str,
    started: float,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    elapsed = round(time.perf_counter() - started, 3)
    payload = {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "gate_version": GATE_VERSION,
        "run_id": run_id,
        "hybrid_mode": settings.mode,
        "hybrid_started": True,
        "hybrid_completed": True,
        "hybrid_status": status,
        "reason": reason,
        "production_write": PRODUCTION_WRITE,
        "authoritative_enabled": False,
        "settings": settings.public_dict(),
        "request_count": 0,
        "cache_hits": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "cost_basis": "ESTIMATED",
        "hybrid_latency_s": elapsed,
        "agreement_counts": summarize_classifications([]),
        "beams": [],
        "excel_fingerprint": _excel_fingerprint(staging),
        "steel_fingerprint": load_steel_fingerprint(staging),
    }
    if extra:
        payload.update(extra)
    return payload


def run_hybrid_shadow(
    *,
    run_id: str,
    staging: Path,
    client_override: Optional[Callable] = None,
    settings: Optional[HybridSettings] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Observe Hybrid semantics for one completed deterministic run.

    Fail-closed: any exception is converted to hybrid_status=ERROR.
    Does not open or write Estimation_Output.xlsx.
    """
    started = time.perf_counter()
    started_iso = datetime.now(timezone.utc).isoformat()
    staging = Path(staging)
    cfg = settings or load_settings()
    ensure_src_on_path()
    try:
        result = _run_shadow_body(
            run_id=run_id,
            staging=staging,
            client_override=client_override,
            settings=cfg,
            started=started,
            started_iso=started_iso,
        )
    except Exception as exc:
        logger.exception("Hybrid shadow failed run_id=%s", run_id)
        result = _empty_result(
            run_id=run_id,
            staging=staging,
            settings=cfg,
            status=STATUS_ERROR,
            reason=type(exc).__name__,
            started=started,
            extra={"error_type": type(exc).__name__, "hybrid_started": True},
        )
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    if persist and cfg.mode != MODE_OFF:
        try:
            out = output_dir(staging)
            _dump(out / "hybrid_shadow_report.json", result)
            _dump(
                out / "hybrid_shadow_summary.json",
                {
                    k: result.get(k)
                    for k in (
                        "run_id",
                        "hybrid_mode",
                        "hybrid_status",
                        "reason",
                        "request_count",
                        "cache_hits",
                        "input_tokens",
                        "output_tokens",
                        "estimated_cost_usd",
                        "cost_basis",
                        "hybrid_latency_s",
                        "agreement_counts",
                        "excel_fingerprint",
                        "steel_fingerprint",
                    )
                },
            )
        except Exception:
            logger.exception("Hybrid shadow persist failed run_id=%s", run_id)
    excel_after = _excel_fingerprint(staging)
    before = result.get("excel_fingerprint") or {}
    excel_absent = not before.get("present") and not excel_after.get("present")
    result["excel_unchanged"] = (
        excel_absent
        or (
            before.get("present") is True
            and excel_after.get("present") is True
            and before.get("size_bytes") == excel_after.get("size_bytes")
            and before.get("mtime_ns") == excel_after.get("mtime_ns")
        )
        or cfg.mode == MODE_OFF
    )
    result["excel_fingerprint_after"] = excel_after
    if persist and cfg.mode != MODE_OFF:
        try:
            _dump(output_dir(staging) / "hybrid_shadow_report.json", result)
        except Exception:
            logger.exception("Hybrid shadow re-persist failed run_id=%s", run_id)
    return result


def _run_shadow_body(
    *,
    run_id: str,
    staging: Path,
    client_override: Optional[Callable],
    settings: HybridSettings,
    started: float,
    started_iso: str,
) -> Dict[str, Any]:
    if settings.mode == MODE_OFF:
        return _empty_result(
            run_id=run_id,
            staging=staging,
            settings=settings,
            status=STATUS_SKIPPED_OFF,
            reason="HYBRID_MODE_OFF",
            started=started,
            extra={"hybrid_started": False, "started_at": started_iso},
        )
    if settings.mode == MODE_AUTHORITATIVE:
        return _empty_result(
            run_id=run_id,
            staging=staging,
            settings=settings,
            status=STATUS_AUTHORITATIVE_FORBIDDEN,
            reason="AUTHORITATIVE_MODE_DISABLED_IN_W5",
            started=started,
            extra={"started_at": started_iso},
        )
    if settings.mode not in (MODE_SHADOW, MODE_PRODUCTION):
        return _empty_result(
            run_id=run_id,
            staging=staging,
            settings=settings,
            status=STATUS_SKIPPED_OFF,
            reason="HYBRID_MODE_UNRECOGNIZED",
            started=started,
        )

    catalog = load_r13_catalog(staging)
    if not catalog.get("ok"):
        return _empty_result(
            run_id=run_id,
            staging=staging,
            settings=settings,
            status=STATUS_NO_ENGINEERING,
            reason=str(catalog.get("reason") or "R13_UNAVAILABLE"),
            started=started,
            extra={"started_at": started_iso, "catalog": {"ok": False, "reason": catalog.get("reason")}},
        )

    beam_ids: List[str] = list(catalog.get("beam_ids") or [])
    visual = discover_visuals(staging, beam_ids=beam_ids)
    key_status = settings.api_key_status
    live_ok = settings.live_calls_allowed or client_override is not None
    if not live_ok and client_override is None and key_status != "PRESENT":
        status_if_no_calls = STATUS_KEY_ABSENT
        key_reason = "ANTHROPIC_API_KEY_ABSENT" if key_status == "ABSENT" else "ANTHROPIC_API_KEY_EMPTY"
    else:
        status_if_no_calls = None
        key_reason = None

    observations: List[Dict[str, Any]] = []
    request_count = 0
    cache_hits = 0
    input_tokens = 0
    output_tokens = 0
    timeout_count = 0
    seen_calls: Dict[str, Dict[str, Any]] = {}
    budget_hit = False
    deadline = None
    if float(settings.max_wall_s) > 0:
        deadline = started + float(settings.max_wall_s)
    vision_attempts = max(1, int(getattr(settings, "max_retries", 1) or 0) + 1)
    beam_budget = float(getattr(settings, "total_beam_timeout_s", 0) or 0)
    per_call = float(settings.per_call_timeout_s or 0)
    total_n = len(beam_ids)
    consecutive_rate_limit = 0
    rate_limit_cooldown_used = False

    models = catalog.get("by_id") or {}
    for beam_id in beam_ids:
        vis = (visual.get("by_id") or {}).get(beam_id) or {}
        model = models.get(beam_id) if isinstance(models.get(beam_id), dict) else None
        context_path = vis.get("context_path") or vis.get("path")
        detail_path = vis.get("detail_path") or vis.get("path")
        row: Dict[str, Any] = {
            "run_id": run_id,
            "beam_id": beam_id,
            "hybrid_mode": settings.mode,
            "visual_available": bool(vis.get("available")),
            "visual_reason": vis.get("reason"),
            "visual_path": vis.get("path"),
            "visual_source": vis.get("source"),
            "context_path": context_path,
            "detail_path": detail_path,
            "context_source": vis.get("context_source") or vis.get("source"),
            "detail_source": vis.get("detail_source") or vis.get("source"),
            "evidence_class": vis.get("evidence_class"),
            "fallback_status": vis.get("fallback_status"),
            "fallback_reason": vis.get("fallback_reason"),
            "evidence_manifest": vis.get("evidence_manifest"),
            "called": False,
            "cache_hit": False,
            "hybrid_status": HYBRID_UNAVAILABLE,
        }
        if deadline is not None and time.perf_counter() >= deadline:
            budget_hit = True
            row["hybrid_status"] = HYBRID_UNAVAILABLE
            row["skip_reason"] = "WALL_CLOCK_BUDGET"
            row["comparison"] = classify_beam(
                beam_id=beam_id, hybrid=None, status=HYBRID_UNAVAILABLE
            )
            observations.append(row)
            continue
        if not vis.get("available"):
            row["skip_reason"] = vis.get("reason") or "EVIDENCE_UNAVAILABLE"
            row["comparison"] = classify_beam(
                beam_id=beam_id, hybrid=None, status=HYBRID_UNAVAILABLE
            )
            observations.append(row)
            continue
        if not live_ok:
            row["skip_reason"] = key_reason or "LIVE_DISABLED"
            row["hybrid_status"] = HYBRID_UNAVAILABLE
            row["comparison"] = classify_beam(
                beam_id=beam_id, hybrid=None, status=HYBRID_UNAVAILABLE
            )
            observations.append(row)
            continue
        if settings.max_live_calls > 0 and request_count >= settings.max_live_calls:
            budget_hit = True
            row["skip_reason"] = "PER_RUN_REQUEST_LIMIT"
            row["comparison"] = classify_beam(
                beam_id=beam_id, hybrid=None, status=HYBRID_UNAVAILABLE
            )
            observations.append(row)
            continue

        cache_key = f"{beam_id}|{context_path}|{detail_path}|{vis.get('bytes')}"
        live: Optional[Dict[str, Any]] = None
        if cache_key in seen_calls:
            live = seen_calls[cache_key]
            cache_hits += 1
            row["cache_hit"] = True
            row["called"] = False
        else:
            write_progress(
                staging,
                run_id=run_id,
                phase=PHASE_VISION,
                beam_id=beam_id,
                index=len(observations) + 1,
                total=total_n,
                started_at=started_iso,
            )
            claude_started = datetime.now(timezone.utc).isoformat()
            claude_t0 = time.perf_counter()
            row["claude_started_at"] = claude_started
            row["attempt_number"] = 1
            try:

                def _invoke(
                    bid=beam_id,
                    ctxp=context_path,
                    detp=detail_path,
                    vis_local=vis,
                ):
                    return call_shadow_beam(
                        version10_root=ENGINE_ROOT,
                        beam_id=bid,
                        render_path=Path(ctxp or vis_local["path"]),
                        context_path=Path(ctxp) if ctxp else None,
                        detail_path=Path(detp) if detp else None,
                        context_source=str(
                            vis_local.get("context_source")
                            or vis_local.get("source")
                            or "W8_EVIDENCE"
                        ),
                        detail_source=str(
                            vis_local.get("detail_source")
                            or vis_local.get("source")
                            or "W8_EVIDENCE"
                        ),
                        client_override=client_override,
                        timeout_s=per_call if per_call > 0 else None,
                        max_attempts=vision_attempts,
                        max_api_attempts=vision_attempts,
                    )

                live = run_with_timeout(_invoke, beam_budget)
                request_count += 1
                row["called"] = True
                seen_calls[cache_key] = live
            except (TimeoutExpired, TimeoutError) as exc:
                timeout_count += 1
                logger.warning(
                    "Hybrid live call timed out run_id=%s beam_id=%s error_type=%s",
                    run_id,
                    beam_id,
                    type(exc).__name__,
                )
                write_progress(
                    staging,
                    run_id=run_id,
                    phase=PHASE_FALLBACK,
                    beam_id=beam_id,
                    index=len(observations) + 1,
                    total=total_n,
                    extra="Vision call timed out — continuing with deterministic fallback...",
                    started_at=started_iso,
                )
                row["hybrid_status"] = HYBRID_UNAVAILABLE
                row["error_type"] = type(exc).__name__
                row["skip_reason"] = STATUS_VISION_TIMEOUT
                row["timeout_status"] = STATUS_VISION_TIMEOUT
                row["claude_ended_at"] = datetime.now(timezone.utc).isoformat()
                row["claude_duration_s"] = round(time.perf_counter() - claude_t0, 3)
                row["comparison"] = classify_beam(
                    beam_id=beam_id,
                    hybrid=None,
                    status=HYBRID_UNAVAILABLE,
                    error=STATUS_VISION_TIMEOUT,
                )
                observations.append(row)
                continue
            except Exception as exc:
                logger.warning(
                    "Hybrid live call failed run_id=%s beam_id=%s error_type=%s",
                    run_id,
                    beam_id,
                    type(exc).__name__,
                )
                row["hybrid_status"] = HYBRID_ERROR
                row["error_type"] = type(exc).__name__
                row["skip_reason"] = "LIVE_CALL_EXCEPTION"
                row["claude_ended_at"] = datetime.now(timezone.utc).isoformat()
                row["claude_duration_s"] = round(time.perf_counter() - claude_t0, 3)
                row["comparison"] = classify_beam(
                    beam_id=beam_id,
                    hybrid=None,
                    status=HYBRID_ERROR,
                    error=type(exc).__name__,
                )
                observations.append(row)
                continue
            row["claude_ended_at"] = datetime.now(timezone.utc).isoformat()
            row["claude_duration_s"] = round(time.perf_counter() - claude_t0, 3)
            row["retry_count"] = (live or {}).get("retry_count")
            row["timeout_status"] = None

        audit = (live or {}).get("audit") if isinstance(live, dict) else None
        usage_payload = dict(audit) if isinstance(audit, dict) else {}
        if isinstance(live, dict) and live.get("usage"):
            usage_payload["usage"] = live.get("usage")
        usage = usage_from_audit(usage_payload)
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
        row["model"] = (live or {}).get("model") or usage.get("model")
        latency = usage.get("latency_s")
        if latency is None and isinstance(audit, dict):
            latency = audit.get("latency_s")
        row["usage"] = {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "estimated_cost_usd": usage.get("estimated_cost_usd"),
            "cost_basis": usage.get("cost_basis"),
            "latency_s": latency,
        }
        row["failure_category"] = (live or {}).get("failure_category")
        row["attempts"] = (live or {}).get("attempts")
        _copy_live_diagnostics(row, live if isinstance(live, dict) else None)
        semantic_usable = bool((live or {}).get("semantic_usable"))
        vision_row = None
        if semantic_usable and isinstance(live, dict):
            vision_row = {
                "usable": True,
                "source": "W5_SHADOW_LIVE" if row.get("called") else "W5_SHADOW_CACHE",
                "extracted": live.get("extracted"),
                "parsed": live.get("parsed"),
            }
        try:
            resolved = resolve_semantic(
                beam_id=beam_id,
                model=model,
                vision_row=vision_row,
                provenance={
                    "kind": "HYBRID" if vision_row else "FALLBACK",
                    "vision_used": bool(vision_row),
                    "mode": (
                        "PRODUCTION_AUTHORITY"
                        if settings.mode == MODE_PRODUCTION
                        else "PRODUCTION_SHADOW"
                    ),
                    "failure_category": (live or {}).get("failure_category"),
                },
            )
            hybrid = resolved.get("hybrid_semantic")
            row["hybrid_semantic"] = hybrid if isinstance(hybrid, dict) else None
            if vision_row:
                row["hybrid_status"] = "OBSERVED"
            else:
                row["hybrid_status"] = HYBRID_UNAVAILABLE
                row["skip_reason"] = row.get("failure_category") or "VISION_UNUSABLE"
            row["hybrid_interpretation"] = _interpretation_view(hybrid if isinstance(hybrid, dict) else {})
            row["confidence"] = _confidence_view(hybrid if isinstance(hybrid, dict) else {})
            row["comparison"] = classify_beam(
                beam_id=beam_id,
                hybrid=hybrid if isinstance(hybrid, dict) else None,
                status=HYBRID_UNAVAILABLE if not vision_row else "OBSERVED",
            )
            if not vision_row:
                row["comparison"]["agreement_classification"] = HYBRID_UNAVAILABLE
        except Exception as exc:
            logger.warning(
                "Hybrid semantic resolve failed run_id=%s beam_id=%s error_type=%s",
                run_id,
                beam_id,
                type(exc).__name__,
            )
            row["hybrid_status"] = HYBRID_ERROR
            row["error_type"] = type(exc).__name__
            row["comparison"] = classify_beam(
                beam_id=beam_id,
                hybrid=None,
                status=HYBRID_ERROR,
                error=type(exc).__name__,
            )
        if row.get("hybrid_status") == "OBSERVED":
            consecutive_rate_limit = 0
        elif (
            str(row.get("failure_category") or "") == "API_FAILED"
            and _looks_like_rate_limit(row, live if isinstance(live, dict) else None)
        ):
            consecutive_rate_limit += 1
            if consecutive_rate_limit >= 3 and not rate_limit_cooldown_used:
                logger.warning(
                    "Hybrid rate-limit cooldown run_id=%s beam_id=%s",
                    run_id,
                    beam_id,
                )
                time.sleep(30)
                rate_limit_cooldown_used = True
                consecutive_rate_limit = 0
        observations.append(row)

    cost = estimate_cost_usd(input_tokens=input_tokens, output_tokens=output_tokens)
    comparisons = [o.get("comparison") or {} for o in observations]
    counts = summarize_classifications(comparisons)
    if status_if_no_calls and request_count == 0:
        hybrid_status = status_if_no_calls
        reason = key_reason or "HYBRID_UNAVAILABLE"
    elif budget_hit:
        hybrid_status = STATUS_PARTIAL_BUDGET
        reason = "REQUEST_OR_WALL_BUDGET"
    elif any(o.get("hybrid_status") == HYBRID_ERROR for o in observations):
        hybrid_status = STATUS_ERROR if all(o.get("hybrid_status") == HYBRID_ERROR for o in observations) else STATUS_COMPLETE
        reason = "SOME_BEAMS_ERRORED"
    else:
        hybrid_status = STATUS_COMPLETE
        reason = (
            "PRODUCTION_COMPLETE"
            if settings.mode == MODE_PRODUCTION
            else "SHADOW_COMPLETE"
        )

    elapsed = round(time.perf_counter() - started, 3)
    return {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "gate_version": GATE_VERSION,
        "run_id": run_id,
        "hybrid_mode": settings.mode,
        "hybrid_started": True,
        "hybrid_completed": True,
        "hybrid_status": hybrid_status,
        "reason": reason,
        "started_at": started_iso,
        "production_write": PRODUCTION_WRITE,
        "authoritative_enabled": False,
        "settings": settings.public_dict(),
        "catalog_ok": True,
        "beam_count": len(beam_ids),
        "visual_available_count": visual.get("available_count"),
        "request_count": request_count,
        "cache_hits": cache_hits,
        "input_tokens": cost["input_tokens"],
        "output_tokens": cost["output_tokens"],
        "estimated_cost_usd": cost["estimated_cost_usd"],
        "cost_basis": cost["cost_basis"],
        "hybrid_latency_s": elapsed,
        "timeout": budget_hit or timeout_count > 0,
        "timeout_count": timeout_count,
        "error_classification": reason if hybrid_status in (STATUS_ERROR, STATUS_KEY_ABSENT) else None,
        "agreement_counts": counts,
        "excel_fingerprint": _excel_fingerprint(staging),
        "steel_fingerprint": load_steel_fingerprint(staging),
        "provider": "anthropic",
        "model": next((o.get("model") for o in observations if o.get("model")), settings.model_override),
        "beams": observations,
    }


def _interpretation_view(hybrid: Dict[str, Any]) -> Dict[str, Any]:
    groups = []
    for group in hybrid.get("reinforcement_groups") or []:
        if not isinstance(group, dict):
            continue
        groups.append(
            {
                "group_id": group.get("group_id"),
                "origin": group.get("origin"),
                "layer": (group.get("layer") or {}).get("value"),
                "bar_count": (group.get("bar_count") or {}).get("value"),
                "diameter": (group.get("diameter") or {}).get("value"),
                "specification": (group.get("specification") or {}).get("value"),
                "main_extra": (group.get("role") or {}).get("value"),
                "support_scope": (group.get("support_scope") or {}).get("value"),
            }
        )
    stirrups = hybrid.get("stirrups") or {}
    items = stirrups.get("items") if isinstance(stirrups, dict) else []
    stirrup_specs = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        ident = item.get("semantic_identification") or {}
        stirrup_specs.append(
            {
                "origin": item.get("origin"),
                "specification": ident.get("value"),
            }
        )
    target = hybrid.get("target_identity") or {}
    return {
        "target": target.get("value") or hybrid.get("beam_id"),
        "physical_groups": groups,
        "stirrup_visual_interpretation": stirrup_specs,
        "ambiguity_indicators": {
            "ambiguous_group_matches": (hybrid.get("group_matching") or {}).get("ambiguous"),
            "vision_only_groups": (hybrid.get("group_matching") or {}).get("vision_only"),
            "possible_duplicate_groups": hybrid.get("possible_duplicate_groups"),
        },
    }


def _confidence_view(hybrid: Dict[str, Any]) -> Dict[str, Any]:
    confs = []
    for group in hybrid.get("reinforcement_groups") or []:
        if not isinstance(group, dict):
            continue
        for name in ("layer", "bar_count", "diameter", "specification", "role", "support_scope"):
            rec = group.get(name) or {}
            if isinstance(rec, dict) and rec.get("confidence") is not None:
                try:
                    confs.append(float(rec.get("confidence")))
                except (TypeError, ValueError):
                    continue
    target = hybrid.get("target_identity") or {}
    return {
        "target_confidence": target.get("confidence") if isinstance(target, dict) else None,
        "group_confidence_count": len(confs),
        "group_confidence_min": min(confs) if confs else None,
        "group_confidence_max": max(confs) if confs else None,
    }


def public_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "hybrid_mode": result.get("hybrid_mode"),
        "hybrid_status": result.get("hybrid_status"),
        "reason": result.get("reason"),
        "request_count": result.get("request_count"),
        "cache_hits": result.get("cache_hits"),
        "hybrid_latency_s": result.get("hybrid_latency_s"),
        "estimated_cost_usd": result.get("estimated_cost_usd"),
        "cost_basis": result.get("cost_basis"),
        "agreement_counts": result.get("agreement_counts"),
        "excel_unchanged": result.get("excel_unchanged"),
        "beam_count": result.get("beam_count"),
        "visual_available_count": result.get("visual_available_count"),
    }
