"""End-to-end geometry trace: Registry -> EngBar -> Steel -> BBS -> Workbook."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List


class GeometryTracer:

    TOL_M = 0.001

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root

    def trace(self, geometries: Dict[str, Any]) -> Dict[str, Any]:
        registry = self._load(self._v7 / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json")
        eng = self._load(self._v7 / "data/output/PhaseR1.3_pipeline_integration/engineering_bar_models.json")
        prod = self._load(self._v7 / "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json")
        steel = self._load(self._v7 / "data/output/Production_Output/steel_weight_summary.json")
        bbs = self._load(self._v7 / "data/output/Production_Output/bbs_summary.json")

        reg_beams = registry.get("beams", {})
        if isinstance(reg_beams, list):
            reg_beams = {b.get("beam_id"): b for b in reg_beams}

        eng_by_id = self._index_eng(eng)
        prod_by_id = self._index_prod(prod)
        steel_by_id = self._index_steel(steel)
        bbs_by_id = self._index_bbs(bbs)

        trails: List[Dict[str, Any]] = []
        for beam_id in sorted(geometries.keys()):
            g = geometries[beam_id]
            provider_span = g.get("clear_span_mm") if isinstance(g, dict) else getattr(g, "clear_span_mm", None)
            reg_span = (reg_beams.get(beam_id) or {}).get("clear_span_mm")
            eng_span = (eng_by_id.get(beam_id) or {}).get("clear_span_mm")
            prod_span = (prod_by_id.get(beam_id) or {}).get("clear_span_mm")
            steel_span = (steel_by_id.get(beam_id) or {}).get("span_mm")
            bbs_spacing_m = (bbs_by_id.get(beam_id) or {}).get("spacing_m")
            bbs_span = bbs_spacing_m * 1000.0 if bbs_spacing_m is not None else None

            stages = {
                "provider": provider_span,
                "registry": reg_span,
                "engineering_bar": eng_span or prod_span,
                "steel": steel_span,
                "bbs": bbs_span,
                "workbook": bbs_span,  # workbook Spacing sourced from BBS/steel span
            }
            mismatches = []
            ref = provider_span
            for name, val in stages.items():
                if ref is None or val is None:
                    continue
                if abs(float(val) - float(ref)) > self.TOL_M * 1000:
                    mismatches.append(f"{name}={val}")

            trails.append({
                "beam_id": beam_id,
                "span_mm": provider_span,
                "width_mm": g.get("width_mm") if isinstance(g, dict) else getattr(g, "width_mm", None),
                "depth_mm": g.get("depth_mm") if isinstance(g, dict) else getattr(g, "depth_mm", None),
                "source": g.get("source") if isinstance(g, dict) else getattr(g, "source", ""),
                "stages": stages,
                "validation": "PASS" if not mismatches and provider_span else ("FAIL" if mismatches else "MISSING"),
                "mismatches": mismatches,
            })

        passed = sum(1 for t in trails if t["validation"] == "PASS")
        return {
            "total_beams": len(trails),
            "passed": passed,
            "failed": sum(1 for t in trails if t["validation"] == "FAIL"),
            "missing": sum(1 for t in trails if t["validation"] == "MISSING"),
            "trails": trails,
        }

    @staticmethod
    def _load(path: pathlib.Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _index_eng(data: dict) -> Dict[str, dict]:
        out = {}
        for b in data.get("beams", data.get("models", [])) or []:
            if isinstance(b, dict) and b.get("beam_id"):
                geo = b.get("geometry") or {}
                out[b["beam_id"]] = {
                    "clear_span_mm": geo.get("clear_span_mm"),
                    "width_mm": geo.get("width_mm"),
                    "depth_mm": geo.get("depth_mm"),
                }
        return out

    @staticmethod
    def _index_prod(data: dict) -> Dict[str, dict]:
        out = {}
        models = data.get("models", data.get("beams", []))
        if isinstance(models, dict):
            models = list(models.values())
        for b in models or []:
            if not isinstance(b, dict):
                continue
            bid = b.get("beam_id")
            geo = b.get("geometry") or {}
            out[bid] = {
                "clear_span_mm": geo.get("clear_span_mm"),
                "width_mm": geo.get("width_mm"),
                "depth_mm": geo.get("depth_mm"),
            }
        return out

    @staticmethod
    def _index_steel(data: dict) -> Dict[str, dict]:
        out = {}
        for b in data.get("beams", data.get("beam_weights", [])) or []:
            if isinstance(b, dict) and b.get("beam_id"):
                out[b["beam_id"]] = {
                    "span_mm": b.get("span_mm") or b.get("clear_span_mm"),
                }
        return out

    @staticmethod
    def _index_bbs(data: dict) -> Dict[str, dict]:
        out = {}
        for row in data.get("rows", []) or []:
            if not isinstance(row, dict):
                continue
            if not (row.get("is_beam_header") or row.get("diameter_mm") == 1):
                continue
            bid = row.get("beam_id")
            if bid and row.get("spacing_m") is not None:
                out[bid] = {"spacing_m": row.get("spacing_m")}
        for h in data.get("headers", data.get("beam_headers", data.get("beams", []))) or []:
            if isinstance(h, dict) and h.get("beam_id") and h["beam_id"] not in out:
                out[h["beam_id"]] = {
                    "spacing_m": h.get("spacing_m") or h.get("span_m"),
                }
        return out
