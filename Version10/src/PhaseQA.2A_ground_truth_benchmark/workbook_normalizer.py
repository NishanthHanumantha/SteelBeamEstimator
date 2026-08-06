"""
workbook_normalizer.py — Parse Estimator / Model Excel into NormalizedWorkbook.
Reuses Phase R.1.4 OfficialModelBuilder (read-only). MODEL_VERSION: 8.9.1
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from gt_models import BarRecord, BeamRecord, NormalizedWorkbook

MODEL_VERSION = "9.1.0"

_R14 = Path(__file__).resolve().parents[1] / "PhaseR1_4_production_accuracy_benchmark"


def _ensure_r14() -> None:
    p = str(_R14)
    if p not in sys.path:
        sys.path.insert(0, p)


def _norm_id(raw: str) -> str:
    s = str(raw or "").strip().upper()
    s = s.replace(" ", "").replace("_", "")
    return s


def _role_family(role: str, description: str = "") -> str:
    _ensure_r14()
    from terminology_mapper import map_official_description  # type: ignore

    r = (role or "").upper().strip()
    if r and r != "UNKNOWN":
        if r.startswith("TOP_EXTRA"):
            return "TOP_EXTRA"
        if r.startswith("TOP"):
            return "TOP_MAIN"
        if r.startswith("BOTTOM_EXTRA"):
            return "BOTTOM_EXTRA"
        if r.startswith("BOTTOM"):
            return "BOTTOM_MAIN"
        if "HOOK" in r:
            return "STIRRUP_HOOK"
        if "STIRRUP" in r:
            return "STIRRUP"
        if "SPACER" in r:
            return "SPACER_BAR"
        if "SIDE" in r or r in ("SFR", "SIDE_FACE_REINFORCEMENT"):
            return "SIDE_FACE_REINFORCEMENT"
        if "CONTINUITY" in r or "LAP" in r:
            return "CONTINUITY"
        if "DEVELOPMENT" in r or "ANCHOR" in r:
            return "DEVELOPMENT"
        return r
    mapped = map_official_description(description or "")
    return mapped if mapped != "UNKNOWN" else _heuristic_role(description)


def _heuristic_role(description: str) -> str:
    t = (description or "").lower()
    if "top" in t and "extra" in t:
        return "TOP_EXTRA"
    if "bottom" in t and "extra" in t:
        return "BOTTOM_EXTRA"
    if re.search(r"\btop\b", t):
        return "TOP_MAIN"
    if re.search(r"\bbottom\b", t):
        return "BOTTOM_MAIN"
    if "stirrup" in t or "stirup" in t:
        return "STIRRUP"
    if "spacer" in t:
        return "SPACER_BAR"
    if "side" in t or "sfr" in t:
        return "SIDE_FACE_REINFORCEMENT"
    return "UNKNOWN"


def _dia(val: Any, diameter_kg: Optional[Dict] = None) -> Optional[int]:
    if val is not None:
        try:
            v = int(round(float(val)))
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    if diameter_kg:
        nonzero = []
        for k, w in diameter_kg.items():
            try:
                if float(w or 0) > 0:
                    nonzero.append(int(k))
            except (TypeError, ValueError):
                pass
        if len(nonzero) == 1:
            return nonzero[0]
    return None


def _aliases(beam_id: str) -> List[str]:
    nid = _norm_id(beam_id)
    al = {nid, beam_id.strip().upper()}
    # B-17 / B17 / BEAM17
    m = re.match(r"^(?:BEAM)?B?-?(\d+[A-Z]?)$", nid)
    if m:
        num = m.group(1)
        al.update({f"B{num}", f"B-{num}", f"BEAM{num}", num})
    return sorted(al)


class WorkbookNormalizer:
    """Build NormalizedWorkbook from Estimator or Model Excel."""

    def normalize(self, workbook_path: Path, source_label: str) -> NormalizedWorkbook:
        _ensure_r14()
        from official_model_builder import OfficialModelBuilder  # type: ignore

        path = Path(workbook_path)
        official = OfficialModelBuilder().build(path)

        beams: List[BeamRecord] = []
        dia_totals: Dict[int, float] = {}

        for ob in official.beams or []:
            bid = _norm_id(ob.beam_id)
            if not bid:
                continue
            bars: List[BarRecord] = []
            for row in ob.reinforcement_rows or []:
                role = _role_family(
                    getattr(row, "role", "") or "",
                    getattr(row, "description", "") or "",
                )
                dkg = getattr(row, "diameter_kg", None) or {}
                dia = _dia(getattr(row, "diameter", None) or getattr(row, "diameter_column", None), dkg)
                qty = getattr(row, "number_of_bars", None)
                try:
                    qty_f = float(qty) if qty is not None else 0.0
                except (TypeError, ValueError):
                    qty_f = 0.0
                steel = float(getattr(row, "steel", 0.0) or 0.0)
                if steel <= 0 and dkg:
                    steel = sum(float(v or 0) for v in dkg.values())
                cut = getattr(row, "cut_length", None) or getattr(row, "total_length", None)
                try:
                    cut_f = float(cut) if cut is not None else None
                except (TypeError, ValueError):
                    cut_f = None
                bars.append(BarRecord(
                    beam_id=bid,
                    bar_role=role,
                    diameter=dia,
                    quantity=qty_f,
                    shape="",
                    cut_length=cut_f,
                    steel_weight=steel,
                    remarks="",
                    source_description=getattr(row, "description", "") or "",
                    source_row=int(getattr(row, "source_row", 0) or 0),
                ))

            beam_dia: Dict[int, float] = {}
            for k, v in (getattr(ob, "diameter_kg", None) or {}).items():
                try:
                    ik, fv = int(k), float(v or 0)
                    if fv > 0:
                        beam_dia[ik] = beam_dia.get(ik, 0.0) + fv
                        dia_totals[ik] = dia_totals.get(ik, 0.0) + fv
                except (TypeError, ValueError):
                    pass
            if not beam_dia:
                for bar in bars:
                    if bar.diameter and bar.steel_weight:
                        beam_dia[bar.diameter] = beam_dia.get(bar.diameter, 0.0) + bar.steel_weight
                        dia_totals[bar.diameter] = dia_totals.get(bar.diameter, 0.0) + bar.steel_weight

            steel_kg = float(getattr(ob, "total_steel_kg", 0) or 0)
            if steel_kg <= 0:
                steel_kg = sum(beam_dia.values()) or sum(b.steel_weight for b in bars)

            beams.append(BeamRecord(
                beam_id=bid,
                beam_length=getattr(ob, "length_m", None),
                beam_depth=getattr(ob, "depth_m", None),
                beam_width=getattr(ob, "width_m", None),
                steel_kg=steel_kg,
                diameter_kg=beam_dia,
                bars=bars,
                source_sheet=getattr(ob, "source_sheet", "") or "",
                aliases=_aliases(bid),
            ))

        summary = official.steel_summary
        total_kg = float(getattr(summary, "total_kg", 0) or 0)
        total_mt = float(getattr(summary, "total_mt", 0) or 0)
        sum_dia = getattr(summary, "diameter_summary", None) or {}
        if not dia_totals and sum_dia:
            for k, v in sum_dia.items():
                try:
                    ik, fv = int(k), float(v or 0)
                    # Heuristic: small values are MT
                    dia_totals[ik] = fv * 1000.0 if 0 < fv < 50 else fv
                except (TypeError, ValueError):
                    pass
        if total_kg <= 0:
            total_kg = sum(b.steel_kg for b in beams) or sum(dia_totals.values())
        if total_mt <= 0:
            total_mt = total_kg / 1000.0

        return NormalizedWorkbook(
            source_path=str(path.resolve()),
            source_label=source_label,
            project_name=getattr(getattr(official, "project", None), "project_name", "") or "",
            sheet_names=list(getattr(getattr(official, "project", None), "sheet_names", []) or []),
            beams=beams,
            total_steel_kg=round(total_kg, 3),
            total_steel_mt=round(total_mt, 4),
            diameter_kg={k: round(v, 3) for k, v in sorted(dia_totals.items())},
        )
