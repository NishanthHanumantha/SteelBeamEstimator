#!/usr/bin/env python3
"""
QA.3.0 live progress tracker.
Rewrites LIVE_PROGRESS.md every --interval seconds until the phase finishes
or --max-hours elapses.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

PRODUCTION_STAGES = [
    "VROOT1", "R1", "T1", "R2A", "R21B", "R21C", "R21D", "L22",
    "R3", "R31", "R12A", "R13", "VB1", "T16CHAIN",
]
T16_SUB = [
    ("T16", "PhaseT16_entity_ownership"),
    ("T17", "PhaseT17_annotation_graph"),
    ("T18", "PhaseT18_beam_ownership"),
    ("T181", "PhaseT181_render_validation"),
    ("T182", "PhaseT182_adaptive_render_extent"),
    ("T183", "PhaseT183_shared_engineering_ownership"),
    ("T1831", "PhaseT1831_shared_scope_dedup"),
]
SETS = ("Fourth", "Fifth", "Sixth")
STAGE_DIRS = {
    "VROOT1": "PhaseVROOT.1_dynamic_pipeline_initialization",
    "R1": "PhaseR1_generalized_reinforcement_discovery",
    "T1": "PhaseT1_geometric_stirrup_evidence",
    "R2A": "PhaseR.2A_engineering_context",
    "R21B": "PhaseR2.1B_engineering_semantic_interpreter",
    "R21C": "PhaseR2.1C_engineering_fact_normalization",
    "R21D": "PhaseR2.1D_evidence_hypothesis_engine",
    "L22": "PhaseL.2.2_geometry_recovery",
    "R3": "PhaseR3_geometry_context_engine",
    "R31": "PhaseR3.1_engineering_relationship_engine",
    "R12A": "PhaseR1_2A_geometry_accuracy",
    "R13": "PhaseR1.3_pipeline_integration",
    "VB1": "Production_Output",
}


def bar(pct: float, width: int = 24) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(round(width * pct / 100.0))
    return "[" + "#" * filled + "-" * (width - filled) + f"] {pct:5.1f}%"


def newest_run(web_runs: Path, set_key: str) -> Path | None:
    safe = f"{set_key}_Set_Drawings"
    cands = sorted(
        [p for p in web_runs.glob(f"qa2_{safe}_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return cands[0] if cands else None


def png_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(list(path.rglob("*.png")))


def set_status(engine: Path, phase_out: Path, set_key: str) -> dict:
    set_dir = phase_out / f"{set_key}_Set_Drawings"
    mirrored = (set_dir / "Estimation_Output.xlsx").exists()
    prod = set_dir / "production_result.json"
    success = False
    if prod.exists():
        try:
            success = bool(json.loads(prod.read_text(encoding="utf-8")).get("success"))
        except Exception:
            pass
    run = newest_run(engine / "data" / "web_runs", set_key)
    out = (run / "data" / "output") if run else None
    stages_done = 0
    current = "not_started"
    t16_detail = ""
    t182_png = t181_png = 0
    if out and out.exists():
        for i, sid in enumerate(PRODUCTION_STAGES):
            if sid == "T16CHAIN":
                break
            dname = STAGE_DIRS.get(sid)
            if dname and (out / dname).exists():
                stages_done = i + 1
                current = sid
        excel = out / "Production_Output" / "Estimation_Output.xlsx"
        if excel.exists():
            stages_done = max(stages_done, 13)  # through VB1
            current = "VB1"
            # T16 sub-progress
            t16_done = 0
            for j, (label, folder) in enumerate(T16_SUB):
                if (out / folder).exists():
                    t16_done = j + 1
                    current = f"T16CHAIN/{label}"
            t181_png = png_count(out / "PhaseT181_render_validation" / "RenderedBeams")
            t182_png = png_count(out / "PhaseT182_adaptive_render_extent" / "RenderedBeams")
            if t181_png > 0 and t182_png < t181_png and t16_done >= 5:
                t16_detail = f"T182 crops {t182_png}/{t181_png}"
            # T16CHAIN fraction of last stage
            t16_frac = t16_done / len(T16_SUB)
            stage_pct = (13 + t16_frac) / 14 * 100.0
        else:
            stage_pct = stages_done / 14 * 100.0
    else:
        stage_pct = 0.0

    if mirrored or success:
        stage_pct = 100.0
        current = "complete"
        stages_done = 14

    return {
        "set_key": set_key,
        "run_id": run.name if run else None,
        "mirrored": mirrored,
        "success": success,
        "current": current,
        "stage_pct": round(stage_pct, 1),
        "t16_detail": t16_detail,
        "t181_png": t181_png,
        "t182_png": t182_png,
        "crops_mirrored": png_count(set_dir / "RenderedCrops") if set_dir.exists() else 0,
    }


def overall_pct(sets: list[dict], phase_out: Path) -> float:
    # Production = 85%, benchmark+reports = 15%
    prod = sum(s["stage_pct"] for s in sets) / (100.0 * len(sets)) * 85.0
    reports = 0.0
    for name in (
        "Generalization_Benchmark_Report.json",
        "QA30Validation.json",
        "GeneralizationSummary.md",
    ):
        if (phase_out / name).exists():
            reports += 5.0
    return min(100.0, round(prod + reports, 1))


def parse_log(log_path: Path) -> str:
    if not log_path.exists():
        return "(log not found)"
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[-12:])


def render(engine: Path) -> tuple[str, dict]:
    phase_out = engine / "data" / "output" / "PhaseQA30_unseen_benchmark"
    log = engine / "data" / "output" / "PhaseQA30_unseen_benchmark_run2.log"
    sets = [set_status(engine, phase_out, k) for k in SETS]
    pct = overall_pct(sets, phase_out)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done_sets = sum(1 for s in sets if s["stage_pct"] >= 100)
    active = next((s for s in sets if 0 < s["stage_pct"] < 100), None)
    finished = (phase_out / "PhaseQA30_result.json").exists() or (
        phase_out / "QA30Validation.json"
    ).exists()

    lines = [
        "# QA.3.0 Live Progress Tracker",
        "",
        f"**Updated:** {now}",
        f"**MODEL_VERSION:** 10.0.0",
        f"**Status:** {'FINISHED' if finished else 'RUNNING'}",
        "",
        "## Overall",
        "",
        "```",
        f"Overall  {bar(pct)}",
        f"Sets     {done_sets}/3 production complete",
        "```",
        "",
        "## Drawing sets",
        "",
    ]
    for s in sets:
        mark = "DONE" if s["stage_pct"] >= 100 else ("ACTIVE" if s is active else "WAIT")
        detail = s["t16_detail"] or s["current"]
        lines += [
            f"### {s['set_key']} Set Drawings  [{mark}]",
            "",
            "```",
            f"{bar(s['stage_pct'])}",
            f"stage: {detail}",
            f"run:   {s['run_id'] or '-'}",
            f"mirrored workbook: {s['mirrored']} | crops: {s['crops_mirrored']}",
            "```",
            "",
        ]

    lines += [
        "## Remaining pipeline",
        "",
        "| Step | State |",
        "|------|-------|",
    ]
    for s in sets:
        st = "done" if s["stage_pct"] >= 100 else (
            f"in progress ({s['current']})" if s["stage_pct"] > 0 else "pending"
        )
        lines.append(f"| {s['set_key']} production | {st} |")
    for label, fname in (
        ("Benchmark (estimator Excel)", "BenchmarkResult.json"),
        ("Generalization report", "Generalization_Benchmark_Report.json"),
        ("QA validation", "QA30Validation.json"),
    ):
        st = "done" if (phase_out / fname).exists() else "pending"
        lines.append(f"| {label} | {st} |")

    lines += [
        "",
        "## Recent log",
        "",
        "```",
        parse_log(log),
        "```",
        "",
        "_Auto-refreshed by `Run_PY/qa30_live_progress.py`. Open this file to watch live._",
        "",
    ]
    doc = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "overall_pct": pct,
        "finished": finished,
        "sets": sets,
        "active_set": active["set_key"] if active else None,
    }
    return "\n".join(lines), doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, default=None)
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--max-hours", type=float, default=12.0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    engine = args.engine or Path(__file__).resolve().parents[1]
    out_md = engine / "data" / "output" / "PhaseQA30_unseen_benchmark" / "LIVE_PROGRESS.md"
    out_json = out_md.with_suffix(".json")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + args.max_hours * 3600
    while True:
        md, doc = render(engine)
        out_md.write_text(md, encoding="utf-8")
        out_json.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(
            f"[{doc['updated_at']}] overall={doc['overall_pct']}% "
            f"active={doc['active_set']} finished={doc['finished']}",
            flush=True,
        )
        if args.once or doc["finished"] or time.time() >= deadline:
            break
        time.sleep(max(5, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
