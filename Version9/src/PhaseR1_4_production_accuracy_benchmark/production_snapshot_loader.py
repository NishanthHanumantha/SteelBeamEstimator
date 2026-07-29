"""
Load production pipeline artefacts into ProductionSnapshot.
MODEL_VERSION: 8.6.0

Read-only — does not modify the production pipeline.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from models import ProductionBeamSnapshot, ProductionSnapshot

MODEL_VERSION = "8.6.0"


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class ProductionSnapshotLoader:
    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root)
        self.out = self.v8 / "data" / "output"

    def load(self) -> ProductionSnapshot:
        sources: Dict[str, Any] = {}

        intents_path = self.out / "PhaseR1_2C_engineering_intent_resolution" / "engineering_intents.json"
        details_path = self.out / "PhaseR1_2D_reinforcement_detailing" / "reinforcement_details.json"
        pieces_path = self.out / "PhaseR1_3_reinforcement_piece_generation" / "piece_generation_report.json"
        piece_trace_path = self.out / "PhaseR1_3_reinforcement_piece_generation" / "piece_traceability.json"
        bars_path = self.out / "PhaseR1.3_pipeline_integration" / "engineering_bar_models.json"
        integ_path = self.out / "PhaseR1.3_pipeline_integration" / "integration_summary.json"
        piece_summary_path = self.out / "PhaseR1_3_reinforcement_piece_generation" / "piece_summary.json"
        workbook_path = self.out / "Production_Output" / "Estimation_Output.xlsx"

        intents_data = _read_json(intents_path) or {}
        details_data = _read_json(details_path) or {}
        pieces_data = _read_json(pieces_path) or {}
        piece_trace = _read_json(piece_trace_path) or {}
        bars_data = _read_json(bars_path) or {}
        integ = _read_json(integ_path) or {}
        piece_summary = _read_json(piece_summary_path) or {}

        intents = intents_data.get("intents") or []
        details = details_data.get("details") or []
        pieces = pieces_data.get("pieces") or []
        if not pieces and isinstance(piece_trace, dict):
            pieces = piece_trace.get("pieces") or piece_trace.get("rows") or []
        if not pieces and isinstance(piece_trace, list):
            pieces = piece_trace

        bar_beams = bars_data.get("beams") or []
        engineering_bars: List[Dict[str, Any]] = []
        for bm in bar_beams:
            for bar in bm.get("bars") or []:
                engineering_bars.append(bar)

        sources.update({
            "intents": str(intents_path) if intents_path.exists() else None,
            "details": str(details_path) if details_path.exists() else None,
            "pieces": str(pieces_path) if pieces_path.exists() else None,
            "engineering_bars": str(bars_path) if bars_path.exists() else None,
            "integration_summary": str(integ_path) if integ_path.exists() else None,
            "workbook": str(workbook_path) if workbook_path.exists() else None,
        })

        steel_summary = self._steel_summary(integ, bars_data, engineering_bars)
        bbs = self._bbs_summary(integ)
        workbook = {
            "path": str(workbook_path) if workbook_path.exists() else None,
            "exists": workbook_path.exists(),
            "size_bytes": workbook_path.stat().st_size if workbook_path.exists() else 0,
        }

        beams = self._assemble_beams(intents, details, pieces, bar_beams, engineering_bars)

        snap = ProductionSnapshot(
            intents=intents,
            details=details,
            pieces=pieces,
            engineering_bars=engineering_bars,
            beams=beams,
            steel_summary=steel_summary,
            bbs=bbs,
            workbook=workbook,
            sources=sources,
            model_version=MODEL_VERSION,
        )
        # attach piece summary counts when piece list empty
        if piece_summary:
            snap.steel_summary["piece_summary"] = piece_summary
        return snap

    def _steel_summary(
        self,
        integ: Dict[str, Any],
        bars_data: Dict[str, Any],
        engineering_bars: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        after = (integ.get("statistics") or {}).get("after") or integ.get("comparison", {}).get("after") or {}
        total_kg = float(after.get("total_steel_kg") or 0.0)
        dia_kg = self._diameter_kg_from_bars(engineering_bars)
        role_counts = ((integ.get("statistics") or {}).get("engineering_bar_counts") or {}).get("role_counts") or {}
        return {
            "total_kg": round(total_kg, 3),
            "total_mt": round(total_kg / 1000.0, 6) if total_kg else 0.0,
            "diameter_kg": dia_kg,
            "role_counts": role_counts,
            "engineering_bar_count": len(engineering_bars),
            "beam_count": bars_data.get("beam_count") or len(bars_data.get("beams") or []),
        }

    @staticmethod
    def _diameter_kg_from_bars(engineering_bars: List[Dict[str, Any]]) -> Dict[str, float]:
        """Estimate diameter kg from EngineeringBar cut lengths when available."""
        unit = {8: 0.395, 10: 0.617, 12: 0.888, 16: 1.58, 20: 2.47, 25: 3.85, 32: 6.31}
        totals: Dict[int, float] = defaultdict(float)
        for bar in engineering_bars:
            try:
                dia = int(round(float(bar.get("diameter_mm") or 0)))
            except (TypeError, ValueError):
                continue
            if dia not in unit:
                continue
            meta = bar.get("engineering_metadata") or {}
            cut_mm = meta.get("cut_length_mm")
            qty = float(bar.get("quantity") or 0)
            if cut_mm is None or qty <= 0:
                continue
            totals[dia] += (float(cut_mm) / 1000.0) * qty * unit[dia]
        return {str(k): round(v, 3) for k, v in sorted(totals.items()) if v > 0}

    def _bbs_summary(self, integ: Dict[str, Any]) -> Dict[str, Any]:
        after = (integ.get("statistics") or {}).get("after") or integ.get("comparison", {}).get("after") or {}
        return {
            "bbs_rows": after.get("bbs_rows") or 0,
            "beams_reaching_bbs": after.get("beams_reaching_bbs") or 0,
        }

    def _assemble_beams(
        self,
        intents: List[Dict[str, Any]],
        details: List[Dict[str, Any]],
        pieces: List[Dict[str, Any]],
        bar_beams: List[Dict[str, Any]],
        engineering_bars: List[Dict[str, Any]],
    ) -> List[ProductionBeamSnapshot]:
        by_beam: Dict[str, ProductionBeamSnapshot] = {}

        def ensure(bid: str) -> ProductionBeamSnapshot:
            if bid not in by_beam:
                by_beam[bid] = ProductionBeamSnapshot(beam_id=bid)
            return by_beam[bid]

        for it in intents:
            bid = str(it.get("beam_id") or "").upper()
            if bid:
                ensure(bid).intents.append(it)
        for dt in details:
            bid = str(dt.get("beam_id") or "").upper()
            if bid:
                ensure(bid).details.append(dt)
        for pc in pieces:
            bid = str(pc.get("beam_id") or "").upper()
            if bid:
                ensure(bid).pieces.append(pc)

        for bm in bar_beams:
            bid = str(bm.get("beam_id") or "").upper()
            if not bid:
                continue
            snap = ensure(bid)
            snap.geometry = bm.get("geometry") or {}
            bars = bm.get("bars") or []
            snap.engineering_bars = bars
            # steel not always on bar; leave 0 unless metadata has weight
            steel = 0.0
            dia: Dict[int, float] = defaultdict(float)
            for bar in bars:
                # no weight on bar model — quantity only
                pass
            snap.steel_kg = round(steel, 3)
            snap.diameter_kg = dict(dia)

        return [by_beam[k] for k in sorted(by_beam.keys())]
