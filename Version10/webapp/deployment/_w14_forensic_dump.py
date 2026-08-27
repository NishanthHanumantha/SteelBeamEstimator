#!/usr/bin/env python3
"""W.14 production forensic dump. Never prints secrets."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ENGINE = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10")
RUN = sys.argv[1] if len(sys.argv) > 1 else ""
STAGING = ENGINE / "data" / "web_runs" / RUN
SECRET_KEYS = ("api_key", "authorization", "sk-ant", "anthropic_api_key")


def _load(rel: str):
    path = STAGING / rel
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"_error": "unreadable", "path": rel}


def _scrub(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            lk = str(k).lower()
            if any(s in lk for s in SECRET_KEYS):
                out[k] = "[REDACTED]"
            else:
                out[k] = _scrub(v)
        return out
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, str) and "sk-ant-" in value.lower():
        return "[REDACTED]"
    return value


def _sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not RUN:
        print("USAGE _w14_forensic_dump.py <run_id>")
        return 2
    sys.path.insert(0, str(ENGINE / "src"))
    from PhaseW6_hybrid_production_authority.resolution_trace import reconstruct_from_staging
    from PhaseW10_hybrid_production_monitoring.monitor import engineering_overwrites

    trace = reconstruct_from_staging(STAGING, run_id=RUN)
    shadow = _load("data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json") or {}
    coverage = _load("data/output/PhaseW6_hybrid_semantic_resolution/hybrid_coverage.json") or {}
    obs = _load("data/output/PhaseW6_hybrid_semantic_resolution/hybrid_observability.json") or {}
    w10 = _load("data/output/PhaseW10_hybrid_production_monitoring/w10_monitor_report.json") or {}
    steel = _load("data/output/Production_Output/steel_weight_summary.json") or {}
    excel = STAGING / "data/output/Production_Output/Estimation_Output.xlsx"
    evidence_root = STAGING / "data/output/PhaseW8_production_vision_evidence"
    packages = []
    same_sha = 0
    distinct = 0
    p2610 = 0
    w6_fb = 0
    unavailable = 0
    for pkg in evidence_root.glob("**/evidence_package.json"):
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        packages.append(data)
        ctx = str(data.get("context_source") or data.get("context_path") or "")
        det = str(data.get("detail_source") or data.get("detail_path") or "")
        src = str(data.get("source") or data.get("visual_source") or data.get("provenance") or "")
        if "W6" in src or "compat" in src.lower() or "fallback" in src.lower():
            w6_fb += 1
        elif "P2.6.10" in src or "P2610" in src or "W8" in src:
            p2610 += 1
        csha = data.get("context_sha256") or data.get("sha256")
        dsha = data.get("detail_sha256")
        ctx_path = data.get("context_path")
        det_path = data.get("detail_path")
        if not csha and ctx_path:
            csha = _sha(Path(ctx_path)) if Path(str(ctx_path)).is_file() else None
        if not dsha and det_path:
            dsha = _sha(Path(det_path)) if Path(str(det_path)).is_file() else None
        if csha and dsha and csha == dsha:
            same_sha += 1
        elif csha and dsha:
            distinct += 1
        if not ctx and not det:
            unavailable += 1
    beams = [b for b in (shadow.get("beams") or []) if isinstance(b, dict)]
    visual_src = {}
    for b in beams:
        src = str(b.get("visual_source") or "UNKNOWN")
        visual_src[src] = visual_src.get(src, 0) + 1
        ctxp = b.get("context_path")
        detp = b.get("detail_path")
        if ctxp and detp and Path(str(ctxp)).is_file() and Path(str(detp)).is_file():
            cs = _sha(Path(str(ctxp)))
            ds = _sha(Path(str(detp)))
            if cs and ds and cs == ds:
                same_sha += 0  # counted via packages; keep beam-level below
    beam_same = 0
    beam_distinct = 0
    for b in beams:
        ctxp = b.get("context_path")
        detp = b.get("detail_path")
        if not ctxp or not detp:
            continue
        cp, dp = Path(str(ctxp)), Path(str(detp))
        if cp.is_file() and dp.is_file():
            cs, ds = _sha(cp), _sha(dp)
            if cs and ds and cs == ds:
                beam_same += 1
            elif cs and ds:
                beam_distinct += 1
    overwrites = engineering_overwrites(STAGING)
    payload = {
        "run_id": RUN,
        "lifecycle": trace.get("lifecycle_counts"),
        "identity_ok": trace.get("identity_ok"),
        "fallback_identity_ok": trace.get("fallback_identity_ok"),
        "reason_counts": trace.get("reason_counts"),
        "provider_category_counts": trace.get("provider_category_counts"),
        "api_recovery": trace.get("api_recovery"),
        "cost_summary": trace.get("cost_summary"),
        "unexplained": trace.get("unexplained"),
        "unresolved_beams": [
            {
                "beam_id": b.get("beam_id"),
                "final_status": b.get("final_status"),
                "reason_code": b.get("reason_code"),
                "provider_category": b.get("provider_category"),
                "http_status": b.get("http_status"),
                "api_error_excerpt": b.get("api_error_excerpt"),
                "retry_count": b.get("retry_count"),
                "timeout_flag": b.get("timeout_flag"),
                "skip_reason": b.get("skip_reason"),
                "failure_category": b.get("failure_category"),
            }
            for b in (trace.get("beams") or [])
            if b.get("final_status") != "HYBRID_RESOLVED"
        ],
        "coverage": _scrub(coverage),
        "observability_timing": {
            k: (obs.get(k) if isinstance(obs, dict) else None)
            for k in ("elapsed_s", "hybrid_elapsed_s", "visual_prep", "timing")
        },
        "w10": _scrub(w10) if isinstance(w10, dict) else w10,
        "steel": _scrub(steel) if isinstance(steel, dict) else steel,
        "overwrites": overwrites,
        "excel": {
            "present": excel.is_file(),
            "bytes": excel.stat().st_size if excel.is_file() else 0,
            "pk": excel.read_bytes()[:2] == b"PK" if excel.is_file() else False,
        },
        "evidence": {
            "package_files": len(packages),
            "visual_source_counts": visual_src,
            "beam_same_sha": beam_same,
            "beam_distinct_sha": beam_distinct,
            "shadow_visual_available": shadow.get("visual_available_count"),
            "shadow_request_count": shadow.get("request_count"),
            "shadow_elapsed_s": shadow.get("elapsed_s"),
        },
        "shadow_cost": {
            "input_tokens": shadow.get("input_tokens"),
            "output_tokens": shadow.get("output_tokens"),
            "estimated_cost_usd": shadow.get("estimated_cost_usd"),
            "cost_basis": shadow.get("cost_basis"),
            "elapsed_s": shadow.get("elapsed_s"),
            "started_at": shadow.get("started_at"),
            "hybrid_status": shadow.get("hybrid_status"),
            "reason": shadow.get("reason"),
        },
    }
    print(json.dumps(_scrub(payload), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
