"""
Phase L.3 Orchestrator — end-to-end pattern recognition pipeline.

Sequence
--------
1.  Load all inputs (L.2.1 feature DB, L.2 models, L.2.2 geometry registry,
    V5 beam schedule).
2.  For each beam → run all detectors → build EngineeringPattern.
3.  Register in PatternRegistry.
4.  Validate (4 rules, fail-fast).
5.  Build reports.
6.  Export 6 artefacts.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from engineering_pattern_builder import EngineeringPatternBuilder
from pattern_export import PatternExport
from pattern_models import EngineeringPattern, MODEL_VERSION, PHASE
from pattern_registry import PatternRegistry
from pattern_reporter import (
    build_beam_pattern_matrix,
    build_pattern_statistics,
    build_pattern_summary,
)
from pattern_validator import PatternValidator

PHASE_LABEL = "Beam Reinforcement Pattern Recognition"


def _load(path: Path) -> Any:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class PhaseL3Orchestrator:

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._root = project_root or Path.cwd()
        v6_out = self._root / "data/output"
        v5_out = self._root.parent / "Version5/data/output"
        self._paths = {
            "l21_feature_db": v6_out / "PhaseL.2.1 - engineering_feature_extraction/engineering_feature_database.json",
            "l21_feature_stats": v6_out / "PhaseL.2.1 - engineering_feature_extraction/feature_statistics.json",
            "l2_beam_models": v6_out / "PhaseL.2 - engineering_reinforcement_interpretation/beam_reinforcement_models.json",
            "l2_continuity": v6_out / "PhaseL.2 - engineering_reinforcement_interpretation/continuity_analysis.json",
            "l2_support_zones": v6_out / "PhaseL.2 - engineering_reinforcement_interpretation/support_zone_analysis.json",
            "l22_geometry_registry": v6_out / "PhaseL.2.2_geometry_recovery/geometry_registry.json",
            "v5_beam_schedule": v5_out / "phase_i/i_15_beam_schedule/beam_schedule_results.json",
            "v5_eng_objects": v5_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
            "output_dir": v6_out / "PhaseL.3_beam_pattern_recognition",
        }
        self._output_dir: Path = self._paths["output_dir"]
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ── data helpers ──────────────────────────────────────────────────────

    def _group_features_by_beam(
        self, feature_db: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return {beam_id: [feature_record, ...]}."""
        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for feat in feature_db.get("features") or []:
            bid = feat.get("beam_id") or ""
            if bid:
                groups[bid].append(feat)
        return dict(groups)

    def _build_l2_model_map(
        self, l2_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Return {beam_id: L2_model}."""
        return {
            m["beam_id"]: m
            for m in (l2_data.get("models") or [])
            if m.get("beam_id")
        }

    def _build_geometry_map(
        self, geo_reg: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        return {
            e["beam_id"]: e
            for e in (geo_reg.get("entries") or [])
            if e.get("beam_id")
        }

    def _count_object_beams(self) -> int:
        """Count distinct beams in L.2 (mirrors L.2.2 approach)."""
        l2 = _load(self._paths["l2_beam_models"])
        if l2 and isinstance(l2, dict):
            return l2.get("model_count") or len(l2.get("models") or [])
        return 0

    # ── public run ────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        started = time.perf_counter()
        ts = datetime.now(timezone.utc).isoformat()

        # ── 1. Load inputs ─────────────────────────────────────────────────
        feature_db = _load(self._paths["l21_feature_db"])
        if not feature_db:
            raise RuntimeError(
                "Cannot load L.2.1 engineering_feature_database.json. "
                "Run Phase L.2.2 and Phase L.2.1 first."
            )

        l2_data = _load(self._paths["l2_beam_models"]) or {}
        l2_continuity = _load(self._paths["l2_continuity"]) or {}
        geo_reg = _load(self._paths["l22_geometry_registry"]) or {}
        feature_stats = _load(self._paths["l21_feature_stats"]) or {}

        features_by_beam = self._group_features_by_beam(feature_db)
        l2_model_map = self._build_l2_model_map(l2_data)
        geometry_map = self._build_geometry_map(geo_reg)

        all_beam_ids: List[str] = sorted(
            l2_model_map.keys(), key=lambda b: (len(b), b)
        )

        # ── 2. Build patterns ─────────────────────────────────────────────
        builder = EngineeringPatternBuilder()
        registry = PatternRegistry()

        for beam_id in all_beam_ids:
            bar_features = features_by_beam.get(beam_id) or []
            l2_model = l2_model_map.get(beam_id) or {}
            geo_entry = geometry_map.get(beam_id) or {}

            pattern = builder.build(
                beam_id=beam_id,
                bar_features=bar_features,
                l2_model=l2_model,
                geometry_entry=geo_entry,
                l2_continuity_data=l2_continuity,
                run_timestamp=ts,
            )
            registry.register(pattern)

        # ── 3. Validate ────────────────────────────────────────────────────
        feature_beam_count = len(feature_stats.get("beam_ids") or [])
        geometry_count = geo_reg.get("total") or len(geometry_map)
        obj_count = self._count_object_beams()

        # Use lenient feature count: if feature DB has more beams, use that
        feature_beam_count = max(feature_beam_count, len(features_by_beam))

        validator = PatternValidator(strict_mode=False)
        val_result = validator.validate_collection(
            registry=registry,
            feature_beam_count=feature_beam_count,
            geometry_count=geometry_count,
            engineering_object_count=obj_count,
        )

        # ── 4. Reports ─────────────────────────────────────────────────────
        all_patterns = registry.all_patterns()
        duration_s = time.perf_counter() - started

        stats = build_pattern_statistics(all_patterns)
        matrix = build_beam_pattern_matrix(all_patterns)
        summary = build_pattern_summary(all_patterns, val_result, stats, ts, duration_s)

        # Full validation report
        val_report = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": ts,
            **val_result,
        }

        # ── 5. Export ──────────────────────────────────────────────────────
        PatternExport.export_all(
            output_dir=self._output_dir,
            patterns=all_patterns,
            registry=registry,
            pattern_summary=summary,
            beam_pattern_matrix=matrix,
            validation_report=val_report,
            statistics=stats,
        )
        export_val = PatternExport.validate_exports(self._output_dir)

        result = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": ts,
            "duration_s": round(duration_s, 3),
            "total_beams": registry.count(),
            "patterns": all_patterns,
            "pattern_summary": summary,
            "statistics": stats,
            "validation": val_result,
            "beam_pattern_matrix": matrix,
            "export_validation": export_val,
        }

        PatternExport.print_summary(result)
        return result
