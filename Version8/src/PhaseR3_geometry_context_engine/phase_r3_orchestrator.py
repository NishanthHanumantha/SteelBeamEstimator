"""
phase_r3_orchestrator.py — Master orchestrator for Phase R.3.
MODEL_VERSION: 8.0.0

Pipeline:
  1. Load R.2.1D EngineeringFacts.json
  2. Load geometry_registry.json (beam axis + support locations)
  3. Load beam_registry.json (DXF centroids + clear spans)
  4. Load reinforcement_annotations.json (DXF positions of annotations)
  5. Build BeamAxis for every beam
  6. Build SupportLocations for every beam
  7. Build GeometryContext for every annotation
  8. Validate (12 rules)
  9. Compute statistics
 10. Generate markdown report
 11. Export 12 artefacts

Design invariant: Intent remains UNKNOWN throughout.
"""
from __future__ import annotations

import json
import pathlib
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import MODEL_VERSION, PHASE_ID
from .beam_axis_builder import BeamAxisBuilder
from .geometry_context_builder import GeometryContextBuilder
from .geometry_export import GeometryExport
from .geometry_models import BeamAxis, GeometryContext, SupportLocation
from .geometry_reporter import GeometryReporter
from .geometry_statistics import GeometryStatistics
from .geometry_validator import GeometryValidator
from .support_locator import SupportLocator


# ── Output directory ──────────────────────────────────────────────────────────
_OUT_DIR_NAME = "PhaseR3_geometry_context_engine"


class PhaseR3Orchestrator:
    """
    Master orchestrator for the Geometry Context Engine (Phase R.3).
    """

    def __init__(self, version7_root: pathlib.Path):
        self._root    = pathlib.Path(version7_root)
        self._out_dir = self._root / "data" / "output" / _OUT_DIR_NAME

        self._axis_builder    = BeamAxisBuilder()
        self._sup_locator     = SupportLocator()
        self._ctx_builder     = GeometryContextBuilder()
        self._validator       = GeometryValidator()
        self._statistics      = GeometryStatistics()
        self._reporter        = GeometryReporter()
        self._exporter        = GeometryExport()

    def run(self) -> Dict[str, Any]:
        print(f"[R.3] Phase R.3 — Geometry Context Engine  (MODEL_VERSION: {MODEL_VERSION})")
        print(f"[R.3] Root: {self._root}")

        # ── 1. Load R.2.1D facts ───────────────────────────────────────────────
        facts_path = self._find_output("PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json")
        print(f"[R.3] Loading R.2.1D facts from: {facts_path}")
        facts_raw  = json.loads(facts_path.read_text(encoding="utf-8"))
        # R.2.1D EngineeringFacts.json uses key "all" for the flat list
        facts_list = (
            facts_raw.get("all")
            or facts_raw.get("facts")
            or facts_raw.get("engineering_facts")
            or (facts_raw if isinstance(facts_raw, list) else [])
        )
        total_facts = len(facts_list)
        print(f"[R.3]   Loaded {total_facts} engineering facts")

        # ── 2. Load geometry_registry ─────────────────────────────────────────
        geo_reg_path = self._find_output("PhaseL.2.2_geometry_recovery/geometry_registry.json")
        print(f"[R.3] Loading geometry_registry from: {geo_reg_path}")
        geo_reg_raw  = json.loads(geo_reg_path.read_text(encoding="utf-8"))
        geo_entries  = geo_reg_raw.get("entries") or []
        geo_by_beam: Dict[str, Any] = {e["beam_id"]: e for e in geo_entries}
        print(f"[R.3]   Geometry entries: {len(geo_by_beam)} beams")

        # ── 3. Load beam_registry ─────────────────────────────────────────────
        beam_reg_path = self._find_output("PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json")
        print(f"[R.3] Loading beam_registry from: {beam_reg_path}")
        beam_reg_raw  = json.loads(beam_reg_path.read_text(encoding="utf-8"))
        beam_reg_dict = beam_reg_raw.get("beams") or {}
        if isinstance(beam_reg_dict, list):
            beam_reg_dict = {b["beam_id"]: b for b in beam_reg_dict}
        print(f"[R.3]   Beam registry: {len(beam_reg_dict)} beams")

        # ── 4. Load reinforcement_annotations ────────────────────────────────
        ann_path = self._find_output("PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotations.json")
        print(f"[R.3] Loading annotations from: {ann_path}")
        ann_raw   = json.loads(ann_path.read_text(encoding="utf-8"))
        by_beam_ann = ann_raw.get("by_beam") or {}
        # Build annotation_id → record index
        ann_by_id: Dict[str, Dict[str, Any]] = {}
        for beam_id, ann_list in by_beam_ann.items():
            for ann in ann_list:
                aid = ann.get("annotation_id")
                if aid:
                    ann_by_id[aid] = ann
        print(f"[R.3]   Annotation lookup: {len(ann_by_id)} annotation_ids")

        # ── Organise facts by beam ────────────────────────────────────────────
        facts_by_beam: Dict[str, List[Dict]] = defaultdict(list)
        for f in facts_list:
            bid = f.get("beam_id") or ""
            facts_by_beam[bid].append(f)

        # ── 5. Build BeamAxis per beam ────────────────────────────────────────
        axes_by_beam: Dict[str, BeamAxis] = {}
        for beam_id in facts_by_beam:
            geo_entry = geo_by_beam.get(beam_id)
            reg_entry = beam_reg_dict.get(beam_id)
            axes_by_beam[beam_id] = self._axis_builder.build(beam_id, geo_entry, reg_entry)

        print(f"[R.3] Built {len(axes_by_beam)} BeamAxis objects")

        # ── 6. Build SupportLocations per beam ───────────────────────────────
        supports_by_beam: Dict[str, List[SupportLocation]] = {}
        for beam_id, axis in axes_by_beam.items():
            geo_entry = geo_by_beam.get(beam_id)
            supports_by_beam[beam_id] = self._sup_locator.locate(
                beam_id, geo_entry, axis.beam_length_mm
            )

        print(f"[R.3] Located supports for {len(supports_by_beam)} beams")

        # ── 7. Build GeometryContext per annotation ───────────────────────────
        # Pre-compute group positions per (beam_id, clean_text) for extent refine
        group_positions: Dict[Tuple[str, str], List[float]] = defaultdict(list)

        # First pass: compute normalized positions without group refinement
        contexts_raw: Dict[str, Tuple[str, GeometryContext]] = {}
        for beam_id, beam_facts in facts_by_beam.items():
            axis      = axes_by_beam.get(beam_id)
            supports  = supports_by_beam.get(beam_id, [])
            for fact in beam_facts:
                ann_id    = fact.get("annotation_id") or ""
                ann_rec   = ann_by_id.get(ann_id)
                ctx = self._ctx_builder.build(
                    annotation_id = ann_id,
                    beam_axis     = axis,
                    supports      = supports,
                    ann_record    = ann_rec,
                    fact_dict     = fact,
                )
                contexts_raw[ann_id] = (beam_id, ctx)
                clean_text = str(fact.get("clean_text") or "")
                group_positions[(beam_id, clean_text)].append(ctx.normalized_position)

        # Second pass: refine extent evidence with group context
        contexts_by_beam: Dict[str, List[GeometryContext]] = defaultdict(list)
        for ann_id, (beam_id, ctx) in contexts_raw.items():
            fact_dict = next(
                (f for f in facts_by_beam[beam_id] if f.get("annotation_id") == ann_id),
                {}
            )
            clean_text = str(fact_dict.get("clean_text") or "")
            grp_pos    = group_positions.get((beam_id, clean_text), [])

            # Rebuild with group refinement
            axis     = axes_by_beam.get(beam_id)
            supports = supports_by_beam.get(beam_id, [])
            ann_rec  = ann_by_id.get(ann_id)
            ctx_refined = self._ctx_builder.build(
                annotation_id  = ann_id,
                beam_axis      = axis,
                supports       = supports,
                ann_record     = ann_rec,
                fact_dict      = fact_dict,
                group_positions= grp_pos,
            )
            contexts_by_beam[beam_id].append(ctx_refined)

        total_contexts = sum(len(cl) for cl in contexts_by_beam.values())
        print(f"[R.3] Built {total_contexts} GeometryContext objects")

        # ── 8. Validate ───────────────────────────────────────────────────────
        production_wb = self._find_production_workbook()
        validation = self._validator.validate(
            contexts_by_beam   = contexts_by_beam,
            axes_by_beam       = axes_by_beam,
            supports_by_beam   = supports_by_beam,
            total_facts        = total_facts,
            r21d_facts_by_beam = facts_by_beam,
            production_workbook= production_wb,
        )
        print(f"[R.3] Validation: {validation['summary']}")
        for rid, res in validation["rules"].items():
            icon = "OK" if res["passed"] else "FAIL"
            print(f"[R.3]   {rid}: {icon} — {res['detail']}")

        # ── 9. Statistics ─────────────────────────────────────────────────────
        stats = self._statistics.compute(contexts_by_beam, axes_by_beam, supports_by_beam)
        print(f"[R.3] Statistics computed: {stats['beam_count']} beams, {stats['context_count']} contexts")

        # ── 10. Markdown report ───────────────────────────────────────────────
        phase_meta = {
            "phase_id":      PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at":  datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        md_report = self._reporter.generate_markdown(stats, validation, phase_meta)

        # ── 11. Export ────────────────────────────────────────────────────────
        paths = self._exporter.export_all(
            out_dir          = self._out_dir,
            contexts_by_beam = contexts_by_beam,
            axes_by_beam     = axes_by_beam,
            supports_by_beam = supports_by_beam,
            stats            = stats,
            validation       = validation,
            md_report        = md_report,
            phase_meta       = phase_meta,
        )
        print(f"[R.3] Exported {len(paths)} artefacts to: {self._out_dir}")
        for name, p in paths.items():
            print(f"[R.3]   {name}: {p.name}")

        return {
            "phase_id":        PHASE_ID,
            "model_version":   MODEL_VERSION,
            "beam_count":      len(axes_by_beam),
            "context_count":   total_contexts,
            "validation":      validation,
            "statistics":      stats,
            "output_dir":      str(self._out_dir),
            "artefacts":       {k: str(v) for k, v in paths.items()},
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_output(self, rel_path: str) -> pathlib.Path:
        p = self._root / "data" / "output" / rel_path
        if not p.exists():
            raise FileNotFoundError(f"[R.3] Required file not found: {p}")
        return p

    def _find_production_workbook(self) -> Optional[pathlib.Path]:
        for search_dir in [
            self._root / "data" / "output" / "Production_Output",
            self._root / "data" / "output" / "PhaseR.1.1_production_validation",
        ]:
            if search_dir.exists():
                hits = list(search_dir.glob("*.xlsx"))
                if hits:
                    return hits[0]
        return None
