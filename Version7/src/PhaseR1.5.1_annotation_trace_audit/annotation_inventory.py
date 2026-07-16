"""Load all pipeline artefacts for annotation forensic audit."""
from __future__ import annotations
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

from .annotation_trace_models import AnnotationInventoryItem
from .dxf_forensic_scanner import DxfForensicScanner


class PipelineDataLoader:

    R1_DIR = "PhaseR.1_generalized_reinforcement_discovery"
    R13_DIR = "PhaseR1.3_pipeline_integration"
    PROD_DIR = "Production_Output"

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self.annotations: Dict[str, List[Dict]] = {}
        self.groups: Dict[str, Dict] = {}
        self.relationships: Dict[str, List[Dict]] = {}
        self.r1_models: Dict[str, Any] = {}
        self.engineering_bars: Dict[str, List[Dict]] = {}
        self.production_models: Dict[str, Any] = {}
        self.steel_json: Dict[str, Any] = {}
        self.bbs_json: Dict[str, Any] = {}
        self.registry: Dict[str, Any] = {}
        self.inventory: List[AnnotationInventoryItem] = []
        self.dxf_y10: List[Dict[str, Any]] = []
        self.dxf_stirrup: List[Dict[str, Any]] = []
        self.steel_summary_computed = None
        self.bbs_rows_computed: List[Any] = []
        self.workbook_path: Optional[pathlib.Path] = None
        self._eng_bar_index: Dict[str, List[Dict]] = {}
        self._rel_by_label: Dict[Tuple[str, str, str], str] = {}

    def load_all(self) -> None:
        r1 = self._v7 / "data/output" / self.R1_DIR
        self.annotations = self._read(r1 / "reinforcement_annotations.json").get("by_beam", {})
        self.groups = self._read(r1 / "reinforcement_groups.json").get("by_beam", {})
        self.relationships = self._read(r1 / "engineering_relationships.json").get("by_beam", {})
        self.r1_models = self._read(r1 / "beam_reinforcement_models.json").get("models", {})
        self.registry = self._read(
            self._v7 / "data/output/PhaseVROOT.1_dynamic_pipeline_initialization"
            / "beam_registry.json"
        )

        eng = self._read(
            self._v7 / "data/output" / self.R13_DIR / "engineering_bar_models.json"
        )
        for beam in eng.get("beams", []):
            self.engineering_bars[beam["beam_id"]] = beam.get("bars", [])

        self.production_models = self._read(
            self._v7 / "data/output" / self.R13_DIR
            / "beam_reinforcement_models_production.json"
        )
        prod = self._v7 / "data/output" / self.PROD_DIR
        self.steel_json = self._read(prod / "steel_weight_summary.json")
        self.bbs_json = self._read(prod / "bbs_summary.json")
        wb = prod / "Estimation_Output.xlsx"
        self.workbook_path = wb if wb.exists() else None

        self._build_rel_index()
        self._build_eng_bar_index()
        self._build_inventory()
        self._dxf_forensic_scan()
        self._recompute_steel_bbs_readonly()

    @staticmethod
    def _read(path: pathlib.Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_rel_index(self) -> None:
        for beam_id, rels in self.relationships.items():
            for rel in rels:
                if rel.get("predicate") != "BELONGS_TO":
                    continue
                meta = rel.get("meta", {})
                key = (beam_id, meta.get("role", ""), rel.get("subject", ""))
                self._rel_by_label[key] = meta.get("group_id", "")

    def _build_eng_bar_index(self) -> None:
        for beam_id, bars in self.engineering_bars.items():
            for i, bar in enumerate(bars):
                gid = bar.get("engineering_metadata", {}).get("group_id", "")
                key = f"{beam_id}|{gid}|{bar.get('bar_role')}|{bar.get('bar_label')}"
                self._eng_bar_index.setdefault(key, []).append({
                    **bar, "trace_bar_id": f"BAR_{beam_id}_{i:04d}",
                })

    def _build_inventory(self) -> None:
        idx = 0
        for beam_id in sorted(self.annotations.keys()):
            for ann in self.annotations[beam_id]:
                self.inventory.append(AnnotationInventoryItem(
                    annotation_id=ann.get("annotation_id", f"ANN_{idx:06d}"),
                    beam_id=beam_id,
                    raw_text=ann.get("clean_text", ""),
                    normalized_text=ann.get("bar_label") or ann.get("clean_text", ""),
                    x=float(ann.get("x", 0)),
                    y=float(ann.get("y", 0)),
                    semantic_role=ann.get("role", ""),
                    diameter_mm=float(ann.get("diameter_mm") or 0),
                    quantity=int(ann.get("quantity") or 0),
                    spacing_mm=ann.get("spacing_mm"),
                    zone=ann.get("position_zone", ""),
                    classification=ann.get("confidence", ""),
                    is_reinforcement=bool(ann.get("is_reinforcement")),
                    source="R.1_DISCOVERED",
                ))
                idx += 1

        discovered_labels = {
            (a.beam_id, a.normalized_text, a.semantic_role)
            for a in self.inventory
        }
        dxf_path = self._resolve_dxf_path()
        if dxf_path:
            scanner = DxfForensicScanner(dxf_path, self.registry)
            for item in scanner.scan_y10():
                norm = item.get("r1_clean_text") or item.get("raw_text", "")
                key = (item.get("nearest_beam_id", ""), norm, "Y10_CANDIDATE")
                if key in discovered_labels:
                    continue
                self.inventory.append(AnnotationInventoryItem(
                    annotation_id=item.get("forensic_id", f"DXF_Y10_{idx}"),
                    beam_id=item.get("nearest_beam_id", ""),
                    raw_text=item.get("raw_text", ""),
                    normalized_text=norm,
                    x=float(item.get("x", 0)),
                    y=float(item.get("y", 0)),
                    semantic_role="Y10_CANDIDATE",
                    diameter_mm=10.0 if "10" in item.get("raw_text", "") else 0,
                    quantity=0,
                    classification="DXF_ONLY",
                    is_reinforcement=False,
                    source="DXF_FORENSIC",
                    nearest_beam_id=item.get("nearest_beam_id", ""),
                ))
                idx += 1
            self.dxf_y10 = scanner.scan_y10()
            self.dxf_stirrup = scanner.scan_stirrup_like()

    def _resolve_dxf_path(self) -> Optional[pathlib.Path]:
        drawing = self.registry.get("drawing_path", "")
        if not drawing:
            return None
        p = pathlib.Path(drawing)
        if p.exists():
            return p
        alt = self._v7.parent / drawing.replace("/", "\\").split("Version7\\")[-1]
        if alt.exists():
            return alt
        alt2 = self._v7 / "data" / "Benchmark_Set_2" / "reinforcement" / p.name
        return alt2 if alt2.exists() else None

    def _dxf_forensic_scan(self) -> None:
        dxf = self._resolve_dxf_path()
        if not dxf:
            return
        scanner = DxfForensicScanner(dxf, self.registry)
        self.dxf_y10 = scanner.scan_y10()
        self.dxf_stirrup = scanner.scan_stirrup_like()

    def _recompute_steel_bbs_readonly(self) -> None:
        prod_path = (
            self._v7 / "data/output" / self.R13_DIR
            / "beam_reinforcement_models_production.json"
        )
        if not prod_path.exists():
            return
        vb1 = self._v7 / "src/PhaseVB.1_production_output_completion"
        if str(vb1) not in sys.path:
            sys.path.insert(0, str(vb1))
        try:
            from steel_weight_completion import SteelWeightCompletion  # type: ignore
            from bbs_completion_engine import BBSCompletionEngine  # type: ignore
            swc = SteelWeightCompletion(prod_path)
            self.steel_summary_computed = swc.compute()
            self.bbs_rows_computed = BBSCompletionEngine(
                self.steel_summary_computed
            ).generate()
        except Exception:
            pass

    def group_for_annotation(self, item: AnnotationInventoryItem) -> Dict[str, Any]:
        if item.source == "DXF_FORENSIC":
            return {}
        beam_groups = self.groups.get(item.beam_id, {})
        grp = beam_groups.get(item.semantic_role, {})
        if grp:
            return grp
        label = item.normalized_text
        gid = self._rel_by_label.get(
            (item.beam_id, item.semantic_role, label), ""
        )
        if gid:
            for role, g in beam_groups.items():
                if g.get("group_id") == gid:
                    return g
        return {}

    def eng_bars_for_group(
        self, beam_id: str, group_id: str, role: str, label: str
    ) -> List[Dict]:
        results = []
        for bar in self.engineering_bars.get(beam_id, []):
            meta = bar.get("engineering_metadata", {})
            if meta.get("group_id") == group_id:
                results.append(bar)
            elif (
                bar.get("bar_role") == role
                and bar.get("bar_label") == label
            ):
                results.append(bar)
        return results
