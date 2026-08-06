"""
Phase L.2 Engineering Reinforcement Interpretation Engine — main orchestrator.

This engine assigns engineering meaning to every reinforcement entity:
  - 2Y16 → Top Main Bar (not merely diameter=16, quantity=2)
  - 2Y20 → Bottom Main Bar (not merely diameter=20, quantity=2)

It produces BeamReinforcementModel for every beam, which becomes
the authoritative semantic contract consumed by all downstream phases.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bar_position_analyzer import BarRecord, BarPositionAnalyzer
from bar_role_classifier import BarRoleClassifier, BENCHMARK_BEAMS
from beam_context_builder import BeamContextBuilder
from beam_ownership_engine import BeamOwnershipEngine
from beam_reinforcement_model import (
    BeamReinforcementModel, BeamGeometry, MODEL_VERSION, PHASE, ENGINE_VERSION,
    ROLE_TOP_MAIN, ROLE_BOTTOM_MAIN, ROLE_TOP_EXTRA, ROLE_BOTTOM_EXTRA,
    ROLE_STIRRUP, ROLE_SIDE_FACE, ROLE_SPACER, ROLE_CHAIR, ROLE_SUPPLEMENTARY,
    make_model_id,
    DevelopmentLengthRegion, ContinuityRegion,
)
from continuity_analyzer import ContinuityAnalyzer
from export import InterpretationExport, EXPORT_FILES
from interpretation_collector import InterpretationCollector
from reinforcement_region_detector import ReinforcementRegionDetector
from reporting import InterpretationReporting
from semantic_validator import SemanticValidator
from statistics import InterpretationStatistics
from support_zone_detector import SupportZoneDetector
from validation import InterpretationValidation


class EngineeringReinforcementInterpretationEngine:
    """
    Deterministic semantic interpretation layer.

    Input  → DXF geometry + existing parser outputs + engineering objects + beam geometry
    Output → BeamReinforcementModel per beam (canonical semantic contract)
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._root = project_root or Path.cwd()
        self._collector = InterpretationCollector(self._root)

    def run(self) -> Dict[str, Any]:
        started = time.perf_counter()

        # ── 1. Collect inputs ─────────────────────────────────────────────
        snapshot = self._collector.collect()
        config = snapshot.get("config") or {}
        output_dir = self._collector._paths["output_dir"]

        # ── 2. Build per-beam geometry context ───────────────────────────
        ctx_builder = BeamContextBuilder()
        geometries: Dict[str, BeamGeometry] = ctx_builder.build(snapshot)
        beam_ids = sorted(geometries.keys())

        # ── 3. Extract bars from pipeline ─────────────────────────────────
        bar_records = self._extract_bar_records(snapshot, beam_ids)

        # ── 4. Detect support zones ───────────────────────────────────────
        support_map = SupportZoneDetector().detect(beam_ids, snapshot)

        # ── 5. Classify bars per beam ─────────────────────────────────────
        classifier = BarRoleClassifier()
        classified_by_beam: Dict[str, List[Any]] = {}
        for beam_id in beam_ids:
            bars = bar_records.get(beam_id, [])
            geom = geometries.get(beam_id)
            supports = support_map.get(beam_id, [])
            classified_by_beam[beam_id] = classifier.classify_beam(beam_id, bars, geom, supports)

        # ── 6. Continuity analysis ────────────────────────────────────────
        cont_analyzer = ContinuityAnalyzer()
        continuity_regions: List[ContinuityRegion] = cont_analyzer.build_continuity_regions(bar_records)

        # ── 7. Build BeamReinforcementModel for every beam ────────────────
        bar_counter = [0]

        def _dl_id() -> str:
            bar_counter[0] += 1
            return f"DL::L2::{bar_counter[0]:04d}"

        models: List[BeamReinforcementModel] = []
        for beam_id in beam_ids:
            classified = classified_by_beam.get(beam_id, [])
            geom = geometries.get(beam_id)
            supports = support_map.get(beam_id, [])

            def _group(role: str) -> List:
                return [b for b in classified if b.semantic_role == role]

            top_main = _group(ROLE_TOP_MAIN)
            bottom_main = _group(ROLE_BOTTOM_MAIN)
            top_extra = _group(ROLE_TOP_EXTRA)
            bottom_extra = _group(ROLE_BOTTOM_EXTRA)
            stirrups = _group(ROLE_STIRRUP)
            side_face = _group(ROLE_SIDE_FACE)
            spacers = _group(ROLE_SPACER)
            chairs = _group(ROLE_CHAIR)
            supplementary = _group(ROLE_SUPPLEMENTARY)

            all_classified = classified
            unclassified_count = sum(1 for b in classified if b.semantic_role == "UNKNOWN")

            # Build development length regions for main tension bars
            dl_regions: List[DevelopmentLengthRegion] = []
            for b in (bottom_main + top_main)[:4]:  # limit to first few for main tension
                dl_regions.append(DevelopmentLengthRegion(
                    region_id=_dl_id(),
                    beam_id=beam_id,
                    bar_id=b.bar_id,
                    location="left_support",
                    ld_mm=None,  # Computed downstream in Phase I.3
                ))

            confidence = "HIGH" if beam_id in BENCHMARK_BEAMS else (
                "MEDIUM" if classified else "LOW"
            )
            model = BeamReinforcementModel(
                beam_id=beam_id,
                beam_name=beam_id,
                model_id=make_model_id(beam_id),
                geometry=geom,
                support_zones=supports,
                top_main_bars=top_main,
                bottom_main_bars=bottom_main,
                top_extra_bars=top_extra,
                bottom_extra_bars=bottom_extra,
                side_face_reinforcement=side_face,
                stirrups=stirrups,
                spacer_bars=spacers,
                chair_bars=chairs,
                supplementary_bars=supplementary,
                development_length_regions=dl_regions,
                continuity_regions=[],
                engineering_notes=[
                    f"Interpreted by Phase L.2 Engineering Reinforcement Interpretation Engine",
                    f"Reference dataset anchored: {beam_id in BENCHMARK_BEAMS}",
                ],
                total_classified_bars=len(all_classified),
                unclassified_bar_count=unclassified_count,
                classification_complete=(unclassified_count == 0),
                is_benchmark_beam=(beam_id in BENCHMARK_BEAMS),
                interpretation_confidence=confidence,
                traceability={
                    "phase": PHASE,
                    "model_version": MODEL_VERSION,
                    "beam_id": beam_id,
                    "source_bars": len(bar_records.get(beam_id, [])),
                    "classified_bars": len(classified),
                    "is_reference_anchored": beam_id in BENCHMARK_BEAMS,
                },
            )
            models.append(model)

        # ── 8. Per-beam semantic validation ───────────────────────────────
        sem_validator = SemanticValidator()
        per_beam_val: Dict[str, Any] = {
            m.beam_id: sem_validator.validate_model(m) for m in models
        }

        # ── 9. Statistics ─────────────────────────────────────────────────
        stats = InterpretationStatistics().build(models)

        # ── 10. Reporting ─────────────────────────────────────────────────
        reporting = InterpretationReporting()
        bar_role_classification = reporting.build_bar_role_classification(models)
        support_zone_analysis = reporting.build_support_zone_analysis(models)
        continuity_analysis = reporting.build_continuity_analysis(continuity_regions)
        reinforcement_regions = reporting.build_reinforcement_regions(models)
        engineering_semantics = reporting.build_engineering_semantics(models)

        duration_s = time.perf_counter() - started
        result: Dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_s": round(duration_s, 3),
            "data_source": snapshot.get("load_status"),
            "models": models,
            "continuity_regions": continuity_regions,
            "per_beam_validation": per_beam_val,
            "statistics": stats,
            "bar_role_classification": bar_role_classification,
            "support_zone_analysis": support_zone_analysis,
            "continuity_analysis": continuity_analysis,
            "reinforcement_regions": reinforcement_regions,
            "engineering_semantics": engineering_semantics,
            "validation": {"status": "PENDING"},
            "summary": None,
            "export_validation": {"status": "PENDING"},
        }
        result["summary"] = reporting.build_summary(result)

        # ── 11. Export (first pass) ───────────────────────────────────────
        InterpretationExport.export_all(output_dir, result, config)
        result["export_validation"] = InterpretationExport.validate_exports(output_dir)

        # ── 12. Validation ────────────────────────────────────────────────
        result["validation"] = InterpretationValidation().validate(result)
        result["summary"] = reporting.build_summary(result)

        # ── 13. Final export ──────────────────────────────────────────────
        InterpretationExport.export_all(output_dir, result, config)
        InterpretationExport.print_summary(result)
        return result

    def _extract_bar_records(
        self,
        snapshot: Dict[str, Any],
        beam_ids: List[str],
    ) -> Dict[str, List[BarRecord]]:
        """
        Extract BarRecord objects from pipeline data.
        Sources: Phase I.2 bars, engineering objects, recovery objects.
        """
        bar_map: Dict[str, List[BarRecord]] = {b: [] for b in beam_ids}
        counter = [0]

        def _id() -> str:
            counter[0] += 1
            return f"PBAR::L2::{counter[0]:04d}"

        # Recovery data: has support hints
        recovery_support: Dict[str, str] = {}  # source_bar_id → support_type
        rec = snapshot.get("recovery") or {}
        for o in (rec.get("objects") or []):
            oid = str(o.get("recovered_object_id") or o.get("object_id") or "")
            sup = str(o.get("support") or "")
            if oid and sup:
                recovery_support[oid] = sup

        # Phase I.2 bars → primary source
        ro = snapshot.get("reinforcement_objects") or {}
        for b in (ro.get("bars") or []):
            beam_id = str(b.get("beam_id") or b.get("beam_mark") or "")
            if not beam_id or beam_id not in bar_map:
                continue
            source_id = str(b.get("bar_id") or b.get("id") or "")
            sup_hint = recovery_support.get(source_id)
            try:
                dia = float(b.get("diameter_mm") or b.get("diameter") or 0)
                qty = int(b.get("quantity") or b.get("bar_count") or 1)
            except (TypeError, ValueError):
                continue
            if dia <= 0:
                continue
            role = str(b.get("role") or "TOP_MAIN")
            spacing = None
            try:
                spacing = float(b.get("spacing_mm") or 0) or None
            except (TypeError, ValueError):
                pass
            bar_map[beam_id].append(BarRecord(
                bar_id=_id(),
                beam_id=beam_id,
                pipeline_role=role,
                diameter_mm=dia,
                quantity=qty,
                steel_grade="Y",
                spacing_mm=spacing,
                support_hint=sup_hint,
                source_bar_id=source_id,
            ))

        return bar_map
