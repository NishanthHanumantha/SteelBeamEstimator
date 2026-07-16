"""
benchmark3_artifact_collector.py — Collect metrics from pipeline outputs.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_V7   = _ROOT / "Version7"
_OUT  = _V7 / "data" / "output"


def _load(path: pathlib.Path) -> Optional[Any]:
    if not path.exists() or path.stat().st_size < 3:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _p(rel: str) -> pathlib.Path:
    return _OUT / rel


class Benchmark3ArtifactCollector:
    """Read-only collector for all phase artefacts."""

    def collect_all(self) -> Dict[str, Any]:
        return {
            "discovery":     self.collect_discovery(),
            "beams":         self.collect_beams(),
            "general_notes": self.collect_general_notes(),
            "reinforcement": self.collect_reinforcement(),
            "interpretation":self.collect_interpretation(),
            "engineering_bars": self.collect_engineering_bars(),
            "production":    self.collect_production(),
        }

    def collect_discovery(self) -> Dict[str, Any]:
        pm  = _load(_p("PhaseVROOT.1_dynamic_pipeline_initialization/project_manifest.json")) or {}
        ctx = _load(_p("PhaseVROOT.1_dynamic_pipeline_initialization/pipeline_context.json")) or {}
        return {
            "project_name":   pm.get("project_name", "UNKNOWN"),
            "building":       pm.get("building", "UNKNOWN"),
            "floor":          pm.get("floor", "UNKNOWN"),
            "input_folder":   pm.get("source_folder") or ctx.get("input_folder", ""),
            "dxf_count":      pm.get("dxf_count", 0),
            "drawing_manifest": _load(
                _V7 / "data/Benchmark_Set_3/benchmark3_manifest.json"
            ),
            "pipeline_context_quality": ctx.get("quality", {}),
        }

    def collect_beams(self) -> Dict[str, Any]:
        reg = _load(_p("PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json")) or {}
        geo = _load(_p("PhaseVROOT.1_dynamic_pipeline_initialization/geometry_registry.json")) or {}
        beam_ids = reg.get("beam_ids") or list((reg.get("beams") or {}).keys())
        beams    = reg.get("beams") or {}

        dupes = [bid for bid, cnt in Counter(beam_ids).items() if cnt > 1]
        geo_beams = geo.get("beams") or geo.get("geometries") or {}
        if isinstance(geo_beams, dict):
            geo_count = len(geo_beams)
        elif isinstance(geo_beams, list):
            geo_count = len(geo_beams)
        else:
            geo_count = 0

        return {
            "total_beams":        reg.get("beam_count") or len(beam_ids),
            "beam_ids":           beam_ids,
            "beam_naming_sample": beam_ids[:10],
            "duplicate_beams":    dupes,
            "missing_beam_numbers": [],
            "registry_coverage_pct": 100.0 if beam_ids else 0.0,
            "geometry_coverage_pct": round(
                100.0 * geo_count / max(len(beam_ids), 1), 1
            ),
            "geometry_beam_count": geo_count,
            "beams_detail_count":  len(beams),
        }

    def collect_general_notes(self) -> Dict[str, Any]:
        ec = _load(_p("PhaseR.2A_engineering_context/engineering_context.json")) or {}
        return {
            "steel_grades":          ec.get("steel_grades") or [ec.get("primary_steel_grade")],
            "concrete_grades":       ec.get("concrete_grades") or [],
            "development_length_table": len(ec.get("development_length_table") or {}),
            "cover_rules":           len(ec.get("cover_rules") or {}),
            "hook_rules":            len(ec.get("hook_rules") or {}),
            "lap_rules":             len(ec.get("lap_rules") or {}),
            "spacer_rules":          len(ec.get("spacer_rules") or {}),
            "code_references":       ec.get("code_references") or [],
            "parse_confidence":      ec.get("parse_confidence", 0.0),
            "gn_dxf_path":           ec.get("gn_dxf_path", ""),
            "dynamically_obtained":  bool(ec.get("gn_dxf_path")),
            "engineering_context_available": bool(ec),
        }

    def collect_reinforcement(self) -> Dict[str, Any]:
        ann  = _load(_p("PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotations.json")) or {}
        r20  = _load(_p("PhaseR2.0_mtext_engineering_text_recovery/mtext_statistics.json")) or {}
        r201 = _load(_p("PhaseR2.0.1_engineering_notation_inventory/engineering_notation_inventory.json")) or {}
        r1_stats = _load(_p("PhaseR.1_generalized_reinforcement_discovery/discovery_statistics.json")) or {}

        by_beam = ann.get("by_beam") or {}
        total_ann = sum(len(v) for v in by_beam.values()) if by_beam else ann.get("total", 0)

        return {
            "text_entities":         r1_stats.get("text_entities") or r1_stats.get("total_text", 0),
            "mtext_entities":        r1_stats.get("mtext_entities") or r1_stats.get("total_mtext", 0),
            "recovered_mtext":       r20.get("recovered_count") or r20.get("total_recovered", 0),
            "reinforcement_annotations": total_ann,
            "unsupported_notations": r201.get("unsupported") or r201.get("unsupported_notations", []),
            "y10_detected":          self._count_diameter(ann, "Y10"),
            "stirrup_detected":      r1_stats.get("stirrup_count", 0),
            "spacer_detected":       r1_stats.get("spacer_count", 0),
            "beams_with_annotations": len(by_beam),
        }

    def collect_interpretation(self) -> Dict[str, Any]:
        sem  = _load(_p("PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json")) or {}
        facts= _load(_p("PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json")) or {}
        geo  = _load(_p("PhaseR3_geometry_context_engine/GeometryContexts.json")) or {}
        rel  = _load(_p("PhaseR3.1_engineering_relationship_engine/EngineeringDrawingRelationships.json")) or {}

        sem_all  = []
        if sem.get("by_beam"):
            for anns in sem["by_beam"].values():
                if isinstance(anns, list):
                    sem_all.extend(anns)
        else:
            sem_all = sem.get("all") or sem.get("objects") or []
        if not sem_all and sem.get("total_objects"):
            sem_all = [None] * int(sem["total_objects"])  # count-only fallback
        facts_all= facts.get("all") or facts.get("facts") or []
        geo_ctxs = geo.get("contexts_by_beam") or {}
        geo_cnt  = sum(len(v) for v in geo_ctxs.values()) if geo_ctxs else geo.get("total", 0)
        rels     = rel.get("relationships") or []
        ann_cnt  = self.collect_reinforcement().get("reinforcement_annotations", 0) or 1

        hyp_cnt = sum(
            len(f.get("intent_hypotheses") or [])
            for f in facts_all if isinstance(f, dict)
        )

        return {
            "semantic_objects":       sem.get("total_objects") or len(sem_all),
            "engineering_facts":      len(facts_all),
            "intent_hypotheses":      hyp_cnt,
            "geometry_contexts":      geo_cnt,
            "drawing_relationships":  len(rels),
            "semantic_coverage_pct":  round(100 * len(sem_all) / ann_cnt, 1),
            "facts_coverage_pct":     round(100 * len(facts_all) / ann_cnt, 1),
            "geometry_coverage_pct":  round(100 * geo_cnt / ann_cnt, 1),
            "relationship_coverage_pct": round(100 * len(rels) / ann_cnt, 1),
            "intent_still_unknown":   all(
                (f.get("intent") or "UNKNOWN") == "UNKNOWN"
                for f in facts_all if isinstance(f, dict)
            ),
        }

    def collect_engineering_bars(self) -> Dict[str, Any]:
        bars = _load(_p("PhaseR1.3_pipeline_integration/engineering_bar_models.json")) or {}
        stats= _load(_p("PhaseR1.3_pipeline_integration/integration_statistics.json")) or {}

        models = bars.get("beams") or bars.get("models") or {}
        if isinstance(models, list):
            beam_cnt = len(models)
            with_bars = sum(1 for m in models if (m.get("bars") or m.get("total_bars", 0)))
        else:
            beam_cnt  = len(models)
            with_bars = sum(
                1 for m in models.values()
                if (m.get("bars") or m.get("total_bars", 0))
            )

        total_beams = self.collect_beams().get("total_beams", 0) or 1
        return {
            "engineering_bar_models": beam_cnt,
            "beams_propagated":       stats.get("beams_propagated") or beam_cnt,
            "beams_with_bars":        with_bars,
            "empty_beams":            max(0, beam_cnt - with_bars),
            "total_bars":             stats.get("total_bars") or bars.get("total_bars", 0),
            "reinforcement_coverage_pct": round(100 * with_bars / total_beams, 1),
            "statistics": stats,
        }

    def collect_production(self) -> Dict[str, Any]:
        prod = _OUT / "Production_Output"
        wb_est  = prod / "Estimation_Output.xlsx"
        wb_eng  = prod / "Engineering_Review.xlsx"
        stats   = _load(prod / "production_statistics.json") or {}
        steel   = _load(prod / "steel_weight_summary.json") or {}
        eng_tot = _load(prod / "engineering_totals.json") or {}
        bbs     = _load(prod / "bbs_summary.json") or {}

        return {
            "workbook_generated":       wb_est.exists(),
            "engineering_review_generated": wb_eng.exists(),
            "steel_quantity_kg":        (
                steel.get("total_weight_kg")
                or eng_tot.get("total_weight_kg")
                or stats.get("total_steel_kg")
                or 0.0
            ),
            "diameter_summary_generated": bool(steel.get("diameter_totals")),
            "beam_summary_generated":     bool(eng_tot.get("beam_totals") or stats.get("total_beams")),
            "bbs_generated":              bool(bbs),
            "bbs_rows":                   bbs.get("total_rows", 0),
            "total_beams_in_production":  stats.get("total_beams", 0),
            "excel_validation": {
                "estimation_exists": wb_est.exists(),
                "estimation_size_kb": round(wb_est.stat().st_size / 1024, 1) if wb_est.exists() else 0,
            },
        }

    @staticmethod
    def _count_diameter(ann_data: dict, dia: str) -> int:
        count = 0
        by_beam = ann_data.get("by_beam") or {}
        for anns in by_beam.values():
            for ann in anns:
                text = str(ann.get("clean_text") or ann.get("text") or "")
                if dia.upper() in text.upper():
                    count += 1
        return count

    def collect_warnings(self) -> List[str]:
        warnings: List[str] = []
        data = self.collect_all()

        reinf = data["reinforcement"]
        if reinf.get("unsupported_notations"):
            warnings.append(
                f"Unsupported reinforcement notations: {len(reinf['unsupported_notations'])}"
            )

        gn = data["general_notes"]
        if not gn.get("engineering_context_available"):
            warnings.append("Engineering Context not generated from General Notes")
        elif gn.get("parse_confidence", 0) < 0.5:
            warnings.append(
                f"Low General Notes parse confidence: {gn.get('parse_confidence', 0):.1%}"
            )

        interp = data["interpretation"]
        if interp.get("relationship_coverage_pct", 0) < 80:
            warnings.append(
                f"Drawing relationship coverage below 80%: "
                f"{interp.get('relationship_coverage_pct', 0)}%"
            )

        bars = data["engineering_bars"]
        if bars.get("empty_beams", 0) > 0:
            warnings.append(f"{bars['empty_beams']} beams have no engineering bars")

        prod = data["production"]
        if not prod.get("workbook_generated"):
            warnings.append("Production workbook (Estimation_Output.xlsx) not generated")

        rel_val = _load(_p("PhaseR3.1_engineering_relationship_engine/RelationshipValidation.json")) or {}
        if rel_val and not rel_val.get("all_pass"):
            warnings.append(
                f"R.3.1 validation: {rel_val.get('summary', 'issues detected')}"
            )

        return warnings
