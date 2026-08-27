#!/usr/bin/env python3
"""W.13 deep forensic dump. Never prints secrets."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ENGINE = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10")
RUNS = ENGINE / "data/web_runs"
OUTS = ENGINE / "webapp/outputs"
LOG = ENGINE / "webapp/logs/webapp.log"
NGINX = Path("/etc/nginx/sites-enabled")

IDS = [
    "20260826_084708_f74912b8",
    "20260826_111142_32321cb4",
    "20260826_141507_88aff694",
]
SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]+)|(ANTHROPIC_API_KEY\s*=\s*\S+)|(api[_-]?key\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def red(s: str) -> str:
    return SECRET_RE.sub("[REDACTED]", s)


def load(p: Path):
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def beam_keys(b: dict) -> list:
    return sorted(b.keys())


def duration_buckets(beams):
    buckets = Counter()
    for b in beams:
        d = b.get("claude_duration_s")
        if d is None:
            buckets["none"] += 1
        elif d < 3:
            buckets["lt3s"] += 1
        elif d < 8:
            buckets["3_8s"] += 1
        elif d < 20:
            buckets["8_20s"] += 1
        else:
            buckets["ge20s"] += 1
    return dict(buckets)


def inspect_run(run_id: str) -> dict:
    root = RUNS / run_id
    shadow = load(root / "data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json") or {}
    beams = shadow.get("beams") if isinstance(shadow, dict) else []
    beams = beams if isinstance(beams, list) else []
    settings = shadow.get("settings") if isinstance(shadow, dict) else {}
    first_fail = None
    first_ok = None
    last_ok = None
    sample_fail = None
    error_types = Counter()
    skip = Counter()
    failcat = Counter()
    tokens_zero = 0
    called = 0
    observed = 0
    for i, b in enumerate(beams):
        if not isinstance(b, dict):
            continue
        if b.get("called"):
            called += 1
        if b.get("hybrid_status") == "OBSERVED":
            observed += 1
            if first_ok is None:
                first_ok = i
            last_ok = i
        else:
            if first_fail is None:
                first_fail = i
            if sample_fail is None:
                sample_fail = {
                    k: b.get(k)
                    for k in (
                        "beam_id",
                        "called",
                        "hybrid_status",
                        "skip_reason",
                        "failure_category",
                        "error_type",
                        "retry_count",
                        "attempts",
                        "claude_duration_s",
                        "timeout_status",
                        "visual_available",
                        "evidence_class",
                        "context_path",
                        "detail_path",
                        "usage",
                        "model",
                    )
                }
                # persist any unexpected nested audit without secrets
                for extra in ("audit", "live", "api_error", "vision_error"):
                    if extra in b:
                        sample_fail[extra] = red(json.dumps(b[extra])[:800])
        et = str(b.get("error_type") or "")
        if et:
            error_types[et] += 1
        sk = str(b.get("skip_reason") or "")
        if sk:
            skip[sk] += 1
        fc = str(b.get("failure_category") or "")
        if fc:
            failcat[fc] += 1
        usage = b.get("usage") or {}
        if isinstance(usage, dict):
            inn = usage.get("input_tokens") or 0
            out = usage.get("output_tokens") or 0
            if b.get("called") and int(inn or 0) == 0 and int(out or 0) == 0:
                tokens_zero += 1
    man = load(root / "result_manifest.json") or {}
    excel = OUTS / f"Estimation_Output_{run_id}.xlsx"
    keyset = beam_keys(beams[0]) if beams and isinstance(beams[0], dict) else []
    return {
        "run_id": run_id,
        "settings": settings,
        "shadow_reason": shadow.get("reason"),
        "shadow_hybrid_status": shadow.get("hybrid_status"),
        "timeout_count": shadow.get("timeout_count"),
        "request_count": shadow.get("request_count"),
        "beam_count": len(beams),
        "called": called,
        "observed": observed,
        "first_observed_idx": first_ok,
        "last_observed_idx": last_ok,
        "first_unobserved_idx": first_fail,
        "duration_buckets": duration_buckets(beams),
        "skip": dict(skip),
        "failcat": dict(failcat),
        "error_types": dict(error_types),
        "called_zero_tokens": tokens_zero,
        "sample_fail": sample_fail,
        "beam_row_keys": keyset,
        "excel_exists": excel.is_file(),
        "excel_size": excel.stat().st_size if excel.is_file() else 0,
        "manifest": {
            "lifecycle": man.get("lifecycle"),
            "download_attempts": man.get("download_attempts"),
            "last_download_ok": man.get("last_download_ok"),
            "workbook_name": man.get("workbook_name") or man.get("filename"),
        },
    }


def scan_log() -> dict:
    if not LOG.is_file():
        return {"missing": True}
    lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    interesting = []
    types = Counter()
    for ln in lines:
        if any(
            tok in ln
            for tok in (
                "Claude vision failure",
                "Claude request failure",
                "error_type=",
                "RateLimit",
                "429",
                "download",
                "88aff694",
                "111142_32321cb4",
                "084708_f74912b8",
            )
        ):
            interesting.append(red(ln)[:400])
            m = re.search(r"error_type=(\S+)", ln)
            if m:
                types[m.group(1)] += 1
    return {
        "hits": len(interesting),
        "error_types": dict(types),
        "tail": interesting[-60:],
    }


def nginx_static() -> str:
    chunks = []
    if not NGINX.exists():
        return "NO_SITES_ENABLED"
    for p in sorted(NGINX.iterdir()):
        text = p.read_text(encoding="utf-8", errors="replace")
        chunks.append(f"FILE {p.name}\n{text}")
    return "\n".join(chunks)[:4000]


def main() -> None:
    for rid in IDS:
        print("==== RUN", rid)
        print(json.dumps(inspect_run(rid), indent=2, default=str))
    print("==== LOG")
    print(json.dumps(scan_log(), indent=2))
    print("==== NGINX")
    print(nginx_static())


if __name__ == "__main__":
    main()
