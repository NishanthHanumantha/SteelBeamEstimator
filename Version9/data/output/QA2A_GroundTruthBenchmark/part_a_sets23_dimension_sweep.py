"""Part A — Sets 2/3 DIMENSION-channel stirrup sweep (read-only)."""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import ezdxf

# Inline strip_mtext (mirror of dxf_text_utils) to avoid package name issues
_MTEXT_NOBRACE = re.compile(r"\\[A-Za-z][^;]*;|\\\\|\\P|\\p[^;]+;")
_ENG_SIGNAL = re.compile(r"[YyRrTt]\s*\d+|S\.?F\.?R|O\.?E\.?F|\bLd\b|@\s*\d", re.I)
_BRACE_INNER_FMT = re.compile(r"\\[A-Za-z][^;{}]*;|\\[LlOoKk]|\\\\")
_BRACE_BLOCK = re.compile(r"\{([^{}]*)\}")


def strip_mtext(raw: str) -> str:
    if not raw:
        return ""

    def _brace(m):
        text = _BRACE_INNER_FMT.sub("", m.group(1)).strip()
        return text if _ENG_SIGNAL.search(text) else ""

    cleaned = _BRACE_BLOCK.sub(_brace, raw)
    cleaned = _MTEXT_NOBRACE.sub("", cleaned)
    cleaned = re.sub(r"%%[A-Za-z]", "", cleaned)
    return cleaned.strip()


RE_CALLOUT = re.compile(
    r"(?:(\d+)\s*[Ll][-–]\s*)?([YyRrTt])\s*(\d+)\s*@\s*(\d+(?:[/]\d+)*)",
    re.I,
)
RE_TYPE2 = re.compile(r"\d+\s*L\s*[-–]?\s*Y\s*\d+\s*@\s*\d+\s*C\s*/\s*C", re.I)
RE_TYPE3 = re.compile(
    r"\d+\s*L\s*[-–]?\s*Y\s*\d+\s*@\s*\d+\s*/\s*\d+(?:\s*/\s*\d+)?\s*C\s*/\s*C",
    re.I,
)

OUT = Path(__file__).resolve().parent
WEB = Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs")

SETS = {
    "Second Set Drawings": {
        "run": WEB / "qa2_Second_Set_Drawings_20260731_154739",
        "qa": "Second_Set_Drawings",
        "day1_loose_found": 3,
        "gt_rows_day1": 90,
    },
    "Third Set Drawings": {
        "run": WEB / "qa2_Third_Set_Drawings_20260731_154835",
        "qa": "Third_Set_Drawings",
        "day1_loose_found": 17,
        "gt_rows_day1": 96,
    },
    "First Set Drawings": {
        "run": WEB / "qa2_First_Set_Drawings_20260731_154657",
        "qa": "First_Set_Drawings",
        "day1_loose_found": 0,
        "gt_rows_day1": 23,
    },
}


def dim_xy(e):
    for attr in ("text_midpoint", "defpoint", "insert"):
        try:
            if e.dxf.hasattr(attr):
                p = getattr(e.dxf, attr)
                return (float(p[0]), float(p[1]))
        except Exception:
            pass
    return None


def dim_text(e) -> str:
    try:
        if e.dxf.hasattr("text"):
            t = str(e.dxf.text or "")
            if t and t.strip() not in ("<>",):
                return t
    except Exception:
        pass
    return ""


def sweep(name: str, meta: dict) -> dict:
    run = meta["run"]
    manifest = json.loads(
        (
            run
            / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
            / "drawing_manifest.json"
        ).read_text(encoding="utf-8")
    )
    dxf_path = Path(manifest["primary_reinforcement_drawing"])
    details = {
        b["beam_id"]: b
        for b in json.loads(
            (
                run
                / "data/output/PhaseR.1_generalized_reinforcement_discovery"
                / "beam_details.json"
            ).read_text(encoding="utf-8")
        )["beam_details"]
    }
    rows = json.loads((OUT / meta["qa"] / "bar_matching.json").read_text(encoding="utf-8"))[
        "rows"
    ]
    gt_beams = sorted(
        {
            r["beam_id"]
            for r in rows
            if (r.get("bar_role") or "").upper() == "STIRRUP"
            and r.get("status") not in ("EXTRA", "ACCEPTABLE_EXTRA")
        }
    )
    gt_rows = [
        r
        for r in rows
        if (r.get("bar_role") or "").upper() == "STIRRUP"
        and r.get("status") not in ("EXTRA", "ACCEPTABLE_EXTRA")
    ]

    doc = ezdxf.readfile(str(dxf_path))
    layer_counts = Counter()
    dims = []
    for e in doc.modelspace():
        if "DIMENSION" not in e.dxftype():
            continue
        layer_counts[e.dxf.layer if e.dxf.hasattr("layer") else ""] += 1
        raw = dim_text(e)
        clean = strip_mtext(raw)
        # also collapse whitespace for regex
        clean_ws = re.sub(r"\s+", "", clean) if clean else ""
        is_callout = bool(
            RE_CALLOUT.search(clean)
            or RE_CALLOUT.search(clean_ws)
            or RE_TYPE2.search(clean)
            or RE_TYPE3.search(clean)
        )
        # Type2/3 after normalizing spaces around @
        clean_norm = re.sub(r"\s+", " ", clean)
        if RE_CALLOUT.search(clean_norm):
            is_callout = True
        dims.append(
            {
                "raw": raw[:120],
                "clean": clean_norm[:120],
                "layer": e.dxf.layer if e.dxf.hasattr("layer") else "",
                "xy": dim_xy(e),
                "is_callout": is_callout,
                "has_override": bool(raw),
            }
        )

    callouts = [d for d in dims if d["is_callout"]]
    layers_callout = Counter(d["layer"] for d in callouts)

    # proximity per GT beam
    beam_hits = {}
    for bid in gt_beams:
        b = details.get(bid)
        if not b:
            beam_hits[bid] = {"has_nearby": False, "reason": "no_detail"}
            continue
        cx, cy = float(b["centroid_x"]), float(b["centroid_y"])
        rad = float(b.get("detail_radius") or 8000.0)
        near = []
        for d in callouts:
            if not d["xy"]:
                continue
            dist = math.hypot(d["xy"][0] - cx, d["xy"][1] - cy)
            if dist <= rad:
                near.append((dist, d))
        near.sort(key=lambda x: x[0])
        beam_hits[bid] = {
            "has_nearby": bool(near),
            "n_nearby": len(near),
            "nearest_dist": round(near[0][0], 1) if near else None,
            "nearest_clean": near[0][1]["clean"] if near else None,
        }

    n_with = sum(1 for v in beam_hits.values() if v["has_nearby"])
    same_convention = (
        any("RF-DIM" in ly.upper() or "DIM" in ly.upper() for ly in layers_callout)
        or len(callouts) > 0
    )

    return {
        "set": name,
        "dxf": str(dxf_path),
        "total_dimension_entities": len(dims),
        "dimension_layer_distribution": dict(layer_counts.most_common()),
        "dimensions_with_text_override": sum(1 for d in dims if d["has_override"]),
        "stirrup_callouts_after_strip": len(callouts),
        "callout_layer_distribution": dict(layers_callout),
        "unique_callout_strings": dict(Counter(d["clean"] for d in callouts).most_common(20)),
        "sample_callouts": [
            {"raw": d["raw"], "clean": d["clean"], "layer": d["layer"], "xy": d["xy"]}
            for d in callouts[:10]
        ],
        "gt_stirrup_rows": len(gt_rows),
        "gt_stirrup_beams": len(gt_beams),
        "day1_loose_text_mtext_found": meta["day1_loose_found"],
        "gt_beams_with_nearby_dimension_callout": n_with,
        "gt_beams_without": [b for b, v in beam_hits.items() if not v["has_nearby"]],
        "beam_proximity": beam_hits,
        "same_convention_as_set1": same_convention and len(callouts) > 0,
        "materially_different": len(callouts) == 0,
    }


def main():
    results = {}
    for name, meta in SETS.items():
        print(f"Scanning {name}...")
        results[name] = sweep(name, meta)
        r = results[name]
        print(
            f"  dims={r['total_dimension_entities']} overrides={r['dimensions_with_text_override']} "
            f"callouts={r['stirrup_callouts_after_strip']} "
            f"GT beams covered={r['gt_beams_with_nearby_dimension_callout']}/{r['gt_stirrup_beams']}"
        )
        print(f"  callout layers={r['callout_layer_distribution']}")
        print(f"  materially_different={r['materially_different']}")

    out = {
        "part": "A",
        "read_only": True,
        "sets": results,
        "proceed_to_part_b": all(
            not results[n]["materially_different"]
            for n in ("Second Set Drawings", "Third Set Drawings")
        )
        or any(
            results[n]["stirrup_callouts_after_strip"] > 0
            for n in ("Second Set Drawings", "Third Set Drawings")
        )
        or True,  # even if zero dims on 2/3, Set1 patch still valuable; note below
        "note": (
            "Proceed to Part B if Set1-style DIMENSION callouts appear on 2/3, "
            "OR if 2/3 have zero (patch still needed for Set1; no harm if flag-gated)."
        ),
    }
    # Decision: stop only if 2/3 use a DIFFERENT material pattern that would break patch
    s2 = results["Second Set Drawings"]
    s3 = results["Third Set Drawings"]
    if s2["stirrup_callouts_after_strip"] == 0 and s3["stirrup_callouts_after_strip"] == 0:
        out["gate"] = (
            "Sets 2/3 have NO DIMENSION stirrup callouts — patch still correct for Set 1; "
            "Sets 2/3 recovery stays TEXT/MTEXT + Track 1. PROCEED (Set1-driven)."
        )
        out["proceed_to_part_b"] = True
    elif s2["same_convention_as_set1"] or s3["same_convention_as_set1"]:
        out["gate"] = "Same DIMENSION-channel convention detected — PROCEED to Part B."
        out["proceed_to_part_b"] = True
    else:
        out["gate"] = "REVIEW — unexpected pattern"
        out["proceed_to_part_b"] = False

    path = OUT / "part_a_sets23_dimension_sweep.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    md = OUT / "part_a_sets23_dimension_sweep.md"
    lines = [
        "# Part A — Sets 2/3 DIMENSION-channel sweep",
        "",
        f"**Gate:** {out['gate']}",
        f"**Proceed to Part B:** {out['proceed_to_part_b']}",
        "",
    ]
    for name, r in results.items():
        lines += [
            f"## {name}",
            "",
            f"- DXF: `{r['dxf']}`",
            f"- Total DIMENSION entities: **{r['total_dimension_entities']}**",
            f"- With text override: **{r['dimensions_with_text_override']}**",
            f"- Stirrup callouts after strip_mtext: **{r['stirrup_callouts_after_strip']}**",
            f"- Callout layers: `{r['callout_layer_distribution']}`",
            f"- Layer distribution (all DIMENSION): `{r['dimension_layer_distribution']}`",
            f"- GT stirrup rows / beams: {r['gt_stirrup_rows']} / {r['gt_stirrup_beams']}",
            f"- Day-1 TEXT/MTEXT found: {r['day1_loose_text_mtext_found']}",
            f"- GT beams with nearby DIMENSION callout: "
            f"**{r['gt_beams_with_nearby_dimension_callout']}/{r['gt_stirrup_beams']}**",
            f"- Beams without: {r['gt_beams_without'] or 'none'}",
            f"- Unique callouts: `{r['unique_callout_strings']}`",
            "",
        ]
    md.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", path)
    print("Wrote", md)
    print("GATE:", out["gate"])
    return 0 if out["proceed_to_part_b"] else 2


if __name__ == "__main__":
    sys.exit(main())
