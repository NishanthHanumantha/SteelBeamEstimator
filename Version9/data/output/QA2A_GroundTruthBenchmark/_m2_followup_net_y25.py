"""Net Y25 diff% excluding ACCEPTABLE_EXTRA + residual-miss spot checks."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETS = [
    ("First_Set_Drawings", "First Set Drawings"),
    ("Second_Set_Drawings", "Second Set Drawings"),
    ("Third_Set_Drawings", "Third Set Drawings"),
]


def net_y25(safe: str) -> dict:
    rows = json.loads((ROOT / safe / "bar_matching.json").read_text(encoding="utf-8"))["rows"]
    dia = json.loads((ROOT / safe / "diameter_comparison.json").read_text(encoding="utf-8"))
    gross = next(x for x in dia["quantity"] if x["diameter"] == 25)
    ae = sum(
        float(r.get("model_qty") or 0)
        for r in rows
        if r.get("status") == "ACCEPTABLE_EXTRA"
        and (r.get("model_diameter") or r.get("diameter")) == 25
    )
    est = float(gross["estimator_quantity"])
    mod_gross = float(gross["model_quantity"])
    mod_net = mod_gross - ae
    diff = mod_net - est
    pct = abs(diff) / est * 100.0 if est else 0.0
    return {
        "set": safe,
        "est": est,
        "mod_gross": mod_gross,
        "ae_qty": ae,
        "mod_net": mod_net,
        "diff": diff,
        "net_diff_pct": round(pct, 2),
    }


def residual_miss_spotcheck() -> list:
    """Find SPACER_BAR MISSING beams and confirm absent MAIN+EXTRA pair in model."""
    results = []
    web = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs")

    def latest_with_spacers(pattern: str) -> Path:
        """Prefer a run that actually emitted M.2 spacers (has spacer_rule_report)."""
        cands = sorted(web.glob(pattern))
        for c in reversed(cands):
            if (c / "data/output/PhaseR1.3_pipeline_integration/spacer_rule_report.json").is_file():
                return c
        return cands[-1]

    run_map = {
        "First Set Drawings": latest_with_spacers("qa2_First_Set*"),
        "Second Set Drawings": latest_with_spacers("qa2_Second_Set*"),
        "Third Set Drawings": latest_with_spacers("qa2_Third_Set*"),
    }
    for safe, name in SETS:
        rows = json.loads((ROOT / safe / "bar_matching.json").read_text(encoding="utf-8"))["rows"]
        miss = [
            r for r in rows
            if r.get("status") == "MISSING" and (r.get("bar_role") or "").upper() == "SPACER_BAR"
        ]
        eng = json.loads(
            (run_map[name] / "data/output/PhaseR1.3_pipeline_integration/engineering_bar_models.json")
            .read_text(encoding="utf-8")
        )
        by_beam = {b["beam_id"]: b for b in eng["beams"]}
        for r in miss:
            bid = r["beam_id"]
            bm = by_beam.get(bid) or {"bars": []}
            roles = [str(b.get("bar_role") or "").upper() for b in bm.get("bars") or []]
            top = [x for x in roles if x in ("TOP_MAIN", "TOP_EXTRA")]
            bot = [x for x in roles if x in ("BOTTOM_MAIN", "BOTTOM_EXTRA")]
            top_pair = ("TOP_MAIN" in top and "TOP_EXTRA" in top)
            bot_pair = ("BOTTOM_MAIN" in bot and "BOTTOM_EXTRA" in bot)
            results.append({
                "set": name,
                "beam_id": bid,
                "est_qty": r.get("estimator_qty"),
                "model_roles": sorted(set(roles)),
                "top_main_extra_pair": top_pair,
                "bottom_main_extra_pair": bot_pair,
                "absent_pair_confirmed": not (top_pair or bot_pair),
            })
    return results


def main() -> None:
    nets = [net_y25(s) for s, _ in SETS]
    misses = residual_miss_spotcheck()
    # pick 5 residual misses with absent pair
    confirmed = [m for m in misses if m["absent_pair_confirmed"]]
    spot = confirmed[:5]
    if len(spot) < 5:
        spot = misses[:5]

    out = {
        "net_y25": nets,
        "spacer_missing_total": len(misses),
        "absent_pair_confirmed_count": sum(1 for m in misses if m["absent_pair_confirmed"]),
        "spotcheck_5": spot,
        "all_residual_misses": misses,
    }
    (ROOT / "m2_followup_net_y25_and_residuals.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
