"""
Day-1 ADDENDUM — Set 1 exhaustive raw-text stirrup sweep.
MODEL_VERSION 9.1.0 — READ-ONLY. Bypasses R.1; reads DXF via ezdxf only.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ezdxf
from ezdxf import recover

OUT_DIR = Path(__file__).resolve().parent
RUN_ROOT = Path(
    r"C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs"
    r"\qa2_First_Set_Drawings_20260731_154657"
)
MANIFEST = (
    RUN_ROOT
    / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
    / "drawing_manifest.json"
)
REGISTRY = (
    RUN_ROOT
    / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
    / "beam_registry.json"
)
BEAM_DETAILS = (
    RUN_ROOT
    / "data/output/PhaseR.1_generalized_reinforcement_discovery"
    / "beam_details.json"
)
BAR_MATCHING = OUT_DIR / "First_Set_Drawings" / "bar_matching.json"

# Substring gates (case-insensitive). "@" counted separately.
RE_CC = re.compile(r"C\s*/\s*C", re.I)
RE_LY = re.compile(r"L\s*[-–]\s*Y", re.I)
RE_STIRRUP = re.compile(r"STIRRUP", re.I)
RE_DIA = re.compile(r"(?:Ø|PHI\b|DIA\b)", re.I)
RE_AT = re.compile(r"@")
# True stirrup callout (R.1-native loose)
RE_CALLOUT = re.compile(
    r"(?:(\d+)\s*[Ll][-–]\s*)?([YyRrTt])\s*(\d+)\s*@\s*(\d+(?:[/]\d+)*)",
    re.I,
)
RE_STRICT2 = re.compile(
    r"\d+\s*L\s*[-–]?\s*Y\s*\d+\s*@\s*\d+\s*C\s*/\s*C", re.I
)


def _safe_layer(e) -> str:
    try:
        return str(e.dxf.layer) if e.dxf.hasattr("layer") else ""
    except Exception:
        return ""


def _xy(e) -> Optional[Tuple[float, float]]:
    for attr in ("insert", "align_point", "start", "defpoint"):
        try:
            if e.dxf.hasattr(attr):
                p = getattr(e.dxf, attr)
                return (float(p[0]), float(p[1]))
        except Exception:
            pass
    try:
        if hasattr(e, "dxf") and e.dxf.hasattr("text_midpoint"):
            p = e.dxf.text_midpoint
            return (float(p[0]), float(p[1]))
    except Exception:
        pass
    return None


def _text_from_entity(e) -> str:
    t = e.dxftype()
    try:
        if t == "TEXT":
            return str(e.dxf.text or "")
        if t == "MTEXT":
            return str(e.text or "")
        if t in ("ATTRIB", "ATTDEF"):
            return str(getattr(e.dxf, "text", "") or "")
        if "DIMENSION" in t or t.endswith("DIMENSION"):
            # override / plain text
            ov = ""
            if e.dxf.hasattr("text"):
                ov = str(e.dxf.text or "")
            if ov and ov not in ("<>", " "):
                return ov
            try:
                return str(e.dxf.get("text", "") or "")
            except Exception:
                return ov
        if t == "ACAD_TABLE" or t == "TABLE":
            # best-effort: dump cell contents if API allows
            parts = []
            try:
                n_rows = e.nrows
                n_cols = e.ncols
                for r in range(n_rows):
                    for c in range(n_cols):
                        try:
                            parts.append(str(e.get_cell_text(r, c) or ""))
                        except Exception:
                            try:
                                parts.append(str(e.get_text(r, c) or ""))
                            except Exception:
                                pass
            except Exception:
                pass
            return " | ".join(p for p in parts if p)
        if t == "MULTILEADER" or t == "MLEADER":
            try:
                ctx = e.context
                if hasattr(ctx, "mtext") and ctx.mtext:
                    return str(getattr(ctx.mtext, "default_content", "") or "")
            except Exception:
                pass
            try:
                return str(e.dxf.get("text", "") or "")
            except Exception:
                return ""
    except Exception:
        return ""
    return ""


def _match_tags(text: str) -> List[str]:
    tags = []
    if RE_CC.search(text):
        tags.append("C/C")
    if RE_LY.search(text):
        tags.append("L-Y")
    if RE_STIRRUP.search(text):
        tags.append("STIRRUP")
    if RE_DIA.search(text):
        tags.append("Ø/PHI/DIA")
    if RE_CALLOUT.search(text):
        tags.append("CALLOUT_YD@S")
    if RE_STRICT2.search(text):
        tags.append("STRICT_TYPE2")
    return tags


def _hit(
    *,
    drawing: str,
    text: str,
    entity_type: str,
    layer: str,
    block: str,
    depth: int,
    xy: Optional[Tuple[float, float]],
    source: str,
    tags: List[str],
) -> Dict[str, Any]:
    return {
        "drawing": drawing,
        "matched_string": text[:300],
        "entity_type": entity_type,
        "layer": layer,
        "containing_block": block,
        "nesting_depth": depth,
        "x": None if xy is None else round(xy[0], 3),
        "y": None if xy is None else round(xy[1], 3),
        "source": source,
        "tags": tags,
    }


def _scan_layout_entities(
    entities,
    *,
    drawing: str,
    block: str,
    depth: int,
    source: str,
    hits: List[Dict[str, Any]],
    at_count: List[int],
    entity_type_counts: Counter,
) -> None:
    for e in entities:
        try:
            et = e.dxftype()
        except Exception:
            continue
        entity_type_counts[et] += 1

        if et == "INSERT":
            # recurse via virtual_entities for nested content
            try:
                for ve in e.virtual_entities():
                    _scan_one_entity(
                        ve,
                        drawing=drawing,
                        block=f"{block}/{e.dxf.name}" if block != "modelspace" else e.dxf.name,
                        depth=depth + 1,
                        source="INSERT.virtual_entities",
                        hits=hits,
                        at_count=at_count,
                        entity_type_counts=entity_type_counts,
                        insert_xy=_xy(e),
                    )
            except Exception:
                pass
            # also ATTRIB on the INSERT itself
            try:
                for a in e.attribs:
                    _scan_one_entity(
                        a,
                        drawing=drawing,
                        block=e.dxf.name,
                        depth=depth + 1,
                        source="INSERT.attribs",
                        hits=hits,
                        at_count=at_count,
                        entity_type_counts=entity_type_counts,
                        insert_xy=_xy(e),
                    )
            except Exception:
                pass
            continue

        _scan_one_entity(
            e,
            drawing=drawing,
            block=block,
            depth=depth,
            source=source,
            hits=hits,
            at_count=at_count,
            entity_type_counts=entity_type_counts,
            insert_xy=None,
        )


def _scan_one_entity(
    e,
    *,
    drawing: str,
    block: str,
    depth: int,
    source: str,
    hits: List[Dict[str, Any]],
    at_count: List[int],
    entity_type_counts: Counter,
    insert_xy: Optional[Tuple[float, float]],
) -> None:
    try:
        et = e.dxftype()
    except Exception:
        return
    # nested INSERT inside virtual stream
    if et == "INSERT":
        try:
            for ve in e.virtual_entities():
                _scan_one_entity(
                    ve,
                    drawing=drawing,
                    block=f"{block}/{e.dxf.name}",
                    depth=depth + 1,
                    source="INSERT.virtual_entities",
                    hits=hits,
                    at_count=at_count,
                    entity_type_counts=entity_type_counts,
                    insert_xy=_xy(e) or insert_xy,
                )
        except Exception:
            pass
        return

    text = _text_from_entity(e)
    if not text:
        return
    at_count[0] += len(RE_AT.findall(text))
    tags = _match_tags(text)
    if not tags:
        return
    xy = _xy(e) or insert_xy
    hits.append(
        _hit(
            drawing=drawing,
            text=text.replace("\n", "\\n").replace("\r", ""),
            entity_type=et,
            layer=_safe_layer(e),
            block=block,
            depth=depth,
            xy=xy,
            source=source,
            tags=tags,
        )
    )


def scan_dxf(path: Path, drawing_label: str) -> Dict[str, Any]:
    try:
        doc, auditor = recover.readfile(str(path))
    except Exception:
        doc = ezdxf.readfile(str(path))
        auditor = None

    hits: List[Dict[str, Any]] = []
    at_count = [0]
    entity_type_counts: Counter = Counter()
    xref_notes: List[str] = []

    # XREF inventory
    try:
        for b in doc.blocks:
            try:
                if b.is_xref or b.is_xref_overlay or getattr(b, "block_record", None) and getattr(
                    b.block_record.dxf, "flags", 0
                ) & 4:
                    # unresolved check: empty entities often
                    n_ent = sum(1 for _ in b)
                    xref_notes.append(
                        f"block={b.name} xref_like ents={n_ent} "
                        f"(path={getattr(b.block_record.dxf, 'xrefpath', '') if hasattr(b, 'block_record') else ''})"
                    )
            except Exception:
                pass
    except Exception as ex:
        xref_notes.append(f"xref scan error: {ex}")

    # 1) Modelspace (includes INSERT explosion)
    _scan_layout_entities(
        doc.modelspace(),
        drawing=drawing_label,
        block="modelspace",
        depth=0,
        source="modelspace",
        hits=hits,
        at_count=at_count,
        entity_type_counts=entity_type_counts,
    )

    # 2) Paperspace layouts
    for layout in doc.layouts:
        if layout.name.lower() == "model":
            continue
        _scan_layout_entities(
            layout,
            drawing=drawing_label,
            block=f"paperspace:{layout.name}",
            depth=0,
            source=f"paperspace:{layout.name}",
            hits=hits,
            at_count=at_count,
            entity_type_counts=entity_type_counts,
        )

    # 3) Every block definition (even unreferenced) — depth marked as def-only
    block_def_hits: List[Dict[str, Any]] = []
    for b in doc.blocks:
        if b.name.startswith("*"):
            continue
        local_hits: List[Dict[str, Any]] = []
        local_at = [0]
        _scan_layout_entities(
            b,
            drawing=drawing_label,
            block=b.name,
            depth=1,
            source="block_definition",
            hits=local_hits,
            at_count=local_at,
            entity_type_counts=entity_type_counts,
        )
        # mark whether this block is inserted in MSP
        inserted = False
        try:
            for e in doc.modelspace().query("INSERT"):
                if e.dxf.name == b.name:
                    inserted = True
                    break
        except Exception:
            pass
        for h in local_hits:
            h["block_is_inserted_in_msp"] = inserted
            h["source"] = "block_definition"
        block_def_hits.extend(local_hits)
        at_count[0] += local_at[0]

    # Deduplicate: same string+block+source+xy
    def key(h):
        return (
            h["matched_string"],
            h["containing_block"],
            h["source"],
            h["entity_type"],
            h.get("x"),
            h.get("y"),
            h["nesting_depth"],
        )

    seen = set()
    uniq_msp = []
    for h in hits:
        k = key(h)
        if k in seen:
            continue
        seen.add(k)
        uniq_msp.append(h)

    seen_def = set()
    uniq_def = []
    for h in block_def_hits:
        k = key(h)
        if k in seen_def:
            continue
        seen_def.add(k)
        uniq_def.append(h)

    # Classify callouts that are only in unreferenced block defs
    callout_msp = [h for h in uniq_msp if "CALLOUT_YD@S" in h["tags"] or "STRICT_TYPE2" in h["tags"]]
    callout_def_only = [
        h
        for h in uniq_def
        if ("CALLOUT_YD@S" in h["tags"] or "STRICT_TYPE2" in h["tags"])
        and not h.get("block_is_inserted_in_msp")
    ]
    callout_def_inserted = [
        h
        for h in uniq_def
        if ("CALLOUT_YD@S" in h["tags"] or "STRICT_TYPE2" in h["tags"])
        and h.get("block_is_inserted_in_msp")
    ]

    return {
        "path": str(path),
        "drawing_label": drawing_label,
        "at_symbol_count": at_count[0],
        "entity_type_counts": dict(entity_type_counts),
        "xref_notes": xref_notes,
        "hits_msp_paperspace_inserts": uniq_msp,
        "hits_block_definitions": uniq_def,
        "callout_in_live_drawing": callout_msp,
        "callout_in_inserted_block_defs": callout_def_inserted,
        "callout_in_unreferenced_block_defs": callout_def_only,
        "summary_tags": dict(
            Counter(t for h in uniq_msp + uniq_def for t in h["tags"])
        ),
    }


def collect_nearby_texts(
    reinf_path: Path,
    beams: List[Dict[str, Any]],
    radius_factor: float = 1.0,
) -> Dict[str, Any]:
    """All TEXT/MTEXT/ATTRIB (MSP + INSERT virtual) near each beam centroid."""
    doc = ezdxf.readfile(str(reinf_path))
    texts: List[Dict[str, Any]] = []

    def add(text, et, layer, block, depth, xy, source):
        if not text or not xy:
            return
        texts.append(
            {
                "text": text.replace("\n", "\\n")[:200],
                "entity_type": et,
                "layer": layer,
                "block": block,
                "depth": depth,
                "x": round(xy[0], 3),
                "y": round(xy[1], 3),
                "source": source,
            }
        )

    def walk(entities, block, depth, source):
        for e in entities:
            try:
                et = e.dxftype()
            except Exception:
                continue
            if et == "INSERT":
                try:
                    for ve in e.virtual_entities():
                        walk([ve], e.dxf.name if depth == 0 else f"{block}/{e.dxf.name}", depth + 1, "INSERT.virtual")
                except Exception:
                    pass
                try:
                    for a in e.attribs:
                        xy = _xy(a) or _xy(e)
                        add(_text_from_entity(a), "ATTRIB", _safe_layer(a), e.dxf.name, depth + 1, xy, "INSERT.attribs")
                except Exception:
                    pass
                continue
            if et in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF") or "DIMENSION" in et or et in (
                "MULTILEADER",
                "MLEADER",
                "ACAD_TABLE",
                "TABLE",
            ):
                xy = _xy(e)
                add(_text_from_entity(e), et, _safe_layer(e), block, depth, xy, source)

    walk(doc.modelspace(), "modelspace", 0, "modelspace")

    by_beam = {}
    for b in beams:
        bid = b["beam_id"]
        cx, cy = float(b["centroid_x"]), float(b["centroid_y"])
        rad = float(b.get("detail_radius") or 8000.0) * radius_factor
        near = []
        for t in texts:
            d = math.hypot(t["x"] - cx, t["y"] - cy)
            if d <= rad:
                near.append({**t, "dist_to_centroid": round(d, 1)})
        near.sort(key=lambda x: x["dist_to_centroid"])
        # classify
        stirrupish = [
            n
            for n in near
            if _match_tags(n["text"]) or RE_CALLOUT.search(n["text"])
        ]
        by_beam[bid] = {
            "centroid": (cx, cy),
            "radius": rad,
            "nearby_text_count": len(near),
            "stirrup_related_nearby": stirrupish[:20],
            "nearest_texts": near[:15],
            "has_stirrup_callout_nearby": any(
                "CALLOUT_YD@S" in _match_tags(n["text"]) or RE_STRICT2.search(n["text"])
                for n in near
            ),
        }
    return {"all_text_entities_collected": len(texts), "by_beam": by_beam}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    drawings = []
    for d in manifest["drawings"]:
        drawings.append(
            {
                "drawing_type": d["drawing_type"],
                "path": d["absolute_path"],
                "filename": d["filename"],
            }
        )

    # GT beams
    rows = json.loads(BAR_MATCHING.read_text(encoding="utf-8"))["rows"]
    gt = [
        r
        for r in rows
        if (r.get("bar_role") or "").upper() == "STIRRUP"
        and r.get("status") not in ("EXTRA", "ACCEPTABLE_EXTRA")
    ]
    gt_beams = sorted({r["beam_id"] for r in gt})
    details = {
        b["beam_id"]: b
        for b in json.loads(BEAM_DETAILS.read_text(encoding="utf-8"))["beam_details"]
    }

    # Prefer beams for spatial check: B1,B9,B10,B2,B4 (+ maybe B13)
    prefer = ["B1", "B9", "B10", "B2", "B4", "B13"]
    spatial_ids = [b for b in prefer if b in gt_beams][:6]
    spatial_beams = [details[b] for b in spatial_ids if b in details]

    per_drawing = []
    for d in drawings:
        label = d["drawing_type"]
        path = Path(d["path"])
        print(f"Scanning {label}: {path.name} ...")
        per_drawing.append(scan_dxf(path, label))

    reinf_path = Path(manifest["primary_reinforcement_drawing"])
    spatial = collect_nearby_texts(reinf_path, spatial_beams)

    # Aggregate callouts
    live_callouts = []
    unref_callouts = []
    legend_hits = []
    for s in per_drawing:
        live_callouts.extend(s["callout_in_live_drawing"])
        live_callouts.extend(s["callout_in_inserted_block_defs"])
        unref_callouts.extend(s["callout_in_unreferenced_block_defs"])
        for h in s["hits_msp_paperspace_inserts"] + s["hits_block_definitions"]:
            if "STIRRUP" in h["tags"] and "CALLOUT_YD@S" not in h["tags"]:
                legend_hits.append(h)

    beams_with_nearby_callout = [
        bid
        for bid, info in spatial["by_beam"].items()
        if info["has_stirrup_callout_nearby"]
    ]
    beams_without = [
        bid
        for bid, info in spatial["by_beam"].items()
        if not info["has_stirrup_callout_nearby"]
    ]

    # Verdict
    # A = no per-beam live callout text anywhere reachable near GT beams
    # B = live/reachable callout exists but R.1 misses it
    # C = mixed
    has_live_per_beam_callout = len(live_callouts) > 0 and any(
        h.get("x") is not None for h in live_callouts
    )
    # For Set1 we know live_callouts should be empty from Day-1; unref may have 2L-Y10
    if not live_callouts and not beams_with_nearby_callout:
        if unref_callouts or legend_hits:
            verdict = "A"
            confidence = "HIGH"
            nuance = (
                "No live/reachable per-beam stirrup callout text in modelspace, "
                "paperspace, or inserted-block virtual entities near any checked GT beam. "
                "Library/legend-only residue exists (unreferenced block def and/or "
                "'TYPICAL STIRRUP DETAILS' title) but is not placed on beam details — "
                "does not constitute a discoverable per-beam notation miss for R.1."
            )
        else:
            verdict = "A"
            confidence = "HIGH"
            nuance = "No stirrup-related callout text found in any form."
    elif live_callouts and not beams_with_nearby_callout:
        verdict = "B"
        confidence = "MEDIUM"
        nuance = "Callouts exist in live drawing but not near GT beam zones (wrong association region or shared schedule)."
    elif beams_with_nearby_callout and beams_without:
        verdict = "C"
        confidence = "HIGH"
        nuance = "Some GT beams have nearby callout text; others do not."
    elif beams_with_nearby_callout and not beams_without:
        verdict = "B"
        confidence = "HIGH"
        nuance = "Callouts exist near beams but R.1 did not surface them — notation-format / scan-scope miss."
    else:
        verdict = "A"
        confidence = "MEDIUM"
        nuance = "Defaulted to absence after inconclusive live-callout geometry."

    report = {
        "model_version": "9.1.0",
        "diagnostic": "Day-1 Addendum — Set 1 exhaustive raw-text stirrup sweep",
        "read_only": True,
        "code_modified": False,
        "config_modified": False,
        "pipeline_artefacts_modified": False,
        "stages_rerun": [],
        "step1_source_files": {
            "run_root": str(RUN_ROOT),
            "manifest": str(MANIFEST),
            "drawings": drawings,
        },
        "step2_per_drawing": [
            {
                "drawing_label": s["drawing_label"],
                "path": s["path"],
                "at_symbol_count": s["at_symbol_count"],
                "entity_type_counts": s["entity_type_counts"],
                "xref_notes": s["xref_notes"],
                "summary_tags": s["summary_tags"],
                "n_hits_live": len(s["hits_msp_paperspace_inserts"]),
                "n_hits_block_defs": len(s["hits_block_definitions"]),
                "hits_live": s["hits_msp_paperspace_inserts"],
                "hits_block_definitions": s["hits_block_definitions"],
                "callout_live": s["callout_in_live_drawing"],
                "callout_unreferenced_block_defs": s["callout_in_unreferenced_block_defs"],
            }
            for s in per_drawing
        ],
        "step2_aggregate": {
            "live_stirrup_callouts": live_callouts,
            "unreferenced_block_callouts": unref_callouts,
            "legend_stirrup_hits": legend_hits,
        },
        "step3_spatial_crosscheck": {
            "beams_checked": spatial_ids,
            "reinforcement_dxf": str(reinf_path),
            "results": spatial["by_beam"],
            "beams_with_nearby_callout": beams_with_nearby_callout,
            "beams_without_nearby_callout": beams_without,
        },
        "step4_verdict": {
            "verdict": verdict,
            "confidence": confidence,
            "nuance": nuance,
            "gt_stirrup_rows": len(gt),
            "gt_stirrup_beams": gt_beams,
        },
    }

    # Markdown
    lines = [
        "# Day-1 Addendum — Set 1 Stirrup Notation Exhaustive Raw-Text Sweep",
        "",
        "**MODEL_VERSION:** 9.1.0 (read-only; no code/config/artefact modifications)",
        "",
        f"## Verdict: **{verdict}** (confidence: {confidence})",
        "",
        nuance,
        "",
        "### Mapping to Track 1",
        "",
    ]
    if verdict == "A":
        lines += [
            "**Strengthens Track 1 for Set 1 specifically:** stirrups are not communicated "
            "as per-beam `2L-Y…@…C/C` / `Y…@…C/C` text on the live drawing. Geometry / "
            "typical-detail inference is required; a small R.1 text-scan patch would not "
            "recover the 23 GT stirrup rows.",
            "",
        ]
    elif verdict == "B":
        lines += [
            "**Third failure mode (NOTATION-FORMAT MISS):** prefer a targeted discovery "
            "patch before full geometry inference for Set 1.",
            "",
        ]
    else:
        lines += ["**MIXED** — see per-beam split below.", ""]

    lines += [
        "## Step 1 — Confirmed Set 1 source files",
        "",
        f"- run_root: `{RUN_ROOT}`",
        f"- manifest: `{MANIFEST}`",
        "",
    ]
    for d in drawings:
        lines.append(f"- **{d['drawing_type']}:** `{d['path']}`")

    lines += ["", "## Step 2 — Exhaustive match list", ""]
    for s in per_drawing:
        lines += [
            f"### {s['drawing_label']}",
            "",
            f"- path: `{s['path']}`",
            f"- `@` symbol count (all scanned text): **{s['at_symbol_count']}**",
            f"- XREF notes: {s['xref_notes'] or ['(none)']}",
            f"- tag summary: `{s['summary_tags']}`",
            "",
            "#### Live hits (modelspace / paperspace / INSERT.virtual / attribs)",
            "",
        ]
        live = s["hits_msp_paperspace_inserts"]
        if not live:
            lines.append("_No substring matches in live drawing graph._")
        else:
            lines.append(
                "| String | Tags | Entity | Layer | Block | Depth | Source | x | y |"
            )
            lines.append("|---|---|---|---|---|---:|---|---:|---:|")
            for h in live:
                lines.append(
                    f"| `{h['matched_string'][:80]}` | {','.join(h['tags'])} | "
                    f"{h['entity_type']} | {h['layer']} | `{h['containing_block']}` | "
                    f"{h['nesting_depth']} | {h['source']} | {h['x']} | {h['y']} |"
                )
        lines += ["", "#### Block-definition hits (includes unreferenced)", ""]
        defs = s["hits_block_definitions"]
        if not defs:
            lines.append("_No substring matches in block definitions._")
        else:
            lines.append(
                "| String | Tags | Entity | Layer | Block | Inserted? | Depth | x | y |"
            )
            lines.append("|---|---|---|---|---|---|---:|---:|---:|")
            for h in defs:
                lines.append(
                    f"| `{h['matched_string'][:80]}` | {','.join(h['tags'])} | "
                    f"{h['entity_type']} | {h['layer']} | `{h['containing_block']}` | "
                    f"{h.get('block_is_inserted_in_msp')} | {h['nesting_depth']} | "
                    f"{h['x']} | {h['y']} |"
                )
        lines.append("")

    lines += [
        "## Step 3 — Spatial cross-check near GT stirrup beams",
        "",
        f"Reinforcement DXF: `{reinf_path}`",
        "",
        "Beams checked: " + ", ".join(spatial_ids),
        "",
    ]
    for bid in spatial_ids:
        info = spatial["by_beam"][bid]
        lines += [
            f"### {bid}",
            "",
            f"- centroid: {info['centroid']}, search radius: {info['radius']}",
            f"- nearby text entities: {info['nearby_text_count']}",
            f"- has stirrup callout nearby: **{info['has_stirrup_callout_nearby']}**",
            "",
            "Nearest texts:",
        ]
        if not info["nearest_texts"]:
            lines.append("- _(none)_")
        for n in info["nearest_texts"][:12]:
            lines.append(
                f"- d={n['dist_to_centroid']}: `{n['text']}` "
                f"[{n['entity_type']}/{n['layer']}/depth={n['depth']}]"
            )
        if info["stirrup_related_nearby"]:
            lines.append("Stirrup-related nearby:")
            for n in info["stirrup_related_nearby"]:
                lines.append(f"- `{n['text']}`")
        lines.append("")

    lines += [
        "## Step 4 — Verdict detail",
        "",
        f"- **Verdict:** {verdict}",
        f"- **Confidence:** {confidence}",
        f"- Live (placed) stirrup callouts found: {len(live_callouts)}",
        f"- Unreferenced block-def callouts: {len(unref_callouts)}",
        f"- Legend/title STIRRUP hits (non-callout): {len(legend_hits)}",
        f"- Spatial beams with nearby callout: {beams_with_nearby_callout or 'none'}",
        f"- Spatial beams without nearby callout: {beams_without}",
        "",
    ]
    if verdict == "B" or verdict == "C":
        lines += [
            "### Recommended discovery patch scope (NOT implemented)",
            "",
            "- Entity types / nesting to add: INSERT.virtual_entities + ATTRIB (and nested INSERT)",
            "- Estimated effort: **~1–2 days**",
            "",
        ]
    else:
        lines += [
            "### Discovery patch recommendation",
            "",
            "**Not recommended as the Set 1 recovery path.** Expanding R.1 to "
            "INSERT.virtual_entities would still yield **0** placed stirrup callouts on "
            "Set 1 beam details (Day-1 + this sweep). Optional hygiene: ignore "
            "unreferenced block-library strings. Set 1 volume recovery belongs to "
            "**Track 1 geometric / typical-detail inference**.",
            "",
        ]

    lines += [
        "## Integrity",
        "",
        "- NO pipeline code modified",
        "- NO config modified",
        "- NO production artefacts rewritten",
        "- NO stages re-run",
        "- Raw DXF read directly with ezdxf/recover — independent of R.1 pipeline",
        f"- Script: `{Path(__file__).resolve()}`",
        "",
    ]

    json_path = OUT_DIR / "day1_set1_stirrup_rawtext_addendum.json"
    md_path = OUT_DIR / "day1_set1_stirrup_rawtext_addendum.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"VERDICT={verdict} confidence={confidence}")
    print(f"live_callouts={len(live_callouts)} unref_callouts={len(unref_callouts)} legend={len(legend_hits)}")


if __name__ == "__main__":
    main()
