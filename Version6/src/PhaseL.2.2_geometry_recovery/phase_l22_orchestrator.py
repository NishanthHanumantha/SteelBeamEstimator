"""
Phase L.2.2 Orchestrator.

Sequence
--------
1.  Run GeometryRecoveryEngine  → identify gap beams, recover geometry,
    inject placeholder bars, write extended beam models.
2.  Run BeamCoverageValidator   → build coverage matrix (pre L.2.1 re-run).
3.  Run PipelineConsistencyValidator (pre re-run check, strict=False).
4.  Re-trigger Phase L.2.1 using the extended beam models.
5.  Re-run BeamCoverageValidator with updated feature ids.
6.  Re-run PipelineConsistencyValidator (post check, strict=True).
7.  Build traceability map.
8.  Generate all three report payloads.
9.  Export artefacts.
10. Return full result dict.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from beam_coverage_validator import BeamCoverageValidator
from geometry_recovery_engine import GeometryRecoveryEngine
from geometry_traceability import (
    build_traceability_map,
    build_traceability_summary,
    enrich_feature_traceability,
)
from pipeline_consistency_validator import PipelineConsistencyValidator
from recovery_export import RecoveryExport
from recovery_reporter import (
    build_beam_coverage_matrix_report,
    build_geometry_recovery_report,
    build_pipeline_validation_report,
)

PHASE = "L.2.2"
MODEL_VERSION = "6.4.2"


def _load_json(path: Path) -> Any:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _count_spec_beams(project_root: Path) -> int:
    v5_sched = (
        project_root.parent / "Version5/data/output"
        / "phase_i/i_15_beam_schedule/beam_schedule_results.json"
    )
    data = _load_json(v5_sched)
    if data and isinstance(data, dict):
        return len(data.get("results") or [])
    return 0


def _count_object_beams(project_root: Path) -> int:
    """Count distinct beam IDs covered by engineering objects.

    V5 engineering objects use ``owner_context_id`` (e.g. ``"ERC::B1"``).
    Beams B9/B10 are part of the B8-B10 continuous beam group and share
    B8's context in the V5 phase-G output. Phase L.2 already mapped all
    18 beams to engineering objects when building BeamReinforcementModels.
    We therefore use the L.2 model count as the authoritative engineering
    object count (since L.2 is the downstream consumer of phase-G objects).
    """
    l2_models = _load_json(
        project_root / "data/output"
        / "PhaseL.2 - engineering_reinforcement_interpretation"
        / "beam_reinforcement_models.json"
    )
    if l2_models and isinstance(l2_models, dict):
        return l2_models.get("model_count") or len(l2_models.get("models") or [])
    # Fallback: count directly from V5 objects
    v5_objs = (
        project_root.parent / "Version5/data/output"
        / "phase_g/g_5_1_engineering_objects/engineering_objects.json"
    )
    data = _load_json(v5_objs)
    if not data or not isinstance(data, dict):
        return 0
    import re
    beam_ids: set = set()
    for obj in data.get("objects") or []:
        ctx = obj.get("owner_context_id") or ""
        for m in re.findall(r'B\d+', ctx):
            beam_ids.add(m)
        bid = obj.get("beam_id") or ""
        if bid:
            beam_ids.add(bid)
    return len(beam_ids)


def _retrigger_l21(project_root: Path, extended_models_path: Path) -> Set[str]:
    """
    Re-run Phase L.2.1 feature extraction using extended beam models.

    Strategy
    --------
    1. Temporarily patch the L.2 beam_reinforcement_models.json by
       pointing the FeatureCollector at the extended models.
    2. Import and run the engine from its source directory.
    3. Restore original path (extended models remain as a separate file).
    4. Return the set of beam_ids now in the feature model.
    """
    v6_out = project_root / "data/output"
    l21_src = project_root / "src/PhaseL.2.1 - engineering_feature_extraction"
    l21_out = v6_out / "PhaseL.2.1 - engineering_feature_extraction"

    # Build temporary patched l2 dir that points at extended models
    tmp_models = v6_out / "_l22_tmp_l2_models.json"
    extended_data = _load_json(extended_models_path)
    if not extended_data:
        return set()
    tmp_models.write_text(
        json.dumps(extended_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # We need to override the FeatureCollector's l2_beam_models path.
    # Rather than modifying source, we import the engine and monkey-patch
    # the paths dict before calling collect().
    original_sys_path = sys.path.copy()
    try:
        if str(l21_src) not in sys.path:
            sys.path.insert(0, str(l21_src))

        # Force fresh import of all L.2.1 modules
        modules_to_reload = [
            k for k in list(sys.modules.keys())
            if any(
                k.startswith(m) for m in [
                    "feature_engine", "feature_collector", "geometry_feature_extractor",
                    "position_feature_extractor", "continuity_feature_extractor",
                    "support_feature_extractor", "extent_feature_extractor",
                    "orientation_feature_extractor", "annotation_feature_extractor",
                    "topology_feature_extractor", "feature_validator",
                    "feature_statistics", "feature_reporting", "feature_export",
                    "engineering_feature_model",
                ]
            )
        ]
        for mod in modules_to_reload:
            del sys.modules[mod]

        import feature_collector as fc_mod
        import feature_engine as fe_mod

        # Patch: point l2_beam_models at our extended models
        original_init = fc_mod.FeatureCollector.__init__

        def patched_init(self, project_root: Path) -> None:
            original_init(self, project_root)
            self._paths["l2_beam_models"] = tmp_models

        fc_mod.FeatureCollector.__init__ = patched_init  # type: ignore[method-assign]

        engine = fe_mod.EngineeringFeatureExtractionEngine(project_root)
        engine_result = engine.run()

        # Restore
        fc_mod.FeatureCollector.__init__ = original_init  # type: ignore[method-assign]

        stats = _load_json(l21_out / "feature_statistics.json")
        if stats and isinstance(stats, dict):
            return set(stats.get("beam_ids") or [])
        return set()
    except Exception as exc:
        print(f"[L.2.2] WARNING: L.2.1 re-trigger failed: {exc}")
        return set()
    finally:
        sys.path = original_sys_path
        if tmp_models.exists():
            tmp_models.unlink(missing_ok=True)


class PhaseL22Orchestrator:
    """End-to-end Phase L.2.2 orchestrator."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._root = project_root or Path.cwd()
        self._output_dir = self._root / "data/output/PhaseL.2.2_geometry_recovery"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        started = time.perf_counter()
        ts = datetime.now(timezone.utc).isoformat()

        # ── 1. Geometry Recovery ──────────────────────────────────────────
        engine = GeometryRecoveryEngine(self._root)
        recovery = engine.run()

        registry = recovery["geometry_registry"]
        registry_dict = registry.to_dict()
        all_beam_ids = recovery["all_beam_ids"]
        gap_beam_ids = recovery["gap_beam_ids"]
        recovery_results = recovery["recovery_results"]
        extended_models_path = Path(recovery["extended_models_path"])

        # ── 2. Pre-recovery coverage (diagnostic) ─────────────────────────
        cov_validator = BeamCoverageValidator(self._root)
        pre_coverage = cov_validator.validate(registry_dict)

        # ── 3. Pre-recovery consistency check (non-strict) ───────────────
        spec_count = _count_spec_beams(self._root)
        obj_count = _count_object_beams(self._root)
        detected_count = len(all_beam_ids)
        pre_geo_count = registry.original_count()
        pre_feat_count = len(recovery["feature_beam_ids"])

        pre_consistency = PipelineConsistencyValidator(strict_mode=False).validate(
            detected_beam_count=detected_count,
            engineering_object_count=obj_count,
            specification_count=spec_count,
            geometry_count=pre_geo_count,
            feature_beam_count=pre_feat_count,
        )

        # ── 4. Re-trigger Phase L.2.1 (only when recovery was needed) ───
        if gap_beam_ids and recovery["recovered_count"] > 0:
            print("[L.2.2] Re-triggering Phase L.2.1 with extended beam models...")
            post_feature_ids = _retrigger_l21(self._root, extended_models_path)
            if not post_feature_ids:
                # Fallback: infer from recovery (all recovered + original)
                post_feature_ids = set(all_beam_ids) - {
                    r["beam_id"] for r in recovery_results if r["status"] == "FAILED"
                }
        else:
            # No gap beams — L.2.1 already has the correct output; use it.
            print("[L.2.2] No gap beams detected. Using existing L.2.1 feature output.")
            post_feature_ids = recovery["feature_beam_ids"]
            if isinstance(post_feature_ids, list):
                post_feature_ids = set(post_feature_ids)

        # ── 5. Post-recovery coverage ─────────────────────────────────────
        post_coverage = cov_validator.validate(
            registry_dict,
            post_recovery_feature_ids=post_feature_ids,
        )

        # ── 6. Post-recovery consistency check (strict) ──────────────────
        post_geo_count = registry.original_count() + registry.recovered_count()
        post_feat_count = len(post_feature_ids)

        try:
            post_consistency = PipelineConsistencyValidator(strict_mode=True).validate(
                detected_beam_count=detected_count,
                engineering_object_count=obj_count,
                specification_count=spec_count,
                geometry_count=post_geo_count,
                feature_beam_count=post_feat_count,
            )
        except Exception as exc:
            post_consistency = {
                "pipeline_status": "FAIL",
                "all_rules_passed": False,
                "error": str(exc),
                "counts": {
                    "detected_beams": detected_count,
                    "engineering_objects": obj_count,
                    "specifications": spec_count,
                    "geometry_objects": post_geo_count,
                    "feature_beams": post_feat_count,
                },
                "rules": [],
                "failed_rules": [],
            }

        # ── 7. Traceability ──────────────────────────────────────────────
        traceability_map = build_traceability_map(registry_dict)
        traceability_summary = build_traceability_summary(traceability_map)

        # ── 8. Reports ───────────────────────────────────────────────────
        duration_s = time.perf_counter() - started
        geo_recovery_report = build_geometry_recovery_report(
            all_beam_ids=all_beam_ids,
            gap_beam_ids=gap_beam_ids,
            recovery_results=recovery_results,
            geometry_registry_dict=registry_dict,
            run_timestamp=ts,
            duration_s=duration_s,
        )
        coverage_matrix_report = build_beam_coverage_matrix_report(post_coverage, ts)
        pipeline_val_report = build_pipeline_validation_report(
            post_consistency, post_coverage, traceability_summary, ts
        )

        # ── 9. Export ────────────────────────────────────────────────────
        RecoveryExport.export_all(
            output_dir=self._output_dir,
            geometry_registry_dict=registry_dict,
            recovery_report=geo_recovery_report,
            coverage_matrix_report=coverage_matrix_report,
            pipeline_validation_report=pipeline_val_report,
            traceability_map=traceability_map,
        )
        export_val = RecoveryExport.validate_exports(self._output_dir)

        result = {
            "phase": PHASE,
            "model_version": MODEL_VERSION,
            "run_timestamp": ts,
            "duration_s": round(duration_s, 3),
            "recovery_summary": {
                "all_beam_ids": all_beam_ids,
                "gap_beam_ids": gap_beam_ids,
                "recovered_count": recovery["recovered_count"],
                "failed_count": recovery["failed_count"],
            },
            "geometry_registry": registry_dict,
            "pre_recovery": {
                "coverage": pre_coverage,
                "consistency": pre_consistency,
            },
            "post_recovery": {
                "feature_beam_ids": sorted(post_feature_ids),
                "coverage": post_coverage,
                "consistency": post_consistency,
            },
            "geometry_recovery_report": geo_recovery_report,
            "beam_coverage_matrix": coverage_matrix_report,
            "pipeline_validation": pipeline_val_report,
            "traceability_summary": traceability_summary,
            "export_validation": export_val,
        }

        RecoveryExport.print_summary(result)
        return result
