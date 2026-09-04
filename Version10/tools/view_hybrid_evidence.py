#!/usr/bin/env python3
"""Open W.8 crops + Hybrid/Claude JSON for one estimation run. Does not call Claude."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

EVIDENCE_REL = Path("data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence")
SHADOW_REL = Path("data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json")
OBS_REL = Path("data/output/PhaseW6_hybrid_semantic_resolution/hybrid_observability.json")


def _load(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _beams_from_reports(run: Path) -> dict:
    by_id = {}
    shadow = _load(run / SHADOW_REL)
    if isinstance(shadow, dict):
        for row in shadow.get("beams") or []:
            if isinstance(row, dict) and row.get("beam_id"):
                by_id[str(row["beam_id"])] = row
    obs = _load(run / OBS_REL)
    if isinstance(obs, dict) and not by_id:
        for row in obs.get("beams") or []:
            if isinstance(row, dict) and row.get("beam_id"):
                by_id[str(row["beam_id"])] = row
    return by_id


def _answer_json(row: dict) -> str:
    payload = row.get("parsed") or row.get("hybrid_semantic") or row.get("extracted") or row
    keep = {
        k: payload.get(k)
        for k in (
            "target_beam_id",
            "target_identified",
            "association_confidence",
            "groups",
            "stirrups",
            "ambiguities",
            "neighbour_evidence_detected",
            "response_status",
            "call_status",
            "usable",
            "unusable_reason",
            "reinforcement_groups",
        )
        if isinstance(payload, dict) and k in payload
    }
    if not keep and isinstance(payload, dict):
        keep = {k: v for k, v in payload.items() if k not in {"raw", "comparison", "usage"}}
    return json.dumps(keep or {"note": "no parsed Claude JSON on this beam"}, indent=2)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python view_hybrid_evidence.py <run_folder>", file=sys.stderr)
        return 2
    run = Path(argv[1]).resolve()
    evidence = run / EVIDENCE_REL
    if not evidence.is_dir():
        print(f"No hybrid_evidence folder at {evidence}", file=sys.stderr)
        return 1
    reports = _beams_from_reports(run)
    cards = []
    for beam_dir in sorted(p for p in evidence.iterdir() if p.is_dir()):
        bid = beam_dir.name
        ctx = beam_dir / "context" / "selected.png"
        det = beam_dir / "detail" / "selected.png"
        man = beam_dir / "evidence_manifest.json"
        row = reports.get(bid) or {}
        ctx_src = ctx.as_uri() if ctx.is_file() else ""
        det_src = det.as_uri() if det.is_file() else ""
        man_txt = man.read_text(encoding="utf-8") if man.is_file() else "{}"
        status = html.escape(str(row.get("hybrid_status") or row.get("call_status") or ""))
        cards.append(
            f"""
<section class="beam">
  <h2>{html.escape(bid)} <span>{status}</span></h2>
  <div class="pair">
    <figure>
      <figcaption>Image 1 — CONTEXT (sent to Claude)</figcaption>
      {"<img src='" + html.escape(ctx_src) + "' alt='context'/>" if ctx_src else "<p>missing context/selected.png</p>"}
    </figure>
    <figure>
      <figcaption>Image 2 — DETAIL (sent to Claude)</figcaption>
      {"<img src='" + html.escape(det_src) + "' alt='detail'/>" if det_src else "<p>missing detail/selected.png</p>"}
    </figure>
  </div>
  <h3>Claude / Hybrid answer</h3>
  <pre>{html.escape(_answer_json(row))}</pre>
  <details><summary>evidence_manifest.json</summary><pre>{html.escape(man_txt)}</pre></details>
</section>
"""
        )
    out = run / "hybrid_evidence_gallery.html"
    out.write_text(
        """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Hybrid evidence — %s</title>
<style>
  body { font-family: Segoe UI, sans-serif; margin: 24px; color: #1a1a1a; background: #f6f6f4; }
  h1 { font-size: 22px; }
  h2 { font-size: 18px; margin-bottom: 8px; }
  h2 span { font-weight: normal; color: #555; font-size: 14px; }
  .beam { background: #fff; border: 1px solid #ddd; padding: 16px; margin: 0 0 24px; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  figure { margin: 0; }
  figcaption { font-size: 12px; color: #444; margin-bottom: 6px; }
  img { width: 100%%; height: auto; border: 1px solid #ccc; background: #111; }
  pre { background: #111; color: #e8e8e4; padding: 12px; overflow: auto; font-size: 12px; }
</style></head>
<body>
<h1>Crops sent to Claude and JSON answers</h1>
<p>Run: <code>%s</code> — Image 1 CONTEXT, Image 2 DETAIL, then parsed answer. No API call.</p>
%s
</body></html>
"""
        % (html.escape(run.name), html.escape(str(run)), "\n".join(cards)),
        encoding="utf-8",
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
