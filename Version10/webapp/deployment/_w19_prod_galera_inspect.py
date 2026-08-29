#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(
    "/opt/steel-beam-estimation/SteelBeamEstimator/Version10/data/web_runs/"
    "20260829_070104_a2dda3ed/data/output"
)
want = {"B1", "B10", "B23"}
sr = json.loads((root / "PhaseR1.3_pipeline_integration" / "spacer_rule_report.json").read_text())
print("cover_mm_used", sr.get("cover_mm_used"), "extent_fallback_rows", sr.get("extent_fallback_rows"))
for row in sr.get("per_beam") or []:
    if row.get("beam_id") in want:
        print("PER", json.dumps(row))

p = root / "PhaseR1.3_pipeline_integration" / "engineering_bar_models.json"
dump = json.loads(p.read_text())
rows = dump if isinstance(dump, list) else dump.get("beams") or dump.get("models") or []
print("EBM_TYPE", type(dump).__name__)
for bm in rows:
    if not isinstance(bm, dict):
        continue
    bid = bm.get("beam_id")
    if bid not in want:
        continue
    print("BEAM", bid, "nbars", len(bm.get("bars") or []))
    for bar in bm.get("bars") or []:
        meta = bar.get("engineering_metadata") or {}
        role = str(bar.get("bar_role") or meta.get("bar_role") or "")
        ptype = str(meta.get("piece_type") or bar.get("piece_type") or "")
        start = meta.get("piece_start_mm", bar.get("piece_start_mm"))
        end = meta.get("piece_end_mm", bar.get("piece_end_mm"))
        cut = meta.get("cut_length_mm", bar.get("cut_length_mm"))
        label = bar.get("bar_label")
        print(
            "  role=%s ptype=%s start=%s end=%s cut=%s label=%s"
            % (role, ptype, start, end, cut, label)
        )

l2 = json.loads(
    (root / "PhaseR1.3_pipeline_integration" / "beam_reinforcement_models_production.json").read_text()
)
models = {m.get("beam_id"): m for m in (l2.get("models") or [])}
for bid in ("B1", "B10", "B23"):
    m = models.get(bid) or {}
    geom = m.get("geometry") or {}
    print("L2", bid, "span", geom.get("span_mm"), "w", geom.get("width_mm"))
    for key in (
        "top_main_bars",
        "top_extra_bars",
        "bottom_main_bars",
        "bottom_extra_bars",
        "spacer_bars",
    ):
        bars = m.get(key) or []
        print(" ", key, len(bars))
        for b in bars:
            print(
                "   ",
                b.get("bar_id"),
                "qty",
                b.get("quantity"),
                "dia",
                b.get("diameter_mm"),
                "start",
                b.get("piece_start_mm"),
                "end",
                b.get("piece_end_mm"),
                "cut",
                b.get("cut_length_mm"),
                "ptype",
                b.get("piece_type"),
                "zlen",
                b.get("zone_length_mm"),
            )

s = json.loads((root / "PhaseR.2A_engineering_context" / "engineering_context_summary.json").read_text())
keep = {
    k: s.get(k)
    for k in s
    if any(x in k.lower() for x in ("cover", "steel", "dev", "grade", "source", "factor"))
}
print("R2A", json.dumps(keep, default=str))
