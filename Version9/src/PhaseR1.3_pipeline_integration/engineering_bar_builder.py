"""Build EngineeringBarModel from R.1 reinforcement discovery."""
from __future__ import annotations
import json
import os
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
    """Builds EngineeringBarModel for every R.1 beam — no benchmark filtering.

    Phase R.1.3 piece generation pipeline:
      Facts → Intent → Detail → ReinforcementPiece → EngineeringBar

    When the piece engine is available, EngineeringBarBuilder consumes ONLY
    ReinforcementPiece objects (no duplicate detailing / fabrication logic).
    """

    def __init__(
        self,
        r1_models_path: pathlib.Path,
        beam_registry_path: pathlib.Path,
        engineering_context: Optional[Dict[str, Any]] = None,
    ):
        self._r1_path = r1_models_path
        self._registry_path = beam_registry_path
        self._ctx = engineering_context or {}
        self._intent_payload: Dict[str, Any] = {}
        self._intents_by_beam: Dict[str, list] = {}
        self._detail_payload: Dict[str, Any] = {}
        self._details_by_beam: Dict[str, list] = {}
        self._piece_payload: Dict[str, Any] = {}
        self._pieces_by_beam: Dict[str, list] = {}

    def _engine_and_run(self) -> Tuple[pathlib.Path, pathlib.Path]:
        """engine_root for src packages; run_root for data/output (RunContext)."""
        run_root = self._registry_path.parents[3]
        env = (os.environ.get("STEEL_ENGINE_ROOT") or "").strip()
        if env:
            engine = pathlib.Path(env).expanduser().resolve()
        elif (run_root / "src").is_dir():
            engine = run_root
        else:
            engine = pathlib.Path(__file__).resolve().parents[2]
        return engine, run_root

    def build_all(self) -> Tuple[List[BeamEngineeringModel], Dict[str, Any]]:
        r1_data = json.loads(self._r1_path.read_text(encoding="utf-8"))
        reg_data = json.loads(self._registry_path.read_text(encoding="utf-8"))
        r1_models = r1_data.get("models", {})
        beam_records = reg_data.get("beams", {})
        # GeometryProvider catalog (Phase R.1.2A) — preferred production geometry
        geo_catalog = self._load_geometry_catalog()

        # Phase R.1.2C — resolve engineering intents once for all beams
        intents_by_beam, intent_payload = self._resolve_intents(sorted(r1_models.keys()))
        self._intents_by_beam = intents_by_beam
        self._intent_payload = intent_payload

        # Phase R.1.2D — ReinforcementDetail
        details_by_beam, detail_payload = self._resolve_details(intents_by_beam)
        self._details_by_beam = details_by_beam
        self._detail_payload = detail_payload

        # Phase R.1.3 — ReinforcementPiece (manufacturing layer)
        pieces_by_beam, piece_payload = self._resolve_pieces(details_by_beam)
        self._pieces_by_beam = pieces_by_beam
        self._piece_payload = piece_payload

        beam_models: List[BeamEngineeringModel] = []
        stats = {
            "total_beams": len(r1_models),
            "beams_with_bars": 0,
            "beams_empty": 0,
            "total_bars": 0,
            "empty_beam_ids": [],
            "geometry_source": "GeometryProvider" if geo_catalog else "beam_registry",
            "intent_source": "R.1.2C" if intents_by_beam else "R.1_groups_fallback",
            "intent_count": intent_payload.get("intent_count", 0),
            "detail_source": "R.1.2D" if details_by_beam else "none",
            "detail_count": detail_payload.get("detail_count", 0),
            "piece_source": "R.1.3" if pieces_by_beam else "none",
            "piece_count": piece_payload.get("piece_count", 0),
        }

        for beam_id, r1_model in sorted(r1_models.items()):
            reg_beam = beam_records.get(beam_id, {})
            section = r1_model.get("section") or reg_beam.get("section") or {}
            gprov = geo_catalog.get(beam_id) or {}
            if gprov:
                span_raw = gprov.get("clear_span_mm")
                if span_raw is None and gprov.get("source") == "MISSING":
                    span_mm = 0.0
                else:
                    span_mm = float(span_raw or reg_beam.get("clear_span_mm") or 0)
            else:
                span_mm = float(reg_beam.get("clear_span_mm") or 0)
            depth_mm = float(
                gprov.get("depth_mm")
                or section.get("depth_mm")
                or 750.0
            )
            width_mm = float(
                gprov.get("width_mm")
                or section.get("width_mm")
                or 300.0
            )
            groups = r1_model.get("groups") or {}

            bars: List[EngineeringBarModel] = []
            beam_pieces = pieces_by_beam.get(beam_id) or []
            beam_details = details_by_beam.get(beam_id) or []
            beam_intents = intents_by_beam.get(beam_id) or []
            if beam_pieces:
                bars = self._bars_from_pieces(beam_id, beam_pieces)
            elif beam_details:
                bars = self._bars_from_details(beam_id, beam_details)
            elif beam_intents:
                bars = self._bars_from_intents(beam_id, beam_intents)
            else:
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
                    "geometry_source": gprov.get("source") or "beam_registry",
                    "geometry_confidence": gprov.get("confidence"),
                },
                source_phase="R.1.3+PIECE",
                classification_complete=(
                    bool(groups) or bool(beam_pieces) or bool(beam_details) or bool(beam_intents)
                ),
            ))

        return beam_models, stats

    def _resolve_intents(
        self, beam_ids: List[str]
    ) -> Tuple[Dict[str, list], Dict[str, Any]]:
        """Load R.1.2C intent engine; return intents grouped by beam."""
        try:
            import importlib.util
            import sys
            import types

            engine_root, run_root = self._engine_and_run()
            pkg_dir = engine_root / "src/PhaseR1_2C_engineering_intent_resolution"
            if not pkg_dir.exists():
                return {}, {}
            pkg_name = "PhaseR12C"
            if pkg_name not in sys.modules:
                pkg = types.ModuleType(pkg_name)
                pkg.__path__ = [str(pkg_dir)]
                pkg.__package__ = pkg_name
                sys.modules[pkg_name] = pkg
            for sub in (
                "engineering_intent_model",
                "engineering_role_resolver",
                "engineering_diameter_resolver",
                "engineering_extent_resolver",
                "engineering_consistency_engine",
                "engineering_intent_resolution_engine",
            ):
                key = f"{pkg_name}.{sub}"
                if key in sys.modules:
                    continue
                spec = importlib.util.spec_from_file_location(key, pkg_dir / f"{sub}.py")
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = pkg_name
                sys.modules[key] = mod
                spec.loader.exec_module(mod)

            Engine = sys.modules[
                f"{pkg_name}.engineering_intent_resolution_engine"
            ].EngineeringIntentResolutionEngine
            engine = Engine(run_root)
            intents, payload = engine.resolve_all(beam_ids)
            by_beam: Dict[str, list] = {}
            for it in intents:
                by_beam.setdefault(it.beam_id, []).append(it)
            return by_beam, payload
        except Exception as exc:
            return {}, {"status": "SKIPPED", "error": str(exc)}

    def _resolve_details(
        self, intents_by_beam: Dict[str, list]
    ) -> Tuple[Dict[str, list], Dict[str, Any]]:
        """Phase R.1.2D — build ReinforcementDetail from intents."""
        if not intents_by_beam:
            return {}, {}
        try:
            import importlib.util
            import sys
            import types

            engine_root, run_root = self._engine_and_run()
            pkg_dir = engine_root / "src/PhaseR1_2D_reinforcement_detailing"
            if not pkg_dir.exists():
                return {}, {}
            pkg_name = "PhaseR12D"
            if pkg_name not in sys.modules:
                pkg = types.ModuleType(pkg_name)
                pkg.__path__ = [str(pkg_dir)]
                pkg.__package__ = pkg_name
                sys.modules[pkg_name] = pkg
            for sub in (
                "reinforcement_detail_model",
                "stirrup_zone_interpreter",
                "support_zone_interpreter",
                "continuity_interpreter",
                "development_length_engine",
                "curtailment_engine",
                "side_face_reinforcement_detector",
                "detail_consistency_validator",
                "detail_confidence_engine",
                "reinforcement_detail_builder",
                "reinforcement_detail_engine",
            ):
                key = f"{pkg_name}.{sub}"
                if key in sys.modules:
                    continue
                spec = importlib.util.spec_from_file_location(
                    key, pkg_dir / f"{sub}.py"
                )
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = pkg_name
                sys.modules[key] = mod
                spec.loader.exec_module(mod)

            Engine = sys.modules[
                f"{pkg_name}.reinforcement_detail_engine"
            ].ReinforcementDetailEngine
            engine = Engine(run_root, self._ctx)
            return engine.build_from_intents_by_beam(intents_by_beam)
        except Exception as exc:
            return {}, {"status": "SKIPPED", "error": str(exc)}

    def _resolve_pieces(
        self, details_by_beam: Dict[str, list]
    ) -> Tuple[Dict[str, list], Dict[str, Any]]:
        """Phase R.1.3 — build ReinforcementPiece from details."""
        if not details_by_beam:
            return {}, {}
        try:
            import importlib.util
            import sys
            import types

            engine_root, run_root = self._engine_and_run()
            pkg_dir = engine_root / "src/PhaseR1_3_reinforcement_piece_generation"
            if not pkg_dir.exists():
                return {}, {}
            pkg_name = "PhaseR13Piece"
            if pkg_name not in sys.modules:
                pkg = types.ModuleType(pkg_name)
                pkg.__path__ = [str(pkg_dir)]
                pkg.__package__ = pkg_name
                sys.modules[pkg_name] = pkg
            for sub in (
                "piece_model",
                "piece_geometry",
                "piece_quantity",
                "piece_generator",
                "piece_validator",
                "piece_confidence",
                "piece_traceability",
                "piece_builder",
            ):
                key = f"{pkg_name}.{sub}"
                if key in sys.modules:
                    continue
                spec = importlib.util.spec_from_file_location(
                    key, pkg_dir / f"{sub}.py"
                )
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = pkg_name
                sys.modules[key] = mod
                spec.loader.exec_module(mod)

            Builder = sys.modules[f"{pkg_name}.piece_builder"].PieceBuilder
            return Builder(run_root, self._ctx).build_by_beam(details_by_beam)
        except Exception as exc:
            return {}, {"status": "SKIPPED", "error": str(exc)}

    def _bars_from_pieces(
        self, beam_id: str, pieces: list
    ) -> List[EngineeringBarModel]:
        """Every EngineeringBar originates from exactly one ReinforcementPiece."""
        cover = self._ctx.get("cover_beam_mm")
        hook = self._ctx.get("hook_multiple_135")
        lap_ctx = self._ctx.get("min_lap_mm")
        conc = self._ctx.get("concrete_grade_beam", "M30")
        steel = self._ctx.get("primary_steel_grade", "Fe550")
        bars: List[EngineeringBarModel] = []
        for pce in pieces:
            dia = float(pce.diameter_mm)
            ld = pce.development_length_mm
            if ld is None:
                ld = self._ld_for_dia(int(dia), conc, steel)
            lap = pce.lap_length_mm if pce.lap_length_mm is not None else lap_ctx
            lbl = str(pce.bar_label or "")
            # Keep left/right and stirrup-zone pieces distinct for consolidation
            if pce.piece_type.endswith("_LEFT") or pce.zone == "LEFT_SUPPORT":
                lbl = f"{lbl}#L" if lbl else "L"
            elif pce.piece_type.endswith("_RIGHT") or pce.zone == "RIGHT_SUPPORT":
                lbl = f"{lbl}#R" if lbl else "R"
            elif str(pce.piece_type).startswith("STIRRUP_ZONE"):
                ztag = str(pce.zone or pce.piece_type).replace(" ", "")
                lbl = f"{lbl}#{ztag}" if lbl else ztag

            bars.append(EngineeringBarModel(
                beam_id=beam_id,
                bar_role=str(pce.role),
                diameter_mm=dia,
                quantity=int(pce.quantity),
                zone=str(pce.zone or _ROLE_TO_ZONE.get(pce.role, "UNKNOWN_ZONE")),
                spacing_mm=pce.spacing_mm,
                development_length_mm=ld,
                cover_mm=cover,
                steel_grade=steel,
                concrete_grade=conc,
                hook_rule=hook,
                lap_rule_mm=lap,
                source_phase="R.1.3",
                bar_label=lbl,
                engineering_metadata={
                    "piece_id": pce.piece_id,
                    "detail_id": pce.detail_id,
                    "intent_id": pce.intent_id,
                    "classification": "R.1.3_REINFORCEMENT_PIECE",
                    "piece_type": pce.piece_type,
                    "fabrication_type": pce.fabrication_type,
                    "shape_code": pce.shape_code,
                    "cut_length_mm": pce.cut_length_mm,
                    "estimated_weight_kg": pce.estimated_weight_kg,
                    "extent": pce.curtailment,
                    "continuity": pce.continuity,
                    "support_type": pce.support_region,
                    "support_region": pce.support_region,
                    "curtailment_type": pce.curtailment,
                    "layer": pce.layer,
                    "spacing_pattern": pce.spacing_pattern,
                    "hook_type": pce.hook_type,
                    "anchor_type": pce.anchor_type,
                    "piece_start_mm": pce.piece_start_mm,
                    "piece_end_mm": pce.piece_end_mm,
                    "piece_confidence": pce.confidence,
                    "detail_confidence": pce.detail_confidence,
                    "validation_flags": list(pce.validation_flags),
                    "evidence": list(pce.evidence),
                    "annotation_ids": list(pce.annotation_ids),
                    "geometry_ids": list(pce.geometry_ids),
                    "relationship_ids": list(pce.relationship_ids),
                    "fact_ids": list(pce.fact_ids),
                },
            ))
        return bars

    def _bars_from_details(
        self, beam_id: str, details: list
    ) -> List[EngineeringBarModel]:
        """Compatibility path when piece engine is unavailable."""
        cover = self._ctx.get("cover_beam_mm")
        hook = self._ctx.get("hook_multiple_135")
        lap_ctx = self._ctx.get("min_lap_mm")
        conc = self._ctx.get("concrete_grade_beam", "M30")
        steel = self._ctx.get("primary_steel_grade", "Fe550")
        bars: List[EngineeringBarModel] = []
        for det in details:
            dia = float(det.diameter_mm)
            ld = det.development_length_mm
            if ld is None:
                ld = self._ld_for_dia(int(dia), conc, steel)
            lap = det.lap_length_mm if det.lap_length_mm is not None else lap_ctx
            bars.append(EngineeringBarModel(
                beam_id=beam_id,
                bar_role=str(det.role),
                diameter_mm=dia,
                quantity=int(det.quantity),
                zone=str(det.zone or _ROLE_TO_ZONE.get(det.role, "UNKNOWN_ZONE")),
                spacing_mm=det.spacing_mm,
                development_length_mm=ld,
                cover_mm=cover,
                steel_grade=steel,
                concrete_grade=conc,
                hook_rule=hook,
                lap_rule_mm=lap,
                source_phase="R.1.2D",
                bar_label=str(det.bar_label or ""),
                engineering_metadata={
                    "detail_id": det.detail_id,
                    "intent_id": det.intent_id,
                    "classification": "R.1.2D_REINFORCEMENT_DETAIL",
                    "extent": det.extent,
                    "continuity": det.continuity,
                    "support_type": det.support_type,
                    "support_region": det.support_region,
                    "curtailment_type": det.curtailment_type,
                    "layer": det.layer,
                    "side_face": det.side_face,
                    "spacing_pattern": det.spacing_pattern,
                    "stirrup_zone_count": det.stirrup_zone_count,
                    "stirrup_segments": list(det.stirrup_segments or []),
                    "development_rule": det.development_rule,
                    "development_source": det.development_source,
                    "hook_type": det.hook_type,
                    "anchor_type": det.anchor_type,
                    "left_support_zone": det.left_support_zone,
                    "mid_zone": det.mid_zone,
                    "right_support_zone": det.right_support_zone,
                    "detail_confidence": det.confidence,
                    "intent_confidence": det.intent_confidence,
                    "engineering_notes": list(det.engineering_notes or []),
                    "validation_flags": list(det.validation_flags or []),
                },
            ))
        return bars

    def _bars_from_intents(
        self, beam_id: str, intents: list
    ) -> List[EngineeringBarModel]:
        """Compatibility path when R.1.2D is unavailable."""
        cover = self._ctx.get("cover_beam_mm")
        hook = self._ctx.get("hook_multiple_135")
        lap = self._ctx.get("min_lap_mm")
        conc = self._ctx.get("concrete_grade_beam", "M30")
        steel = self._ctx.get("primary_steel_grade", "Fe550")
        bars: List[EngineeringBarModel] = []
        for it in intents:
            dia = float(it.diameter_mm)
            ld = self._ld_for_dia(int(dia), conc, steel)
            if it.development_length_mm is not None:
                ld = it.development_length_mm
            bars.append(EngineeringBarModel(
                beam_id=beam_id,
                bar_role=str(it.role),
                diameter_mm=dia,
                quantity=int(it.quantity),
                zone=str(it.zone or _ROLE_TO_ZONE.get(it.role, "UNKNOWN_ZONE")),
                spacing_mm=it.spacing_mm,
                development_length_mm=ld,
                cover_mm=cover,
                steel_grade=steel,
                concrete_grade=conc,
                hook_rule=hook,
                lap_rule_mm=lap,
                source_phase="R.1.2C",
                bar_label=str(it.bar_label or ""),
                engineering_metadata={
                    "intent_id": it.intent_id,
                    "classification": "R.1.2C_ENGINEERING_INTENT",
                    "extent": it.extent,
                    "continuity": it.continuity,
                    "support_type": it.support_type,
                    "layer": it.layer,
                    "intent_confidence": it.intent_confidence,
                    "role_confidence": it.role_confidence,
                    "diameter_confidence": it.diameter_confidence,
                    "extent_confidence": it.extent_confidence,
                    "annotation_ids": list(it.annotation_ids),
                    "intent_reason": it.intent_reason,
                    "consistency_flags": list(it.consistency_flags),
                },
            ))
        return bars

    def _load_geometry_catalog(self) -> Dict[str, Any]:
        """Load validated geometry from GeometryProvider if available."""
        try:
            _, run_root = self._engine_and_run()
            catalog = (
                run_root
                / "data/output/PhaseR1_2A_geometry_accuracy/validated_beam_geometry.json"
            )
            if not catalog.exists():
                return {}
            data = json.loads(catalog.read_text(encoding="utf-8"))
            return data.get("geometries") or {}
        except Exception:
            return {}

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
                "engineering_notes": [
                    "Source: Phase R.1.3 via ReinforcementPiece"
                ],
                "total_classified_bars": len(bm.bars),
                "unclassified_bar_count": 0,
                "classification_complete": bm.classification_complete,
                "traceability": {
                    "source": "R.1.3+PIECE+R.1.2D+R.1.2C+R.1.2B",
                    "model_version": "8.5.0",
                    "source_phase": "ReinforcementPiece",
                },
            }
            for bar in bm.bars:
                meta = bar.engineering_metadata or {}
                l2_key = _ROLE_TO_L2_KEY.get(bar.bar_role, "supplementary_bars")
                l2_bar = {
                    "bar_id": f"R13-{bar.beam_id}-{bar.bar_role}-{uuid.uuid4().hex[:6]}",
                    "source_bar_id": (
                        meta.get("piece_id")
                        or meta.get("detail_id")
                        or meta.get("intent_id")
                    ),
                    "beam_id": bar.beam_id,
                    "semantic_role": bar.bar_role,
                    "diameter_mm": bar.diameter_mm,
                    "quantity": bar.quantity,
                    "steel_grade": bar.steel_grade,
                    "bar_label": bar.bar_label,
                    "position_zone": bar.zone,
                    "extent": meta.get("extent") or meta.get("curtailment_type") or "FULL_SPAN",
                    "continuity": meta.get("continuity") or "SINGLE_BEAM",
                    "support_zone": meta.get("support_type") or meta.get("support_region"),
                    "coverage_ratio": None,
                    "spacing_mm": bar.spacing_mm,
                    "classification_evidence": (
                        (
                            "SYNTHESIZED_GEOMETRY|GEOMETRY_ONLY|"
                            + (
                                f"R.1.3 Piece {meta.get('piece_id')}: {bar.bar_label}"
                                if meta.get("piece_id")
                                else (
                                    f"R.1.2D Detail {meta.get('detail_id')}: {bar.bar_label}"
                                    if meta.get("detail_id")
                                    else f"R.1.3 EngineeringBarModel: {bar.bar_label}"
                                )
                            )
                        )
                        if (
                            str(bar.bar_label or "").upper().startswith("SYNTH:")
                            or "SYNTHESIZED_GEOMETRY"
                            in " ".join(str(x) for x in (meta.get("engineering_notes") or [])).upper()
                            or "GEOMETRY_STIRRUP" in str(meta.get("source") or "").upper()
                        )
                        else (
                            f"R.1.3 Piece {meta.get('piece_id')}: {bar.bar_label}"
                            if meta.get("piece_id")
                            else (
                                f"R.1.2D Detail {meta.get('detail_id')}: {bar.bar_label}"
                                if meta.get("detail_id")
                                else f"R.1.3 EngineeringBarModel: {bar.bar_label}"
                            )
                        )
                    ),
                    "classification_confidence": (
                        "WARN"
                        if (
                            str(bar.bar_label or "").upper().startswith("SYNTH:")
                            or "SYNTHESIZED_GEOMETRY"
                            in " ".join(str(x) for x in (meta.get("engineering_notes") or [])).upper()
                        )
                        else str(
                            meta.get("piece_confidence")
                            or meta.get("detail_confidence")
                            or meta.get("intent_confidence")
                            or "HIGH"
                        )
                    ),
                    "source_pipeline_role": "R.1.3+PIECE",
                    "is_corrected": False,
                    "is_reference_anchored": False,
                    "spacing_pattern": meta.get("spacing_pattern"),
                    "stirrup_segments": meta.get("stirrup_segments"),
                    "piece_type": meta.get("piece_type"),
                    "shape_code": meta.get("shape_code"),
                    "cut_length_mm": meta.get("cut_length_mm"),
                }
                if isinstance(l2.get(l2_key), list):
                    l2[l2_key].append(l2_bar)
                l2["bar_count_by_role"][bar.bar_role] = (
                    l2["bar_count_by_role"].get(bar.bar_role, 0) + 1
                )
            l2_models.append(l2)

        return {
            "model_count": len(l2_models),
            "source": "Phase R.1.3 — EngineeringBarModel + ReinforcementPiece",
            "model_version": "8.5.0",
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
