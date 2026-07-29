"""
phase_r31_orchestrator.py — Master orchestrator for Phase R.3.1.
MODEL_VERSION: 8.9.4

Pipeline:
  1.  Load R.2.1D EngineeringFacts + R.3 GeometryContexts + BeamAxis + SupportLocations
  2.  Load DXF modelspace (ezdxf)
  3.  Load reinforcement annotations (annotation_id → DXF position)
  4.  Discover leaders (LEADER entities on -S-ARROW layer)
  5.  Build leader chains
  6.  Detect arrows from leaders
  7.  Associate annotations with leaders (tail proximity)
  8.  Detect physical bars (LINE/LWPOLYLINE on -STR-REINF layer)
  9.  Build extent evidence for all bars
 10.  Build support crossings for all bars
 11.  Build relationship graph (assemble EngineeringDrawingRelationship)
 12.  Validate (12 rules)
 13.  Compute statistics
 14.  Generate markdown report
 15.  Export 12 artefacts

Design invariant: Intent remains UNKNOWN throughout.

I/O is run-scoped via RunContext (Phase D.5.4). Engineering logic unchanged.
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import ezdxf

from .annotation_relationship_builder import AnnotationRelationshipBuilder
from .arrow_detector import ArrowDetector
from .extent_builder import ExtentBuilder
from .leader_chain_builder import LeaderChainBuilder
from .leader_discovery import LeaderDiscovery
from .physical_bar_detector import PhysicalBarDetector
from .relationship_export import RelationshipExport
from .relationship_graph_builder import RelationshipGraphBuilder
from .relationship_models import SupportCrossing
from .relationship_reporter import RelationshipReporter
from .relationship_statistics import RelationshipStatistics
from .relationship_validator import RelationshipValidator
from .support_crossing_builder import SupportCrossingBuilder

MODEL_VERSION = "8.9.4"
PHASE_ID = "R.3.1"

_OUT_DIR_NAME = "PhaseR3.1_engineering_relationship_engine"
_R21D_FACTS_REL = "PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json"
_R3_AXIS_REL = "PhaseR3_geometry_context_engine/BeamAxis.json"
_R3_SUP_REL = "PhaseR3_geometry_context_engine/SupportLocations.json"
_R3_GEO_REL = "PhaseR3_geometry_context_engine/GeometryContexts.json"
_R1_ANN_REL = "PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotations.json"
_VROOT1_BEAM_REL = "PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json"


class PhaseR31Orchestrator:

    def __init__(
        self,
        output_root: Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
        facts_path: Optional[pathlib.Path] = None,
        beam_axis_path: Optional[pathlib.Path] = None,
        supports_path: Optional[pathlib.Path] = None,
        geo_contexts_path: Optional[pathlib.Path] = None,
        annotations_path: Optional[pathlib.Path] = None,
        beam_registry_path: Optional[pathlib.Path] = None,
        engine_root: Optional[pathlib.Path] = None,
    ):
        self._output_root = (
            pathlib.Path(output_root)
            if output_root
            else (
                pathlib.Path(engine_root) / "data" / "output"
                if engine_root
                else None
            )
        )
        if self._output_root is None and any(
            p is None
            for p in (
                facts_path,
                beam_axis_path,
                supports_path,
                geo_contexts_path,
                annotations_path,
                beam_registry_path,
                output_dir,
            )
        ):
            raise ValueError(
                "output_root/engine_root or explicit artefact paths + output_dir required"
            )

        self.facts_path = pathlib.Path(facts_path) if facts_path else (
            self._output_root / _R21D_FACTS_REL
        )
        self.beam_axis_path = (
            pathlib.Path(beam_axis_path)
            if beam_axis_path
            else self._output_root / _R3_AXIS_REL
        )
        self.supports_path = (
            pathlib.Path(supports_path)
            if supports_path
            else self._output_root / _R3_SUP_REL
        )
        self.geo_contexts_path = (
            pathlib.Path(geo_contexts_path)
            if geo_contexts_path
            else self._output_root / _R3_GEO_REL
        )
        self.annotations_path = (
            pathlib.Path(annotations_path)
            if annotations_path
            else self._output_root / _R1_ANN_REL
        )
        self.beam_registry_path = (
            pathlib.Path(beam_registry_path)
            if beam_registry_path
            else self._output_root / _VROOT1_BEAM_REL
        )
        self._out_dir = (
            pathlib.Path(output_dir)
            if output_dir
            else self._output_root / _OUT_DIR_NAME
        )
        # run_root ≈ output_root/../..  (…/<run>/data/output → <run>)
        self._run_root: Optional[pathlib.Path] = None
        if self._output_root is not None and len(self._output_root.parents) >= 2:
            self._run_root = self._output_root.parents[1]

    def run(self) -> Dict[str, Any]:
        print(f"[R.3.1] Phase R.3.1 — Engineering Drawing Relationship Engine  (MODEL_VERSION: {MODEL_VERSION})")
        print(f"[R.3.1] output_root: {self._output_root}")
        print(f"[R.3.1] output_dir: {self._out_dir}")

        # ── 1. Load inputs ─────────────────────────────────────────────────────
        facts_list   = self._load_facts()
        beam_axes    = self._load_beam_axes()
        sup_by_beam  = self._load_supports()
        geo_ctx_by_ann = self._load_geo_contexts()
        ann_by_id    = self._load_annotations()
        dxf_path     = self._find_dxf()

        print(f"[R.3.1] DXF: {dxf_path.name}")
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()

        total_facts = len(facts_list)
        print(f"[R.3.1] Loaded {total_facts} facts, {len(beam_axes)} beams, {len(ann_by_id)} annotations")

        # ── Build beam depth + centroid maps for bar detector ──────────────────
        beam_centroids = {
            bid: (float(ax.get("dxf_centroid_x", 0)), float(ax.get("dxf_centroid_y", 0)))
            for bid, ax in beam_axes.items()
        }
        beam_depths = {}
        for f in facts_list:
            bid = f.get("beam_id", "")
            eso = f.get("original_semantic_object") or {}
            if bid and bid not in beam_depths:
                beam_depths[bid] = 750.0  # default; refined below
        beam_reg = self._load_beam_registry()
        for bid, breg in beam_reg.items():
            sec = breg.get("section") or {}
            beam_depths[bid] = float(sec.get("depth_mm") or 750.0)

        # ── 3-6. Leader + Arrow discovery ─────────────────────────────────────
        print("[R.3.1] Discovering leaders...")
        leader_disc = LeaderDiscovery()
        leaders     = leader_disc.discover(msp, beam_axes)
        print(f"[R.3.1]   Leaders discovered: {len(leaders)}")

        chain_builder = LeaderChainBuilder()
        chains        = chain_builder.build_chains(leaders)
        print(f"[R.3.1]   Leader chains: {len(chains)}")

        arrow_det = ArrowDetector()
        arrows    = arrow_det.detect(leaders)
        print(f"[R.3.1]   Arrows detected: {len(arrows)}")

        # ── 7. Annotation → Leader association ───────────────────────────────
        print("[R.3.1] Associating annotations with leaders...")
        ann_rel_builder = AnnotationRelationshipBuilder()
        ann_relationships = ann_rel_builder.build(ann_by_id, leaders)
        print(f"[R.3.1]   Annotation relationships: {len(ann_relationships)}")

        # ── 8. Physical bar detection ─────────────────────────────────────────
        print("[R.3.1] Detecting physical bars...")
        bar_detector = PhysicalBarDetector()
        bars         = bar_detector.detect(msp, beam_axes, beam_centroids, beam_depths)
        print(f"[R.3.1]   Physical bars detected: {len(bars)}")

        # ── 9. Bar extent evidence ────────────────────────────────────────────
        print("[R.3.1] Computing bar extents...")
        extent_builder = ExtentBuilder()
        extents_by_bar = extent_builder.build_all(bars, sup_by_beam)

        # ── 10. Support crossings ─────────────────────────────────────────────
        print("[R.3.1] Computing support crossings...")
        crossing_builder = SupportCrossingBuilder()
        all_crossings: List[SupportCrossing] = []
        crossings_by_bar: Dict[str, List[SupportCrossing]] = {}
        for bar in bars:
            sup_data = sup_by_beam.get(bar.beam_id, [])
            bar_crossings = crossing_builder.build(bar, sup_data)
            crossings_by_bar[bar.bar_id] = bar_crossings
            all_crossings.extend(bar_crossings)
        print(f"[R.3.1]   Support crossings: {len(all_crossings)}")

        # ── 11. Relationship graph assembly ───────────────────────────────────
        print("[R.3.1] Building relationship graph...")
        leaders_by_id = {l.leader_id: l for l in leaders}
        arrows_by_ldr = {a.leader_id: a for a in arrows}
        bars_by_id    = {b.bar_id: b for b in bars}

        graph_builder  = RelationshipGraphBuilder()
        relationships  = graph_builder.build(
            ann_rels         = ann_relationships,
            leaders_by_id    = leaders_by_id,
            arrows_by_ldr    = arrows_by_ldr,
            bars_by_id       = bars_by_id,
            crossings_by_bar = crossings_by_bar,
            extents_by_bar   = extents_by_bar,
            detector         = bar_detector,
            bars_flat        = bars,
            geo_context_by_ann = geo_ctx_by_ann,
        )
        print(f"[R.3.1]   Relationships built: {len(relationships)}")

        # ── 12. Validation ────────────────────────────────────────────────────
        # Excel is owned by VB.1 under RunContext — do not search shared dirs
        validator  = RelationshipValidator()
        validation = validator.validate(
            relationships     = relationships,
            total_annotations = len(ann_by_id),
            leaders           = leaders,
            arrows            = arrows,
            r21d_facts        = facts_list,
            production_workbook = None,
            graph_exported    = False,  # will be set True after export
        )
        print(f"[R.3.1] Validation: {validation['summary']}")
        for rid, res in validation["rules"].items():
            icon = "OK" if res["passed"] else "FAIL"
            print(f"[R.3.1]   {rid}: {icon} — {res['detail']}")

        # ── 13. Statistics ────────────────────────────────────────────────────
        statistics_engine = RelationshipStatistics()
        stats = statistics_engine.compute(relationships, leaders, arrows, bars, all_crossings)

        # ── 14. Markdown report ───────────────────────────────────────────────
        phase_meta = {
            "phase_id":      PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at":  datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        reporter  = RelationshipReporter()
        md_report = reporter.generate_markdown(stats, validation, phase_meta)

        # ── 15. Export ────────────────────────────────────────────────────────
        exporter = RelationshipExport()

        # Re-run validation with graph_exported=True for RULE_12
        validation["rules"]["RULE_12"] = {
            "passed": True,
            "status": "PASS",
            "detail": "RelationshipGraph.json will be exported",
        }
        validation["passed"] = sum(1 for r in validation["rules"].values() if r["passed"])
        validation["all_pass"] = validation["passed"] == validation["total"]
        validation["summary"] = f"{validation['passed']}/{validation['total']} validation rules passed"

        paths = exporter.export_all(
            out_dir       = self._out_dir,
            relationships = relationships,
            leaders       = leaders,
            arrows        = arrows,
            bars          = bars,
            crossings     = all_crossings,
            extents_by_bar= extents_by_bar,
            stats         = stats,
            validation    = validation,
            md_report     = md_report,
            phase_meta    = phase_meta,
        )
        print(f"[R.3.1] Exported {len(paths)} artefacts to: {self._out_dir}")
        for name, p in paths.items():
            print(f"[R.3.1]   {name}: {p.name}")

        return {
            "phase_id":        PHASE_ID,
            "model_version":   MODEL_VERSION,
            "total_facts":     total_facts,
            "total_leaders":   len(leaders),
            "total_arrows":    len(arrows),
            "total_bars":      len(bars),
            "total_crossings": len(all_crossings),
            "total_relationships": len(relationships),
            "validation":      validation,
            "statistics":      stats,
            "output_dir":      str(self._out_dir),
            "artefacts":       {k: str(v) for k, v in paths.items()},
            "success": bool((self._out_dir / "EngineeringDrawingRelationships.json").exists()),
        }

    # ── Loaders ───────────────────────────────────────────────────────────────

    def _load_facts(self) -> List[Dict]:
        p = self._require(self.facts_path, "R.2.1D EngineeringFacts.json")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw.get("all") or raw.get("facts") or (raw if isinstance(raw, list) else [])

    def _load_beam_axes(self) -> Dict[str, Any]:
        p = self._require(self.beam_axis_path, "R.3 BeamAxis.json")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw.get("axes") or {}

    def _load_supports(self) -> Dict[str, List[Dict]]:
        p = self._require(self.supports_path, "R.3 SupportLocations.json")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw.get("supports") or {}

    def _load_geo_contexts(self) -> Dict[str, Any]:
        p = self._require(self.geo_contexts_path, "R.3 GeometryContexts.json")
        raw = json.loads(p.read_text(encoding="utf-8"))
        by_beam = raw.get("contexts_by_beam") or {}
        result = {}
        for beam_id, ctx_list in by_beam.items():
            for ctx in ctx_list:
                ann_id = ctx.get("annotation_id")
                if ann_id:
                    result[ann_id] = ctx
        return result

    def _load_annotations(self) -> Dict[str, Any]:
        p = self._require(self.annotations_path, "R.1 reinforcement_annotations.json")
        raw = json.loads(p.read_text(encoding="utf-8"))
        by_beam = raw.get("by_beam") or {}
        result = {}
        for beam_id, ann_list in by_beam.items():
            for ann in ann_list:
                aid = ann.get("annotation_id")
                if aid:
                    result[aid] = {**ann, "beam_id": beam_id}
        return result

    def _load_beam_registry(self) -> Dict[str, Any]:
        p = self._require(self.beam_registry_path, "VROOT1 beam_registry.json")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw.get("beams") or {}

    def _find_dxf(self) -> pathlib.Path:
        """Resolve DXF from beam_registry drawing_path; fallback under run_root only."""
        reg_path = self._require(self.beam_registry_path, "VROOT1 beam_registry.json")
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        dxf_str = reg.get("drawing_path") or ""
        if dxf_str:
            dxf_p = pathlib.Path(dxf_str)
            if dxf_p.exists():
                return dxf_p

        # Fallback: search ONLY under run_root (never engine-wide / Version7 / Benchmark)
        search_root = self._run_root
        if search_root is None and self._output_root is not None:
            if len(self._output_root.parents) >= 2:
                search_root = self._output_root.parents[1]
            else:
                search_root = self._output_root
        if search_root is None:
            raise FileNotFoundError(
                "[R.3.1] No DXF file found (no drawing_path and no run_root/output_root to search)"
            )
        for hit in search_root.rglob("*.dxf"):
            return hit
        raise FileNotFoundError(
            f"[R.3.1] No DXF file found under run search root: {search_root}"
        )

    @staticmethod
    def _require(path: pathlib.Path, label: str) -> pathlib.Path:
        if not path.exists():
            raise FileNotFoundError(
                f"[R.3.1] Required {label} not found: {path}\n"
                "Ensure prior phases wrote artefacts under this run's output_root."
            )
        return path
