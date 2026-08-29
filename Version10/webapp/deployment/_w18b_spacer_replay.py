"""W.18B local replay: Galera B1/B10/B23 through M.2 → L.2 → VB.1 → BBS.

Reconstructs EngineeringBarModels from W.18A forensic identities (pre-hybrid
bar_id role token) and PieceGenerator geometric extents (0.25L / 0.75L).
Does not mutate production data. Does not re-run DXF extraction.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
import types
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
ENGINE = ROOT / "Version10" / "src"
DEPLOY = ROOT / "Version10" / "webapp" / "deployment"
FORENSIC = DEPLOY / "W18A_SPACER_FORENSIC_TRACE.json"
OUT_JSON = DEPLOY / "W18B_SPACER_VALIDATION_TRACE.json"
VB1 = ENGINE / "PhaseVB.1_production_output_completion"
R13 = ENGINE / "PhaseR1.3_pipeline_integration"
FOCUS = ("B1", "B10", "B23")

sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(VB1))

from PhaseV9_spacer_rule.r13_injector import inject_spacers  # noqa: E402
from PhaseV9_spacer_rule.spacer_engine import (  # noqa: E402
    SPACER_DIA_MM,
    SPACER_SPACING_MM,
    spacer_quantity,
    spacer_raw_quantity,
)
from bbs_completion_engine import BBSCompletionEngine  # noqa: E402
from steel_weight_completion import SteelWeightCompletion  # noqa: E402


def _load_r13():
    pkg_name = "PhaseR13W18BReplay"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(R13)]
        pkg.__package__ = pkg_name
        sys.modules[pkg_name] = pkg
    for sub in ("engineering_bar_model", "engineering_bar_builder"):
        key = f"{pkg_name}.{sub}"
        if key in sys.modules:
            continue
        import importlib.util
        spec = importlib.util.spec_from_file_location(key, R13 / f"{sub}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = pkg_name
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return (
        sys.modules[f"{pkg_name}.engineering_bar_builder"].EngineeringBarBuilder,
        sys.modules[f"{pkg_name}.engineering_bar_model"].EngineeringBarModel,
        sys.modules[f"{pkg_name}.engineering_bar_model"].BeamEngineeringModel,
    )


EngineeringBarBuilder, EngineeringBarModel, BeamEngineeringModel = _load_r13()


def _extents_from_piece_type(piece_type: str, span: float) -> Tuple[Optional[float], Optional[float]]:
    pt = str(piece_type or "").upper()
    if pt in ("TOP_MAIN", "BOTTOM_MAIN", "CONTINUOUS_BAR", "CONTINUOUS"):
        return 0.0, float(span)
    if pt.endswith("_LEFT") or pt in ("TOP_EXTRA_LEFT", "BOTTOM_EXTRA_LEFT"):
        return 0.0, float(span) * 0.25
    if pt.endswith("_RIGHT") or pt in ("TOP_EXTRA_RIGHT", "BOTTOM_EXTRA_RIGHT"):
        return float(span) * 0.75, float(span)
    return None, None


def _rebuild_beam(rec: Dict[str, Any]) -> Any:
    beam_id = rec["beam_id"]
    geom = rec["geometry"]
    span = float(geom["clear_span_mm"])
    bars = []
    pieces = []
    for bar in rec.get("longitudinal_reinforcement_records") or []:
        role = str(bar.get("bar_id_role_token") or "")
        if role == "SPACER_BAR":
            continue
        pt = str(bar.get("piece_type") or "")
        start, end = _extents_from_piece_type(pt, span)
        pieces.append({
            "piece_id": bar.get("source_bar_id"),
            "piece_type": pt,
            "bar_label": bar.get("bar_label"),
            "bar_role": role,
            "diameter_mm": bar.get("diameter_mm"),
            "quantity": bar.get("quantity"),
            "fabrication_cut_length_mm": bar.get("cut_length_mm"),
            "piece_start_mm": start,
            "piece_end_mm": end,
            "physical_overlap_length_mm": (end - start) if start is not None and end is not None else None,
        })
        bars.append(EngineeringBarModel(
            beam_id=beam_id,
            bar_role=role,
            diameter_mm=float(bar.get("diameter_mm") or 0),
            quantity=int(bar.get("quantity") or 1),
            zone=str(bar.get("position_zone") or "TOP_ZONE"),
            bar_label=str(bar.get("bar_label") or ""),
            source_phase="R.1.3",
            engineering_metadata={
                "piece_type": pt,
                "piece_start_mm": start,
                "piece_end_mm": end,
                "cut_length_mm": bar.get("cut_length_mm"),
                "piece_id": bar.get("source_bar_id"),
                "detail_id": bar.get("source_bar_id"),
            },
        ))
    beam = BeamEngineeringModel(
        beam_id=beam_id,
        beam_name=beam_id,
        bars=bars,
        geometry={
            "width_mm": geom.get("width_mm"),
            "depth_mm": geom.get("depth_mm"),
            "clear_span_mm": span,
        },
    )
    return beam, pieces


def _audit_beam(beam_id: str, pieces, injected, l2_rec, bbs_rows, report_pb) -> Dict[str, Any]:
    spacers = [b for b in injected.bars if b.bar_role == "SPACER_BAR"]
    meta = (spacers[0].engineering_metadata if spacers else {}) or {}
    zones = list(meta.get("zones") or [])
    overlap_zones = []
    for z in zones:
        length = float(z.get("zone_length_mm") or 0)
        overlap_zones.append({
            "zone_start_mm": z.get("zone_start_mm"),
            "zone_end_mm": z.get("zone_end_mm"),
            "physical_overlap_length_mm": length,
            "fabrication_cut_length_mm": "NOT_USED",
            "raw_quantity": z.get("raw_quantity"),
            "rounded_quantity": z.get("quantity"),
        })
    l2_spacers = l2_rec.get("spacer_bars") or []
    spacer_bbs = [
        {
            "description": r.description,
            "quantity": r.quantity,
            "cut_length_m": r.cut_length_m,
            "aggregation_key": f"{beam_id}|SPACER|{SPACER_DIA_MM}|{r.cut_length_m}",
        }
        for r in bbs_rows
        if (not r.is_beam_header) and r.beam_id == beam_id and r.description == "Spacer bars"
    ]
    hooked_cuts = [p.get("fabrication_cut_length_mm") for p in pieces if "EXTRA" in str(p.get("bar_role") or "")]
    return {
        "beam_id": beam_id,
        "pieces": pieces,
        "m2_zone_rows_before_aggregation": report_pb.get("zone_rows"),
        "m2_zone_quantities": report_pb.get("zone_quantities"),
        "overlap_zones": overlap_zones,
        "spacer_cut_length_mm": meta.get("cut_length_mm"),
        "extent_fallback": meta.get("extent_fallback"),
        "l2_spacer_count": len(l2_spacers),
        "l2_spacer_quantity": [s.get("quantity") for s in l2_spacers],
        "l2_piece_start_preserved_on_longitudinal": any(
            (b.get("piece_start_mm") is not None)
            for k in ("top_main_bars", "top_extra_bars")
            for b in (l2_rec.get(k) or [])
        ),
        "l2_zone_metadata_on_spacer": bool(l2_spacers and l2_spacers[0].get("zones")),
        "bbs": spacer_bbs,
        "hooked_fabrication_cuts_present_but_not_used_as_overlap": hooked_cuts,
        "w18a_was": {
            "B1": [3, 7, 3],
            "B10": [4],
            "B23": [5],
        }.get(beam_id),
    }


def main() -> Dict[str, Any]:
    forensic = json.loads(FORENSIC.read_text(encoding="utf-8"))
    focused = {r["beam_id"]: r for r in forensic.get("focused_beams") or [] if r.get("beam_id") in FOCUS}

    rebuilt = []
    piece_map = {}
    for bid in FOCUS:
        beam, pieces = _rebuild_beam(focused[bid])
        rebuilt.append(beam)
        piece_map[bid] = pieces

    cover = 30.0
    injected, inj_report = inject_spacers(rebuilt, cover, bar_model_cls=EngineeringBarModel)
    per_beam = {p["beam_id"]: p for p in inj_report.get("per_beam") or []}

    builder = EngineeringBarBuilder.__new__(EngineeringBarBuilder)
    builder._ctx = {"cover_beam_mm": cover}
    l2 = builder.to_l2_compatible(injected)

    tmp = Path(tempfile.gettempdir()) / "w18b_galera_l2.json"
    tmp.write_text(json.dumps(l2, indent=2), encoding="utf-8")
    summary = SteelWeightCompletion(tmp).compute()
    bbs_rows = BBSCompletionEngine(summary, frame_type="GF").generate()

    audits = []
    l2_by_id = {m["beam_id"]: m for m in l2.get("models") or []}
    inj_by_id = {b.beam_id: b for b in injected}
    for bid in FOCUS:
        audits.append(_audit_beam(
            bid, piece_map[bid], inj_by_id[bid], l2_by_id[bid], bbs_rows, per_beam.get(bid) or {},
        ))

    rounding = {
        "rule": "round_half_up((overlap_mm / 1000) + 1)",
        "1040_mm": {"raw": spacer_raw_quantity(1040), "qty": spacer_quantity(1040)},
        "1500_mm": {"raw": spacer_raw_quantity(1500), "qty": spacer_quantity(1500)},
        "2490_mm": {"raw": spacer_raw_quantity(2490), "qty": spacer_quantity(2490)},
        "2500_mm": {"raw": spacer_raw_quantity(2500), "qty": spacer_quantity(2500)},
        "bankers_round_2_5": round(2.5),
        "estimator_round_half_up_2_5": int(math.floor(2.5 + 0.5)),
        "dia_mm": SPACER_DIA_MM,
        "spacing_mm": SPACER_SPACING_MM,
    }

    out = {
        "phase": "W.18B",
        "production_mutation": "NO",
        "l2_temp_path": str(tmp),
        "source": "W.18A forensic identities + PieceGenerator extents + live M.2/L.2/VB.1/BBS",
        "injector_report": inj_report,
        "rounding": rounding,
        "beams": audits,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    result = main()
    print(json.dumps({
        "wrote": str(OUT_JSON),
        "rounding": result["rounding"],
        "beams": [
            {
                "beam_id": b["beam_id"],
                "zone_qtys": b["m2_zone_quantities"],
                "l2_qty": b["l2_spacer_quantity"],
                "bbs": b["bbs"],
                "overlap_zones": b["overlap_zones"],
                "cut_mm": b["spacer_cut_length_mm"],
            }
            for b in result["beams"]
        ],
    }, indent=2))
