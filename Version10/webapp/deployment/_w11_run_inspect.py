#!/usr/bin/env python3
"""W.11 live-run forensic. No secrets."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

PID = 168565
RUN = Path("/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/20260826_084708_f74912b8")
OUT = RUN / "data/output"
W6 = OUT / "PhaseW6_hybrid_semantic_resolution"
R13 = OUT / "PhaseR1.3_pipeline_integration" / "beam_reinforcement_models_production.json"


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def safe_read(path: Path, n: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:n]
    except Exception as exc:
        return f"<err {type(exc).__name__}>"


print("UTC", datetime.now(timezone.utc).isoformat())
print("pid_alive", Path(f"/proc/{PID}").exists())
if Path(f"/proc/{PID}").exists():
    stat = Path(f"/proc/{PID}/stat").read_text().split()
    print("stat_state", stat[2] if len(stat) > 2 else "?")
    print("wchan", safe_read(Path(f"/proc/{PID}/wchan"), 200))
    print("cmdline", Path(f"/proc/{PID}/cmdline").read_bytes().replace(b"\0", b" ").decode()[:400])
    print("rss_kb", safe_read(Path(f"/proc/{PID}/status")).split("VmRSS:")[-1].splitlines()[0].strip() if "VmRSS:" in safe_read(Path(f"/proc/{PID}/status")) else "?")
    print("syscall", safe_read(Path(f"/proc/{PID}/syscall"), 300))
    print("cwd", os.readlink(f"/proc/{PID}/cwd"))
    # open files
    fds = Path(f"/proc/{PID}/fd")
    names = []
    for fd in list(fds.iterdir())[:80]:
        try:
            names.append(os.readlink(str(fd)))
        except Exception:
            pass
    interesting = [n for n in names if any(x in n.lower() for x in (".png", ".json", "hybrid", "evidence", "anthropic", "socket", "http"))]
    print("open_interesting_count", len(interesting))
    for n in interesting[:40]:
        print("FD", n)

print("run_exists", RUN.is_dir())
print("excel", (OUT / "Production_Output" / "Estimation_Output.xlsx").is_file())
print("w6_dir", W6.is_dir())
print("w5_report", (OUT / "PhaseW5_production_hybrid_shadow" / "hybrid_shadow_report.json").is_file())
print("w10_monitor", (OUT / "PhaseW10_hybrid_monitoring" / "hybrid_production_monitor.json").is_file())

if R13.is_file():
    data = json.loads(R13.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        beams = data.get("beams") or data.get("beam_models") or []
        if isinstance(beams, dict):
            ids = list(beams.keys())
        elif isinstance(beams, list):
            ids = [b.get("beam_id") or b.get("id") for b in beams if isinstance(b, dict)]
        else:
            ids = []
        print("r13_top_keys", sorted(data.keys())[:30])
        print("r13_beam_count_guess", len(ids))
        print("r13_ids_head", ids[:20])
    elif isinstance(data, list):
        print("r13_list_len", len(data))

# stage dirs + mtimes
print("==== OUTPUT DIRS ====")
if OUT.is_dir():
    for d in sorted(OUT.iterdir(), key=lambda p: p.stat().st_mtime):
        if d.is_dir():
            print(d.name, iso(d.stat().st_mtime))

print("==== W6 TREE ====")
if W6.is_dir():
    files = sorted(W6.rglob("*"), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    print("w6_entries", len(files))
    for p in files[-40:]:
        if p.is_file():
            print(iso(p.stat().st_mtime), p.stat().st_size, p.relative_to(W6))

# newest files in whole run
print("==== NEWEST RUN FILES ====")
allf = [p for p in RUN.rglob("*") if p.is_file()]
allf.sort(key=lambda p: p.stat().st_mtime, reverse=True)
now = time.time()
for p in allf[:30]:
    print(iso(p.stat().st_mtime), round(now - p.stat().st_mtime, 1), p.stat().st_size, p.relative_to(RUN))

# evidence manifests
ev = W6 / "hybrid_evidence"
print("==== EVIDENCE ====")
print("hybrid_evidence_dir", ev.is_dir())
if ev.is_dir():
    beams = [d for d in ev.iterdir() if d.is_dir()]
    print("evidence_beam_dirs", len(beams), [d.name for d in sorted(beams)[:40]])
    pngs = list(ev.rglob("*.png"))
    print("png_count", len(pngs), "png_bytes", sum(p.stat().st_size for p in pngs))

# p2610 evidence elsewhere
for name in (
    "PhaseP2610C1_context_evidence_selection",
    "PhaseP2610C2_detail_evidence_selection",
    "PhaseP2610C3_visual_completeness_claude_shadow",
    "PhaseP2610B1_population_generalization",
    "PhaseW8_hybrid_evidence",
):
    p = OUT / name
    print("phase_dir", name, p.is_dir(), iso(p.stat().st_mtime) if p.exists() else "")
    if p.is_dir():
        pngs = list(p.rglob("*.png"))
        print("  pngs", len(pngs), "bytes", sum(x.stat().st_size for x in pngs) if pngs else 0)
        newest = sorted([x for x in p.rglob("*") if x.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:8]
        for x in newest:
            print(" ", iso(x.stat().st_mtime), x.stat().st_size, x.relative_to(p))
