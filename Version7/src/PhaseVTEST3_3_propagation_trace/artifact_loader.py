"""
artifact_loader.py — Load Benchmark Set 3 pipeline artefacts (read-only).
MODEL_VERSION: 8.1.4
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional, Set, Tuple


class PropagationArtifactLoader:

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self._out = v7_root / "data" / "output"
        self.annotations_by_beam: Dict[str, List[Dict]] = {}
        self.r1_models: Dict[str, Any] = {}
        self.groups_by_beam: Dict[str, Dict] = {}
        self.semantic_by_id: Dict[str, Dict] = {}
        self.facts_by_id: Dict[str, Dict] = {}
        self.hypotheses_by_id: Dict[str, Dict] = {}
        self.geometry_by_id: Dict[str, Dict] = {}
        self.relationships_by_id: Dict[str, Dict] = {}
        self.engineering_bars_by_beam: Dict[str, List[Dict]] = {}
        self.propagation_matrix: Dict[str, Dict] = {}
        self.steel_by_beam: Dict[str, Dict] = {}
        self.bbs_rows: List[Dict] = []
        self.beam_registry: Dict[str, Any] = {}
        self.r1_statistics: Dict[str, Any] = {}
        self.all_beam_ids: List[str] = []

    def load_all(self) -> None:
        r1 = self._out / "PhaseR.1_generalized_reinforcement_discovery"
        self.annotations_by_beam = self._read(r1 / "reinforcement_annotations.json").get("by_beam", {})
        self.r1_models = self._read(r1 / "beam_reinforcement_models.json").get("models", {})
        self.groups_by_beam = self._read(r1 / "reinforcement_groups.json").get("by_beam", {})
        self.r1_statistics = self._read(r1 / "reinforcement_statistics.json")

        reg = self._read(
            self._out / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
        )
        self.beam_registry = reg.get("beams", reg)

        sem = self._read(
            self._out / "PhaseR2.1B_engineering_semantic_interpreter"
            / "engineering_semantic_objects.json"
        )
        for items in sem.get("by_beam", {}).values():
            for obj in items:
                self.semantic_by_id[obj["annotation_id"]] = obj

        facts = self._read(
            self._out / "PhaseR2.1C_engineering_fact_normalization" / "EngineeringFacts.json"
        )
        for fact in facts.get("all", []):
            self.facts_by_id[fact["annotation_id"]] = fact

        hyp = self._read(
            self._out / "PhaseR2.1D_evidence_hypothesis_engine" / "IntentHypotheses.json"
        )
        for items in hyp.get("by_beam", {}).values():
            for h in items:
                self.hypotheses_by_id[h["annotation_id"]] = h

        geo = self._read(self._out / "PhaseR3_geometry_context_engine" / "GeometryContexts.json")
        for items in geo.get("contexts_by_beam", {}).values():
            for ctx in items:
                self.geometry_by_id[ctx["annotation_id"]] = ctx

        rel = self._read(
            self._out / "PhaseR3.1_engineering_relationship_engine"
            / "EngineeringDrawingRelationships.json"
        )
        for r in rel.get("relationships", []):
            self.relationships_by_id[r["annotation_id"]] = r

        ebm = self._read(
            self._out / "PhaseR1.3_pipeline_integration" / "engineering_bar_models.json"
        )
        for beam in ebm.get("beams", []):
            self.engineering_bars_by_beam[beam["beam_id"]] = beam.get("bars", [])

        pm = self._read(
            self._out / "PhaseR1.3_pipeline_integration" / "beam_propagation_matrix.json"
        )
        for b in pm.get("beams", []):
            self.propagation_matrix[b["beam_id"]] = b

        steel = self._read(self._out / "Production_Output" / "steel_weight_summary.json")
        for bw in steel.get("beam_weights", []):
            self.steel_by_beam[bw["beam_id"]] = bw

        bbs = self._read(self._out / "Production_Output" / "bbs_summary.json")
        self.bbs_rows = bbs.get("rows", [])

        self.all_beam_ids = sorted(self.beam_registry.keys())

    @staticmethod
    def _read(path: pathlib.Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Required artefact missing: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def group_for_annotation(self, ann: Dict) -> Optional[Dict]:
        beam_id = ann.get("beam_id") or ""
        role = ann.get("role", "")
        groups = self.groups_by_beam.get(beam_id, {})
        return groups.get(role)

    def eng_bars_for_annotation(self, ann: Dict) -> List[Dict]:
        beam_id = ann.get("beam_id", "")
        role = ann.get("role", "")
        label = ann.get("bar_label") or ann.get("clean_text", "")
        bars = self.engineering_bars_by_beam.get(beam_id, [])
        matched = []
        for bar in bars:
            if bar.get("bar_role") != role:
                continue
            if label and bar.get("bar_label") == label:
                matched.append(bar)
            elif int(bar.get("quantity", 0)) == int(ann.get("quantity", 0)):
                matched.append(bar)
        if not matched:
            matched = [b for b in bars if b.get("bar_role") == role]
        return matched

    def steel_for_beam(self, beam_id: str) -> Optional[Dict]:
        bw = self.steel_by_beam.get(beam_id)
        if bw and bw.get("total_weight_kg", 0) > 0:
            return bw
        return None

    def bbs_for_beam(self, beam_id: str) -> List[Dict]:
        return [
            r for r in self.bbs_rows
            if r.get("beam_id") == beam_id and not r.get("is_beam_header")
        ]

    def workbook_reached(self, beam_id: str) -> bool:
        wb = self._out / "Production_Output" / "Estimation_Output.xlsx"
        return wb.exists() and beam_id in self.steel_by_beam
