"""Build EngineeringBarModel from R.1 reinforcement discovery."""
from __future__ import annotations
import json
import pathlib
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .engineering_bar_model import EngineeringBarModel, BeamEngineeringModel

_ROLE_TO_ZONE = {
    "TOP_MAIN": "TOP_ZONE",
    "TOP_EXTRA": "TOP_ZONE",
    "BOTTOM_MAIN": "BOTTOM_ZONE",
    "BOTTOM_EXTRA": "BOTTOM_ZONE",
    "STIRRUP": "TRANSVERSE_ZONE",
    "SPACER_BAR": "BOTTOM_ZONE",
    "SIDE_FACE_REINFORCEMENT": "SIDE_ZONE",
}

_ROLE_TO_L2_KEY = {
    "TOP_MAIN": "top_main_bars",
    "BOTTOM_MAIN": "bottom_main_bars",
    "TOP_EXTRA": "top_extra_bars",
    "BOTTOM_EXTRA": "bottom_extra_bars",
    "SIDE_FACE_REINFORCEMENT": "side_face_reinforcement",
    "STIRRUP": "stirrups",
    "SPACER_BAR": "spacer_bars",
    "DEVELOPMENT": "supplementary_bars",
    "LAP": "supplementary_bars",
    "UNKNOWN": "supplementary_bars",
}


class EngineeringBarBuilder:
    """Builds EngineeringBarModel for every R.1 beam — no benchmark filtering."""

    def __init__(
        self,
        r1_models_path: pathlib.Path,
        beam_registry_path: pathlib.Path,
        engineering_context: Optional[Dict[str, Any]] = None,
    ):
        self._r1_path = r1_models_path
        self._registry_path = beam_registry_path
        self._ctx = engineering_context or {}

    def build_all(self) -> Tuple[List[BeamEngineeringModel], Dict[str, Any]]:
        r1_data = json.loads(self._r1_path.read_text(encoding="utf-8"))
        reg_data = json.loads(self._registry_path.read_text(encoding="utf-8"))
        r1_models = r1_data.get("models", {})
        beam_records = reg_data.get("beams", {})

        beam_models: List[BeamEngineeringModel] = []
        stats = {
            "total_beams": len(r1_models),
            "beams_with_bars": 0,
            "beams_empty": 0,
            "total_bars": 0,
            "empty_beam_ids": [],
        }

        for beam_id, r1_model in sorted(r1_models.items()):
            reg_beam = beam_records.get(beam_id, {})
            section = r1_model.get("section") or reg_beam.get("section") or {}
            span_mm = float(reg_beam.get("clear_span_mm") or 0)
            depth_mm = float(section.get("depth_mm") or 750.0)
            width_mm = float(section.get("width_mm") or 300.0)
            groups = r1_model.get("groups") or {}

            bars: List[EngineeringBarModel] = []
            for role, grp in groups.items():
                bars.extend(self._expand_group(beam_id, role, grp))

            if bars:
                stats["beams_with_bars"] += 1
            else:
                stats["beams_empty"] += 1
                stats["empty_beam_ids"].append(beam_id)
            stats["total_bars"] += len(bars)

            beam_models.append(BeamEngineeringModel(
                beam_id=beam_id,
                beam_name=r1_model.get("beam_mark", beam_id),
                bars=bars,
                geometry={
                    "beam_id": beam_id,
                    "width_mm": width_mm,
                    "depth_mm": depth_mm,
                    "clear_span_mm": span_mm,
                    "effective_span_mm": span_mm,
                },
                source_phase="R.1.3",
                classification_complete=bool(groups),
            ))

        return beam_models, stats

    def _expand_group(
        self, beam_id: str, role: str, group: dict
    ) -> List[EngineeringBarModel]:
        labels = group.get("labels", [])
        diameters = group.get("diameters_mm", [])
        total_qty = int(group.get("total_quantity") or 0)
        if not diameters or total_qty == 0:
            return []

        spacing_mm: Optional[float] = None
        if role == "STIRRUP":
            for lbl in labels:
                m = re.search(r"@(\d+)", lbl)
                if m:
                    spacing_mm = float(m.group(1))
                    break

        bars: List[EngineeringBarModel] = []
        zone = _ROLE_TO_ZONE.get(role, "UNKNOWN_ZONE")
        cover = self._ctx.get("cover_beam_mm")
        hook = self._ctx.get("hook_multiple_135")
        lap = self._ctx.get("min_lap_mm")
        conc = self._ctx.get("concrete_grade_beam", "M30")
        steel = self._ctx.get("primary_steel_grade", "Fe550")

        if labels:
            for lbl in labels:
                m = re.match(r"(\d+)[YRyTt](\d+)", lbl)
                if m:
                    qty = int(m.group(1))
                    dia = float(m.group(2))
                    ld = self._ld_for_dia(int(dia), conc, steel)
                    bars.append(EngineeringBarModel(
                        beam_id=beam_id,
                        bar_role=role,
                        diameter_mm=dia,
                        quantity=qty,
                        zone=zone,
                        spacing_mm=spacing_mm,
                        development_length_mm=ld,
                        cover_mm=cover,
                        steel_grade=steel,
                        concrete_grade=conc,
                        hook_rule=hook,
                        lap_rule_mm=lap,
                        source_phase="R.1",
                        bar_label=lbl,
                        engineering_metadata={
                            "group_id": group.get("group_id"),
                            "classification": "R.1_DXF_DISCOVERY",
                        },
                    ))
                elif diameters:
                    qty_each = max(1, total_qty // len(diameters))
                    dia = float(diameters[0])
                    bars.append(EngineeringBarModel(
                        beam_id=beam_id,
                        bar_role=role,
                        diameter_mm=dia,
                        quantity=qty_each,
                        zone=zone,
                        spacing_mm=spacing_mm,
                        development_length_mm=self._ld_for_dia(int(dia), conc, steel),
                        cover_mm=cover,
                        steel_grade=steel,
                        concrete_grade=conc,
                        hook_rule=hook,
                        lap_rule_mm=lap,
                        source_phase="R.1",
                        bar_label=lbl,
                        engineering_metadata={"classification": "R.1_DXF_DISCOVERY"},
                    ))
        else:
            qty_each = max(1, total_qty // max(len(diameters), 1))
            for dia in diameters:
                lbl = f"{qty_each}Y{int(dia)}"
                bars.append(EngineeringBarModel(
                    beam_id=beam_id,
                    bar_role=role,
                    diameter_mm=float(dia),
                    quantity=qty_each,
                    zone=zone,
                    spacing_mm=spacing_mm,
                    development_length_mm=self._ld_for_dia(int(dia), conc, steel),
                    cover_mm=cover,
                    steel_grade=steel,
                    concrete_grade=conc,
                    hook_rule=hook,
                    lap_rule_mm=lap,
                    source_phase="R.1",
                    bar_label=lbl,
                    engineering_metadata={"classification": "R.1_DXF_DISCOVERY"},
                ))
        return bars

    def _ld_for_dia(self, dia: int, conc: str, steel: str) -> Optional[int]:
        factor = self._ctx.get("dev_length_factor")
        if factor:
            return factor * dia
        return None

    def to_l2_compatible(
        self, beam_models: List[BeamEngineeringModel]
    ) -> Dict[str, Any]:
        """Convert EngineeringBarModel to L.2 bar-list format for VB1 consumption."""
        l2_models: List[Dict[str, Any]] = []
        for bm in beam_models:
            l2: Dict[str, Any] = {
                "model_id": f"BRM::{bm.beam_id}::R1.3",
                "beam_id": bm.beam_id,
                "beam_name": bm.beam_name,
                "is_benchmark_beam": False,
                "interpretation_confidence": "HIGH",
                "geometry": {
                    **bm.geometry,
                    "top_cover_mm": self._ctx.get("cover_beam_mm", 30),
                    "bottom_cover_mm": self._ctx.get("cover_beam_mm", 30),
                },
                "support_zones": self._default_support_zones(bm.beam_id),
                "bar_count_by_role": {},
                "top_main_bars": [],
                "bottom_main_bars": [],
                "top_extra_bars": [],
                "bottom_extra_bars": [],
                "side_face_reinforcement": [],
                "stirrups": [],
                "spacer_bars": [],
                "chair_bars": [],
                "supplementary_bars": [],
                "development_length_regions": [],
                "continuity_regions": [],
                "engineering_notes": ["Source: Phase R.1.3 EngineeringBarModel"],
                "total_classified_bars": len(bm.bars),
                "unclassified_bar_count": 0,
                "classification_complete": bm.classification_complete,
                "traceability": {
                    "source": "R.1.3",
                    "model_version": "7.7.0",
                    "source_phase": "EngineeringBarModel",
                },
            }
            for bar in bm.bars:
                l2_key = _ROLE_TO_L2_KEY.get(bar.bar_role, "supplementary_bars")
                l2_bar = {
                    "bar_id": f"R13-{bar.beam_id}-{bar.bar_role}-{uuid.uuid4().hex[:6]}",
                    "source_bar_id": None,
                    "beam_id": bar.beam_id,
                    "semantic_role": bar.bar_role,
                    "diameter_mm": bar.diameter_mm,
                    "quantity": bar.quantity,
                    "steel_grade": bar.steel_grade,
                    "bar_label": bar.bar_label,
                    "position_zone": bar.zone,
                    "extent": "FULL_SPAN",
                    "continuity": "SINGLE_BEAM",
                    "support_zone": None,
                    "coverage_ratio": None,
                    "spacing_mm": bar.spacing_mm,
                    "classification_evidence": f"R.1.3 EngineeringBarModel: {bar.bar_label}",
                    "classification_confidence": "HIGH",
                    "source_pipeline_role": "R.1.3",
                    "is_corrected": False,
                    "is_reference_anchored": False,
                }
                if isinstance(l2.get(l2_key), list):
                    l2[l2_key].append(l2_bar)
                l2["bar_count_by_role"][bar.bar_role] = (
                    l2["bar_count_by_role"].get(bar.bar_role, 0) + 1
                )
            l2_models.append(l2)

        return {
            "model_count": len(l2_models),
            "source": "Phase R.1.3 — EngineeringBarModel Pipeline Integration",
            "model_version": "7.7.0",
            "models": l2_models,
        }

    @staticmethod
    def _default_support_zones(beam_id: str) -> List[dict]:
        return [
            {"support_id": f"SUP::R13::{beam_id}::L", "support_type": "LEFT_SUPPORT",
             "beam_id": beam_id, "position_fraction": 0.0, "support_width_mm": 200.0},
            {"support_id": f"SUP::R13::{beam_id}::R", "support_type": "RIGHT_SUPPORT",
             "beam_id": beam_id, "position_fraction": 1.0, "support_width_mm": 200.0},
        ]
