"""
Phase L.2.1 Engineering Feature Extraction Engine — main orchestrator.

Architecture:
  Drawing → Parser → Engineering Geometry
  → Engineering Feature Extraction (this phase — L.2.1)
  → Engineering Reinforcement Interpretation (L.2)
  → BeamReinforcementModel → Rules → Calculation → Steel → BBS → Excel

This phase extracts deterministic engineering observations from every bar.
It does NOT assign semantic roles. It does NOT modify BeamReinforcementModel.
All outputs are read-only feature records.

A structural engineer never classifies reinforcement immediately.
They first observe engineering characteristics:
  - Uppermost bar → observation (position_zone=TOP, vertical_rank=1)
  - Continuous bar → observation (is_continuous=True, coverage_ratio=0.97)
  - Runs through span → observation (extent_type=FULL_SPAN)
  - Crosses supports → observation (crosses_support=True, both_supports=True)
These observations are then used for classification in Phase L.2.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from annotation_feature_extractor import AnnotationFeatureExtractor
from continuity_feature_extractor import ContinuityFeatureExtractor
from engineering_feature_model import (
    EngineeringFeatureModel, MODEL_VERSION, PHASE, ENGINE_VERSION, make_feature_id,
)
from extent_feature_extractor import ExtentFeatureExtractor
from feature_collector import FeatureCollector
from feature_export import FeatureExport
from feature_reporting import FeatureReporting
from feature_statistics import FeatureStatistics
from feature_validator import FeatureValidator
from geometry_feature_extractor import GeometryFeatureExtractor
from orientation_feature_extractor import OrientationFeatureExtractor
from position_feature_extractor import PositionFeatureExtractor
from support_feature_extractor import SupportFeatureExtractor
from topology_feature_extractor import TopologyFeatureExtractor


class EngineeringFeatureExtractionEngine:
    """
    Deterministic engineering feature extraction layer.

    Input  → BeamReinforcementModel (L.2) + all pipeline data (read-only)
    Output → EngineeringFeatureModel per bar (observations only, no semantic roles)
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._root = project_root or Path.cwd()
        self._collector = FeatureCollector(self._root)

    def run(self) -> Dict[str, Any]:
        started = time.perf_counter()

        # ── 1. Collect inputs (read-only) ─────────────────────────────────
        snapshot = self._collector.collect()
        config = snapshot.get("config") or {}
        output_dir = self._collector._paths["output_dir"]

        beam_models_list = snapshot.get("beam_models_list") or []
        eng_objects = (snapshot.get("v5_engineering_objects") or {}).get("objects") or []

        # ── 2. Initialise extractors ───────────────────────────────────────
        geo_ext = GeometryFeatureExtractor()
        pos_ext = PositionFeatureExtractor()
        cont_ext = ContinuityFeatureExtractor()
        supp_ext = SupportFeatureExtractor()
        ext_ext = ExtentFeatureExtractor()
        ori_ext = OrientationFeatureExtractor()
        ann_ext = AnnotationFeatureExtractor()
        top_ext = TopologyFeatureExtractor()

        # ── 3. Extract features for every bar ─────────────────────────────
        features: List[EngineeringFeatureModel] = []
        feat_counter = [0]

        def _fid(bar_id: str) -> str:
            feat_counter[0] += 1
            return make_feature_id(f"{bar_id}::{feat_counter[0]:04d}")

        for beam_model in beam_models_list:
            beam_id = beam_model.get("beam_id") or ""
            all_bars_in_beam = self._gather_all_bars(beam_model)

            for bar in all_bars_in_beam:
                bar_id = bar.get("bar_id") or ""
                feat_id = _fid(bar_id)

                geom = geo_ext.extract(bar, beam_model, config)
                pos = pos_ext.extract(bar, beam_model, all_bars_in_beam, config)
                cont = cont_ext.extract(bar, beam_model, config)
                supp = supp_ext.extract(bar, beam_model, config)
                ext = ext_ext.extract(bar, beam_model, config)
                ori = ori_ext.extract(bar, beam_model)
                ann = ann_ext.extract(bar, beam_model)
                top = top_ext.extract(bar, beam_model, beam_models_list, eng_objects)

                completeness = self._completeness_score(geom, pos, cont, supp, ext, ori, ann, top)

                fm = EngineeringFeatureModel(
                    feature_id=feat_id,
                    bar_id=bar_id,
                    beam_id=beam_id,
                    annotation_id=bar.get("source_bar_id"),
                    geometry_reference=beam_model.get("model_id"),
                    engineering_object_reference=None,
                    geometry=geom,
                    position=pos,
                    continuity=cont,
                    support=supp,
                    extent=ext,
                    orientation=ori,
                    annotation=ann,
                    topology=top,
                    feature_completeness_score=completeness,
                    traceability={
                        "phase": PHASE,
                        "model_version": MODEL_VERSION,
                        "bar_id": bar_id,
                        "beam_id": beam_id,
                        "source": "L.2 BeamReinforcementModel",
                        "is_observation_only": True,
                    },
                )
                features.append(fm)

        # ── 4. Per-feature validation ──────────────────────────────────────
        validator = FeatureValidator()
        per_feature_val: List[Dict[str, Any]] = [
            validator.validate_feature(f) for f in features
        ]

        # ── 5. Statistics ──────────────────────────────────────────────────
        stats = FeatureStatistics().build(features)

        # ── 6. Reporting ───────────────────────────────────────────────────
        rep = FeatureReporting()
        duration_s = time.perf_counter() - started

        result: Dict[str, Any] = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "engine_version": ENGINE_VERSION,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_s": round(duration_s, 3),
            "load_status": snapshot.get("load_status"),
            "features": features,
            "per_feature_validation": per_feature_val,
            "statistics": stats,
            "geometry_features": rep.build_geometry_features(features),
            "position_features": rep.build_position_features(features),
            "continuity_features": rep.build_continuity_features(features),
            "support_features": rep.build_support_features(features),
            "extent_features": rep.build_extent_features(features),
            "orientation_features": rep.build_orientation_features(features),
            "annotation_features": rep.build_annotation_features(features),
            "topology_features": rep.build_topology_features(features),
            "validation": {"status": "PENDING"},
            "summary": None,
            "export_validation": {"status": "PENDING"},
        }
        result["summary"] = rep.build_summary(result)

        # ── 7. Export (first pass) ────────────────────────────────────────
        FeatureExport.export_all(output_dir, result, config)
        result["export_validation"] = FeatureExport.validate_exports(output_dir)

        # ── 8. Collection validation ──────────────────────────────────────
        result["validation"] = validator.validate_collection(features, result)
        result["summary"] = rep.build_summary(result)

        # ── 9. Final export ───────────────────────────────────────────────
        FeatureExport.export_all(output_dir, result, config)
        FeatureExport.print_summary(result)
        return result

    def _gather_all_bars(self, beam_model: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect every bar from all role lists in the BeamReinforcementModel."""
        role_lists = [
            "top_main_bars", "bottom_main_bars",
            "top_extra_bars", "bottom_extra_bars",
            "side_face_reinforcement", "stirrups",
            "spacer_bars", "chair_bars", "supplementary_bars",
        ]
        all_bars: List[Dict[str, Any]] = []
        for rl in role_lists:
            for bar in (beam_model.get(rl) or []):
                all_bars.append(bar)
        return all_bars

    @staticmethod
    def _completeness_score(*feature_groups) -> float:
        """Compute fraction of feature fields that are not None (False/0/[] are valid observations)."""
        total = 0
        present = 0
        for fg in feature_groups:
            if fg is None:
                total += 1
                continue
            d = fg.__dict__
            total += len(d)
            present += sum(1 for v in d.values() if v is not None)
        return round(present / max(total, 1), 3)
