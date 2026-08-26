"""Build a run-level Hybrid monitor from existing W.5/W.6/W.8 artefacts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PhaseW5_production_hybrid_shadow.config import (
    AGREE,
    BENIGN_DIFFERENCE,
    HYBRID_ERROR,
    HYBRID_UNAVAILABLE,
    MATERIAL_DISAGREEMENT,
    SEMANTIC_DISAGREEMENT,
)

from .config import (
    COST_ESTIMATED,
    COST_UNKNOWN,
    CROP_DECISION_NO_CHANGE,
    DETERMINISTIC_AGREEMENT,
    DUP_COMPATIBILITY_FALLBACK,
    DUP_DETAIL_NOT_AVAILABLE,
    DUP_HISTORICAL_LIMITED,
    DUP_NOT_DUPLICATE,
    DUP_OUTCOME_AMBIGUOUS,
    DUP_OUTCOME_FAILURE,
    DUP_OUTCOME_RELIABLE,
    DUP_OUTCOME_UNKNOWN,
    DUP_RENDERING_GAP,
    DUP_SELECTION_LIMITATION,
    DUP_UNKNOWN,
    EVIDENCE_REL,
    EXCEL_REL,
    GATE_VERSION,
    GEOM_KEYS,
    HISTORICAL_LIMITED,
    MATERIAL_DISAGREEMENT as W10_MATERIAL,
    NOT_RECORDED,
    PHASE_ID,
    PHASE_NAME,
    PRE_HYBRID_REL,
    PROTECTED_KEYS,
    R13_REL,
    SEMANTIC_CORRECTION,
    SEMANTIC_REINFORCEMENT,
    STEEL_REL,
    UNAVAILABLE_OR_FALLBACK,
    W5_REL,
    W6_REL,
)

_SEMANTIC_MAP = {
    AGREE: DETERMINISTIC_AGREEMENT,
    BENIGN_DIFFERENCE: SEMANTIC_REINFORCEMENT,
    SEMANTIC_DISAGREEMENT: SEMANTIC_CORRECTION,
    MATERIAL_DISAGREEMENT: W10_MATERIAL,
    HYBRID_UNAVAILABLE: UNAVAILABLE_OR_FALLBACK,
    HYBRID_ERROR: UNAVAILABLE_OR_FALLBACK,
}


def _load(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sha(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _bar_maps(model: dict) -> dict:
    out = {}
    for key in (
        "top_main_bars",
        "top_extra_bars",
        "bottom_main_bars",
        "bottom_extra_bars",
        "stirrups",
        "spacer_bars",
        "side_face_reinforcement",
    ):
        for bar in model.get(key) or []:
            if isinstance(bar, dict) and bar.get("bar_id"):
                out[(key, bar.get("bar_id"))] = bar
    return out


def engineering_overwrites(staging: Path) -> Dict[str, int]:
    pre = _load(Path(staging) / PRE_HYBRID_REL)
    post = _load(Path(staging) / R13_REL)
    cut = 0
    geom = 0
    stirrup_qty = 0
    if not isinstance(pre, dict) or not isinstance(post, dict):
        return {
            "cut_length_overwrites": 0,
            "geometry_overwrites": 0,
            "stirrup_quantity_overwrites": 0,
            "deterministic_engineering_overwrite_count": 0,
            "pre_hybrid_present": isinstance(pre, dict),
            "post_hybrid_present": isinstance(post, dict),
        }
    pre_models = {m.get("beam_id"): m for m in (pre.get("models") or []) if isinstance(m, dict)}
    for model in post.get("models") or []:
        if not isinstance(model, dict):
            continue
        old = pre_models.get(model.get("beam_id")) or {}
        old_bars = _bar_maps(old)
        new_bars = _bar_maps(model)
        for ident, bar in new_bars.items():
            prev = old_bars.get(ident) or {}
            for key in PROTECTED_KEYS:
                if key == "geometry":
                    continue
                if key in bar and key in prev and bar.get(key) != prev.get(key):
                    if str(key).startswith("cut_length"):
                        cut += 1
            if ident[0] == "stirrups" and "quantity" in bar and "quantity" in prev:
                if bar.get("quantity") != prev.get("quantity"):
                    stirrup_qty += 1
        old_geom = old.get("geometry") if isinstance(old.get("geometry"), dict) else {}
        new_geom = model.get("geometry") if isinstance(model.get("geometry"), dict) else {}
        if old_geom and new_geom and old_geom != new_geom:
            geom += 1
        for gkey in GEOM_KEYS:
            if gkey in model and gkey in old and model.get(gkey) != old.get(gkey):
                geom += 1
    return {
        "cut_length_overwrites": cut,
        "geometry_overwrites": geom,
        "stirrup_quantity_overwrites": stirrup_qty,
        "deterministic_engineering_overwrite_count": cut + geom + stirrup_qty,
        "pre_hybrid_present": True,
        "post_hybrid_present": True,
    }


def map_semantic(cls: Optional[str]) -> str:
    if not cls:
        return UNAVAILABLE_OR_FALLBACK
    return _SEMANTIC_MAP.get(str(cls), UNAVAILABLE_OR_FALLBACK)


def _duplicate_reason(
    *,
    same: bool,
    evidence_class: str,
    visual_source: str,
    ctx_exists: bool,
    det_exists: bool,
    historical: bool,
) -> str:
    if historical:
        return DUP_HISTORICAL_LIMITED
    if not same:
        return DUP_NOT_DUPLICATE
    if not det_exists or not ctx_exists:
        return DUP_DETAIL_NOT_AVAILABLE
    cls = (evidence_class or "").upper()
    src = (visual_source or "").upper()
    if cls in ("FALLBACK", "COMPATIBILITY") or "W6" in src or "ENVELOPE" in src:
        return DUP_COMPATIBILITY_FALLBACK
    if cls == "PRIMARY":
        return DUP_RENDERING_GAP
    if "T1" in src:
        return DUP_SELECTION_LIMITATION
    return DUP_UNKNOWN


def _duplicate_outcome(*, same: bool, hybrid_status: str, called: bool) -> str:
    if not same:
        return DUP_NOT_DUPLICATE
    status = str(hybrid_status or "")
    if status == "OBSERVED":
        return DUP_OUTCOME_RELIABLE
    if status in (HYBRID_ERROR, "HYBRID_ERROR"):
        return DUP_OUTCOME_FAILURE
    if not called:
        return DUP_OUTCOME_UNKNOWN
    return DUP_OUTCOME_AMBIGUOUS


def _crop_decision(reviews: List[Dict[str, Any]], coverage: Dict[str, Any]) -> Dict[str, Any]:
    unexplained = int(coverage.get("unexplained") or 0)
    unavailable = int(coverage.get("visual_context_unavailable") or coverage.get("evidence_unavailable") or 0)
    dups = [r for r in reviews if r.get("images_distinct") is False]
    failed_dups = [r for r in dups if r.get("duplicate_outcome") == DUP_OUTCOME_FAILURE]
    if unexplained > 0 or unavailable > 0 or failed_dups:
        return {
            "decision": "REVIEW_REQUIRED",
            "reason": "unexplained_or_unavailable_or_failed_duplicate",
            "unexplained": unexplained,
            "unavailable": unavailable,
            "failed_duplicate_count": len(failed_dups),
        }
    return {
        "decision": CROP_DECISION_NO_CHANGE,
        "reason": (
            "Fallbacks and duplicate-image cases are explicit, logged, and still "
            "resolved by Hybrid. No silent gap. No crop rewrite."
        ),
        "unexplained": unexplained,
        "unavailable": unavailable,
        "duplicate_count": len(dups),
        "reliable_duplicate_count": sum(
            1 for r in dups if r.get("duplicate_outcome") == DUP_OUTCOME_RELIABLE
        ),
    }


def build_beam_reviews(
    *,
    staging: Path,
    coverage: Dict[str, Any],
    shadow: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool]:
    staging = Path(staging)
    evidence_root = staging / EVIDENCE_REL
    historical = not evidence_root.is_dir()
    shadow_by = {}
    if isinstance(shadow, dict):
        for row in shadow.get("beams") or []:
            if isinstance(row, dict) and row.get("beam_id"):
                shadow_by[str(row["beam_id"])] = row
    cov_by = {}
    for row in coverage.get("beams") or []:
        if isinstance(row, dict) and row.get("beam_id"):
            cov_by[str(row["beam_id"])] = row

    beam_ids = [str(b.get("beam_id")) for b in (coverage.get("beams") or []) if b.get("beam_id")]
    if not beam_ids:
        beam_ids = list(shadow_by.keys())

    reviews: List[Dict[str, Any]] = []
    for bid in beam_ids:
        man_path = evidence_root / bid / "evidence_manifest.json"
        man = _load(man_path) if man_path.is_file() else None
        man = man if isinstance(man, dict) else {}
        ctx = evidence_root / bid / "context" / "selected.png"
        det = evidence_root / bid / "detail" / "selected.png"
        ctx_sha = _sha(ctx)
        det_sha = _sha(det)
        same = bool(ctx_sha and det_sha and ctx_sha == det_sha)
        cov = cov_by.get(bid) or {}
        sh = shadow_by.get(bid) or {}
        evidence_class = (
            man.get("evidence_class")
            or cov.get("evidence_class")
            or sh.get("evidence_class")
            or (HISTORICAL_LIMITED if historical else "UNKNOWN")
        )
        visual_source = (
            man.get("visual_source")
            or cov.get("visual_source")
            or sh.get("visual_source")
        )
        hybrid_status = sh.get("hybrid_status") or cov.get("hybrid_status")
        comparison = sh.get("comparison") if isinstance(sh.get("comparison"), dict) else {}
        w5_cls = comparison.get("agreement_classification")
        reviews.append(
            {
                "beam_id": bid,
                "evidence_source": visual_source,
                "selection_classification": evidence_class,
                "context_image_provenance": str(ctx) if ctx.is_file() else (sh.get("context_path") or NOT_RECORDED),
                "detail_image_provenance": str(det) if det.is_file() else (sh.get("detail_path") or NOT_RECORDED),
                "context_source_phase": (man.get("selected_context_evidence") or {}).get("source_phase")
                or sh.get("context_source"),
                "detail_source_phase": (man.get("selected_detail_evidence") or {}).get("source_phase")
                or sh.get("detail_source"),
                "context_sha": ctx_sha,
                "detail_sha": det_sha,
                "images_distinct": (None if historical and not ctx_sha else (not same if ctx_sha and det_sha else None)),
                "c3_status": man.get("completeness_status") or man.get("c3_status") or NOT_RECORDED,
                "fallback_status": man.get("fallback_status") or sh.get("fallback_status") or cov.get("fallback_status"),
                "fallback_reason": man.get("fallback_reason") or sh.get("fallback_reason") or cov.get("skip_reason"),
                "vision_invocation_status": "CALLED" if sh.get("called") else ("CACHE" if sh.get("cache_hit") else "NOT_CALLED"),
                "hybrid_resolution_status": hybrid_status,
                "deterministic_comparison_classification": map_semantic(w5_cls),
                "w5_agreement_classification": w5_cls or NOT_RECORDED,
                "duplicate_reason": _duplicate_reason(
                    same=same,
                    evidence_class=str(evidence_class or ""),
                    visual_source=str(visual_source or ""),
                    ctx_exists=ctx.is_file() or bool(sh.get("context_path")),
                    det_exists=det.is_file() or bool(sh.get("detail_path")),
                    historical=historical and not ctx_sha,
                ),
                "duplicate_outcome": _duplicate_outcome(
                    same=same,
                    hybrid_status=str(hybrid_status or ""),
                    called=bool(sh.get("called")),
                ),
                "n_images": 2 if (ctx.is_file() and det.is_file()) or (sh.get("context_path") and sh.get("detail_path")) else NOT_RECORDED,
                "usage": {
                    "latency_s": ((sh.get("usage") or {}) if isinstance(sh.get("usage"), dict) else {}).get("latency_s"),
                    "input_tokens": ((sh.get("usage") or {}) if isinstance(sh.get("usage"), dict) else {}).get("input_tokens"),
                    "output_tokens": ((sh.get("usage") or {}) if isinstance(sh.get("usage"), dict) else {}).get("output_tokens"),
                    "cost_basis": ((sh.get("usage") or {}) if isinstance(sh.get("usage"), dict) else {}).get("cost_basis"),
                },
                "historical_observability": HISTORICAL_LIMITED if historical else None,
            }
        )
    return reviews, historical


def build_monitor(
    staging: Path,
    *,
    run_id: Optional[str] = None,
    live_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    staging = Path(staging)
    rid = run_id or staging.name
    coverage = _load(staging / W6_REL / "hybrid_coverage.json") or {}
    observability = _load(staging / W6_REL / "hybrid_observability.json") or {}
    shadow = _load(staging / W5_REL / "hybrid_shadow_report.json")
    steel = _load(staging / STEEL_REL) or {}
    live_result = live_result if isinstance(live_result, dict) else {}
    if not coverage:
        coverage = (observability.get("coverage") if isinstance(observability, dict) else None) or {}
    if not coverage and isinstance(shadow, dict):
        coverage = {"hybrid_eligible": shadow.get("beam_count"), "unexplained": None}

    reviews, historical = build_beam_reviews(staging=staging, coverage=coverage, shadow=shadow)
    semantic_counts = {
        DETERMINISTIC_AGREEMENT: 0,
        SEMANTIC_REINFORCEMENT: 0,
        SEMANTIC_CORRECTION: 0,
        W10_MATERIAL: 0,
        UNAVAILABLE_OR_FALLBACK: 0,
    }
    for row in reviews:
        key = str(row.get("deterministic_comparison_classification") or UNAVAILABLE_OR_FALLBACK)
        if key not in semantic_counts:
            semantic_counts[key] = 0
        semantic_counts[key] += 1

    latencies = []
    for row in reviews:
        raw = (row.get("usage") or {}).get("latency_s")
        try:
            if raw is not None and str(raw) not in ("", "NOT_RECORDED"):
                latencies.append(float(raw))
        except (TypeError, ValueError):
            continue
    vision_duration = round(sum(latencies), 3) if latencies else NOT_RECORDED
    avg_vision = round(sum(latencies) / len(latencies), 3) if latencies else NOT_RECORDED

    input_tokens = None
    output_tokens = None
    estimated_cost = None
    cost_basis = COST_UNKNOWN
    if isinstance(shadow, dict):
        try:
            input_tokens = int(shadow.get("input_tokens") or 0)
            output_tokens = int(shadow.get("output_tokens") or 0)
            estimated_cost = shadow.get("estimated_cost_usd")
            raw_basis = str(shadow.get("cost_basis") or "")
            if raw_basis.upper() == COST_ESTIMATED or estimated_cost is not None:
                cost_basis = COST_ESTIMATED
            elif input_tokens or output_tokens:
                cost_basis = COST_ESTIMATED
            else:
                cost_basis = COST_UNKNOWN
        except (TypeError, ValueError):
            cost_basis = COST_UNKNOWN

    dups = [r for r in reviews if r.get("images_distinct") is False]
    excel = staging / EXCEL_REL
    identity_ok = coverage.get("identity_ok")
    if identity_ok is None and coverage.get("hybrid_eligible") is not None:
        identity_ok = HISTORICAL_LIMITED if historical and coverage.get("p2610_primary_evidence") is None else None

    evidence_duration = NOT_RECORDED
    prep = observability.get("visual_prep") if isinstance(observability, dict) else None
    if isinstance(prep, dict) and prep.get("evidence_generation_duration_s") is not None:
        evidence_duration = prep.get("evidence_generation_duration_s")
    elif live_result.get("evidence_generation_duration_s") is not None:
        evidence_duration = live_result.get("evidence_generation_duration_s")

    return {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "gate_version": GATE_VERSION,
        "run_id": rid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hybrid_mode": observability.get("hybrid_mode") or live_result.get("hybrid_mode") or NOT_RECORDED,
        "model": observability.get("model") or (shadow.get("model") if isinstance(shadow, dict) else None),
        "observability_status": HISTORICAL_LIMITED if historical else "W8_EVIDENCE_PRESENT",
        "total_beams": coverage.get("total_production_beams")
        or coverage.get("hybrid_eligible")
        or (shadow.get("beam_count") if isinstance(shadow, dict) else NOT_RECORDED),
        "hybrid_eligible": coverage.get("hybrid_eligible") or NOT_RECORDED,
        "primary_evidence_count": coverage.get("p2610_primary_evidence")
        if "p2610_primary_evidence" in coverage
        else (HISTORICAL_LIMITED if historical else NOT_RECORDED),
        "native_t1_evidence_count": coverage.get("native_t1_crop")
        if "native_t1_crop" in coverage
        else NOT_RECORDED,
        "compatibility_fallback_count": coverage.get("generated_fallback_crop")
        if "generated_fallback_crop" in coverage
        else coverage.get("fallback_path", NOT_RECORDED),
        "deterministic_fallback_count": coverage.get("deterministic_fallback")
        if "deterministic_fallback" in coverage
        else (observability.get("deterministic_fallback_usage") or 0),
        "unavailable_count": coverage.get("visual_context_unavailable")
        if "visual_context_unavailable" in coverage
        else coverage.get("evidence_unavailable", NOT_RECORDED),
        "unexplained_count": coverage.get("unexplained")
        if "unexplained" in coverage
        else HISTORICAL_LIMITED,
        "identity_ok": identity_ok,
        "claude_attempted": coverage.get("claude_attempted")
        or observability.get("claude_invocation_count")
        or (shadow.get("request_count") if isinstance(shadow, dict) else NOT_RECORDED),
        "claude_successful": coverage.get("claude_success")
        or observability.get("successful_invocation_count"),
        "claude_failed": coverage.get("claude_failure")
        or observability.get("failed_invocation_count"),
        "timeout_count": observability.get("timeout_count"),
        "fallback_calls": observability.get("fallback_count"),
        "vision_duration_s": vision_duration,
        "average_vision_duration_s": avg_vision,
        "hybrid_duration_s": observability.get("hybrid_latency_s")
        or (shadow.get("hybrid_latency_s") if isinstance(shadow, dict) else NOT_RECORDED),
        "evidence_generation_duration_s": evidence_duration,
        "pipeline_duration_s": live_result.get("pipeline_duration_s") or NOT_RECORDED,
        "semantic_agreement_count": semantic_counts[DETERMINISTIC_AGREEMENT],
        "semantic_reinforcement_count": semantic_counts[SEMANTIC_REINFORCEMENT],
        "semantic_correction_count": semantic_counts[SEMANTIC_CORRECTION],
        "material_disagreement_count": semantic_counts[W10_MATERIAL],
        "deterministic_fallback_resolution_count": semantic_counts[UNAVAILABLE_OR_FALLBACK],
        "semantic_counts": semantic_counts,
        "api_usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost,
            "cost_classification": cost_basis,
            "cost_basis_label": (
                "W.5 shadow estimate_cost_usd from recorded token usage; not billed exact"
                if cost_basis == COST_ESTIMATED
                else "no token usage recorded on this run"
            ),
        },
        "duplicate_image": {
            "same_sha_count": len(dups),
            "distinct_count": sum(1 for r in reviews if r.get("images_distinct") is True),
            "unknown_count": sum(1 for r in reviews if r.get("images_distinct") is None),
            "by_reason": _count_field(dups, "duplicate_reason"),
            "by_outcome": _count_field(dups, "duplicate_outcome"),
        },
        "steel": {
            "total_weight_kg": steel.get("total_weight_kg") if isinstance(steel, dict) else None,
            "total_beams": steel.get("total_beams") if isinstance(steel, dict) else None,
            "total_bars": steel.get("total_bars") if isinstance(steel, dict) else None,
            "calculation_method": steel.get("calculation_method") if isinstance(steel, dict) else None,
        },
        "excel_present": excel.is_file(),
        "engineering_protection": engineering_overwrites(staging),
        "crop_improvement": _crop_decision(reviews, coverage),
        "beam_review_count": len(reviews),
        "live_hybrid_classification": observability.get("classification") or live_result.get("classification"),
    }


def _count_field(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in rows:
        val = str(row.get(key) or "UNKNOWN")
        out[val] = out.get(val, 0) + 1
    return out
