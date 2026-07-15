"""
phase_r1_orchestrator.py — Master orchestrator for Phase R.1.

Pipeline (within R.1):
  beam_detail_discovery
        │
  beam_detail_segmenter  (assigns DXF entities to beams)
        │
  annotation_discovery   (parse annotation text)
        │
  reinforcement_annotation_classifier (role assignment pass 1)
        │
  reinforcement_geometry_mapper       (refine zones via section geometry)
        │
  reinforcement_annotation_classifier (role assignment pass 2 - re-classify)
        │
  reinforcement_group_builder
        │
  reinforcement_role_classifier       (final confirmation + deep-beam handling)
        │
  reinforcement_relationship_builder
        │
  engineering_reinforcement_builder   (produce R1BeamReinforcementModel)
        │
  reinforcement_statistics
        │
  reinforcement_validator
        │
  reinforcement_reporter
        │
  reinforcement_export

No hardcoded beam IDs.  No benchmark assumptions.  No LLM.
"""

from __future__ import annotations

import logging
import pathlib
import sys
import time
from typing import Optional

import ezdxf
import yaml

from .beam_detail_discovery             import BeamDetailDiscovery
from .beam_detail_segmenter             import BeamDetailSegmenter
from .annotation_discovery             import AnnotationDiscovery
from .reinforcement_annotation_classifier import ReinforcementAnnotationClassifier
from .reinforcement_geometry_mapper    import ReinforcementGeometryMapper
from .reinforcement_group_builder      import ReinforcementGroupBuilder
from .reinforcement_role_classifier    import ReinforcementRoleClassifier
from .reinforcement_relationship_builder import ReinforcementRelationshipBuilder
from .engineering_reinforcement_builder  import EngineeringReinforcementBuilder
from .reinforcement_statistics         import ReinforcementStatistics
from .reinforcement_validator          import ReinforcementValidator
from .reinforcement_reporter           import ReinforcementReporter
from .reinforcement_export             import ReinforcementExport

log = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level   = logging.INFO,
        format  = "%(asctime)s  [%(levelname)-7s]  %(name)s — %(message)s",
        datefmt = "%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force   = True,
    )
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def _load_config(config_path: pathlib.Path) -> dict:
    if not config_path.exists():
        log.warning("Config not found at %s — using defaults", config_path)
        return {}
    with open(config_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _resolve_dxf_path(project_root: pathlib.Path, config: dict) -> Optional[pathlib.Path]:
    """Resolve the reinforcement DXF path from the beam_registry."""
    import json
    registry_rel = config.get("discovery", {}).get(
        "beam_registry_path",
        "data/output/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json",
    )
    registry_path = project_root / registry_rel
    if not registry_path.exists():
        log.error("beam_registry not found: %s", registry_path)
        return None

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    drawing_paths = registry.get("drawing_paths", {})

    # Try "reinforcement" key first
    reinforcement_key = config.get("discovery", {}).get("reinforcement_dxf_key", "reinforcement")
    dxf_rel = drawing_paths.get(reinforcement_key)
    if dxf_rel:
        return project_root / dxf_rel

    # Fallback: search for first .dxf containing "Beam" in name
    for key, rel in drawing_paths.items():
        if rel and "beam" in rel.lower() and rel.lower().endswith(".dxf"):
            return project_root / rel

    # Last resort: scan data/Benchmark_Set_2/reinforcement
    rein_dir = project_root / "data" / "Benchmark_Set_2" / "reinforcement"
    if rein_dir.exists():
        dxf_files = list(rein_dir.glob("*.dxf"))
        if dxf_files:
            return dxf_files[0]

    log.error("Cannot locate reinforcement DXF file")
    return None


# ════════════════════════════════════════════════════════════════════════════
class PhaseR1Orchestrator:
    """Master orchestrator for Phase R.1."""

    def __init__(self, project_root: pathlib.Path, config: dict):
        self.project_root = project_root
        self.config       = config

    def run(self) -> dict:
        t0 = time.perf_counter()
        log.info("=" * 72)
        log.info("Phase R.1 — Generalized Reinforcement Discovery  MODEL_VERSION 7.3.0")
        log.info("=" * 72)

        # ── Step 1: Beam detail discovery ─────────────────────────────────────
        log.info("[1/9] Beam Detail Discovery ...")
        discoverer = BeamDetailDiscovery(self.project_root, self.config)
        details    = discoverer.discover()
        if not details:
            log.error("No beam details discovered — aborting")
            return {"status": "FAILED", "reason": "No beam details discovered"}
        log.info("      %d BeamDetail objects", len(details))

        # ── Step 2: Resolve DXF and segment entities ───────────────────────────
        log.info("[2/9] Beam Detail Segmentation ...")
        dxf_path = _resolve_dxf_path(self.project_root, self.config)
        if dxf_path is None or not dxf_path.exists():
            log.error("Reinforcement DXF not found — aborting")
            return {"status": "FAILED", "reason": "DXF not found"}

        log.info("      DXF: %s", dxf_path)
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        segmenter = BeamDetailSegmenter(self.config)
        beam_map  = segmenter.segment(msp, details)

        # ── Step 3: Annotation discovery ──────────────────────────────────────
        log.info("[3/9] Annotation Discovery ...")
        ann_discoverer    = AnnotationDiscovery(self.config)
        beam_annotations  = ann_discoverer.discover(details, beam_map)
        total_anns = sum(len(v) for v in beam_annotations.values())
        log.info("      %d annotations discovered", total_anns)

        # ── Step 4: Geometry mapping ───────────────────────────────────────────
        log.info("[4/9] Reinforcement Geometry Mapping ...")
        mapper = ReinforcementGeometryMapper(self.config)
        mapper.map_geometry(details, beam_annotations)

        # ── Step 5: Annotation classification (pass 1 + post-geometry pass 2) ─
        log.info("[5/9] Reinforcement Annotation Classification ...")
        classifier       = ReinforcementAnnotationClassifier(self.config)
        beam_annotations = classifier.classify(beam_annotations)

        # ── Step 6: Group building ─────────────────────────────────────────────
        log.info("[6/9] Reinforcement Group Building ...")
        group_builder = ReinforcementGroupBuilder()
        beam_groups   = group_builder.build(beam_annotations)

        # ── Step 7: Role classification (final) ────────────────────────────────
        log.info("[7/9] Reinforcement Role Classification ...")
        role_classifier = ReinforcementRoleClassifier(self.config)
        beam_groups     = role_classifier.classify_roles(details, beam_groups)

        # ── Step 8: Relationship building ─────────────────────────────────────
        log.info("[8/9] Relationship Building ...")
        rel_builder   = ReinforcementRelationshipBuilder()
        relationships = rel_builder.build(beam_groups)

        # ── Step 9: Engineering model building ────────────────────────────────
        log.info("[9/9] Engineering Reinforcement Builder ...")
        model_builder = EngineeringReinforcementBuilder()
        models        = model_builder.build(details, beam_annotations, beam_groups)

        # ── Statistics ────────────────────────────────────────────────────────
        log.info("Computing statistics ...")
        stats_engine = ReinforcementStatistics()
        statistics   = stats_engine.compute(details, beam_annotations, beam_groups, models)

        # ── Validation ────────────────────────────────────────────────────────
        log.info("Validating ...")
        validator  = ReinforcementValidator(self.config, self.project_root)
        validation = validator.validate(details, models, beam_annotations, beam_groups, statistics)

        # ── Report ────────────────────────────────────────────────────────────
        log.info("Generating report ...")
        reporter = ReinforcementReporter()
        report   = reporter.generate(details, beam_annotations, models, statistics, validation)

        # ── Export ────────────────────────────────────────────────────────────
        log.info("Exporting artefacts ...")
        exporter  = ReinforcementExport(self.config, self.project_root)
        artefacts = exporter.export_all(
            details, beam_annotations, beam_groups, models,
            relationships, statistics, validation, report,
        )

        elapsed = round(time.perf_counter() - t0, 2)

        log.info("=" * 72)
        log.info("Phase R.1 COMPLETE in %.2fs", elapsed)
        log.info("  Beam details       : %d", len(details))
        log.info("  Annotations        : %d", total_anns)
        log.info("  Models built       : %d", len(models))
        log.info("  Coverage           : %.1f%%", statistics["coverage_pct"])
        log.info("  Validation         : %s (%d/%d)", validation.overall, validation.passed, 10)
        log.info("  Artefacts written  : %d", len(artefacts))
        log.info("=" * 72)

        return {
            "status":          validation.overall,
            "model_version":   "7.3.0",
            "phase":           "R.1",
            "elapsed_s":       elapsed,
            "total_beams":     len(details),
            "total_annotations": total_anns,
            "total_models":    len(models),
            "coverage_pct":    statistics["coverage_pct"],
            "validation":      validation.to_dict(),
            "statistics":      statistics,
            "artefacts":       artefacts,
        }


# ── Entry point ───────────────────────────────────────────────────────────────
def run_phase_r1(project_root: pathlib.Path, config_path: Optional[pathlib.Path] = None) -> dict:
    _setup_logging()
    if config_path is None:
        config_path = project_root / "config" / "generalized_reinforcement_discovery.yaml"
    config = _load_config(config_path)
    orch   = PhaseR1Orchestrator(project_root, config)
    return orch.run()
