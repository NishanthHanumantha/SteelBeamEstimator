#!/usr/bin/env python3
"""W.13 production forensic dump. No secrets."""
from pathlib import Path
import json

ENGINE = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10")
RUNS = ENGINE / "data/web_runs"
OUTS = ENGINE / "webapp/outputs"
LOG = ENGINE / "webapp/logs/webapp.log"

IDS = [
    "20260826_084708_f74912b8",
    "20260826_111142_32321cb4",
    "20260826_141507_88aff694",
]


def load(p: Path):
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": type(exc).__name__}


def summarize_hybrid(run_id: str) -> dict:
    root = RUNS / run_id
    obs = load(root / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_observability.json") or {}
    cov = (obs.get("coverage") or {}) if isinstance(obs, dict) else {}
    shadow = load(root / "data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json") or {}
    res = load(root / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_resolution.json") or {}
    handoff = load(root / "data/output/PhaseW6_hybrid_semantic_resolution/hybrid_handoff.json") or {}
    mon = load(root / "data/output/PhaseW10_hybrid_monitoring/hybrid_production_monitor.json") or {}
    beams = shadow.get("beams") if isinstance(shadow, dict) else None
    status_counts = {}
    skip_counts = {}
    fail_counts = {}
    called = 0
    semantic = 0
    if isinstance(beams, list):
        for b in beams:
            if not isinstance(b, dict):
                continue
            if b.get("called"):
                called += 1
            st = str(b.get("hybrid_status") or "NONE")
            status_counts[st] = status_counts.get(st, 0) + 1
            sk = str(b.get("skip_reason") or b.get("failure_category") or "")
            if sk:
                skip_counts[sk] = skip_counts.get(sk, 0) + 1
            fc = str(b.get("failure_category") or "")
            if fc:
                fail_counts[fc] = fail_counts.get(fc, 0) + 1
            if b.get("hybrid_status") == "OBSERVED":
                semantic += 1
        sample_unobs = [
            {
                "beam_id": b.get("beam_id"),
                "called": b.get("called"),
                "hybrid_status": b.get("hybrid_status"),
                "skip_reason": b.get("skip_reason"),
                "failure_category": b.get("failure_category"),
                "error_type": b.get("error_type"),
                "retry_count": b.get("retry_count"),
            }
            for b in beams
            if isinstance(b, dict) and b.get("hybrid_status") != "OBSERVED"
        ][:8]
        sample_obs = [
            {
                "beam_id": b.get("beam_id"),
                "called": b.get("called"),
                "hybrid_status": b.get("hybrid_status"),
                "failure_category": b.get("failure_category"),
            }
            for b in beams
            if isinstance(b, dict) and b.get("hybrid_status") == "OBSERVED"
        ][:5]
    else:
        sample_unobs = []
        sample_obs = []
    excel = OUTS / f"Estimation_Output_{run_id}.xlsx"
    man = load(root / "result_manifest.json") or {}
    return {
        "run_id": run_id,
        "excel_exists": excel.is_file(),
        "excel_size": excel.stat().st_size if excel.is_file() else 0,
        "manifest_lifecycle": man.get("lifecycle"),
        "manifest_download_attempts": man.get("download_attempts"),
        "manifest_last_download_ok": man.get("last_download_ok"),
        "obs_classification": obs.get("classification") if isinstance(obs, dict) else None,
        "obs_claude_invocation": obs.get("claude_invocation_count") if isinstance(obs, dict) else None,
        "obs_successful_invocation": obs.get("successful_invocation_count") if isinstance(obs, dict) else None,
        "obs_unresolved": obs.get("semantic_items_unresolved") if isinstance(obs, dict) else None,
        "obs_timeout": obs.get("timeout_count") if isinstance(obs, dict) else None,
        "obs_beams_patched": obs.get("beams_patched") if isinstance(obs, dict) else None,
        "coverage": {k: cov.get(k) for k in [
            "hybrid_eligible", "evidence_packages_generated", "claude_attempted",
            "claude_success", "claude_failure", "deterministic_fallback",
            "hybrid_resolved", "unresolved", "unexplained", "p2610_primary_evidence",
            "fallback_path", "evidence_unavailable",
        ]},
        "shadow_request_count": shadow.get("request_count") if isinstance(shadow, dict) else None,
        "shadow_beam_count": shadow.get("beam_count") if isinstance(shadow, dict) else None,
        "shadow_hybrid_status": shadow.get("hybrid_status") if isinstance(shadow, dict) else None,
        "shadow_reason": shadow.get("reason") if isinstance(shadow, dict) else None,
        "called_true": called,
        "observed": semantic,
        "status_counts": status_counts,
        "skip_counts": skip_counts,
        "fail_counts": fail_counts,
        "handoff_applied": handoff.get("applied") if isinstance(handoff, dict) else None,
        "handoff_reason": handoff.get("reason") if isinstance(handoff, dict) else None,
        "monitor_overwrites": (mon.get("engineering_protection") if isinstance(mon, dict) else None),
        "sample_unobserved": sample_unobs,
        "sample_observed": sample_obs,
        "shadow_beam_len": len(beams) if isinstance(beams, list) else None,
    }


def main():
    for rid in IDS:
        print("====", rid)
        print(json.dumps(summarize_hybrid(rid), indent=2, default=str)[:8000])
    print("==== LOG_TAIL_DOWNLOAD")
    if LOG.is_file():
        lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        hits = [ln for ln in lines if "download" in ln.lower() or "88aff694" in ln or "Workbook" in ln]
        for ln in hits[-40:]:
            print(ln[:300])
    print("==== JOURNAL")


if __name__ == "__main__":
    main()
