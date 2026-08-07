"""
Locate QA.3.0 mirrors and web_run Track1 artefacts (read-only).
MODEL_VERSION: 10.0.1
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


PRIORITY_FOURTH_BEAMS = (
    "B14", "B15", "B16", "B18", "B19", "B22", "B23", "B29", "B42A", "B45", "B46",
)


@dataclass
class SetArtefacts:
    drawing_set: str
    set_key: str
    mirror_dir: Path
    run_root: Optional[Path] = None
    output_root: Optional[Path] = None
    reinforcement_dxf: Optional[Path] = None
    paths: Dict[str, Path] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def get(self, key: str) -> Optional[Path]:
        p = self.paths.get(key)
        return p if p and p.exists() else None

    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        p = self.get(key)
        if not p:
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            self.warnings.append(f"failed_load {key}: {exc}")
            return None


def _first_existing(*candidates: Path) -> Optional[Path]:
    for c in candidates:
        if c and c.exists():
            return c
    return None


class ArtefactLocator:
    def __init__(self, engine_root: Path, qa30_root: Optional[Path] = None):
        self.engine_root = Path(engine_root)
        self.qa30_root = Path(qa30_root) if qa30_root else (
            self.engine_root / "data" / "output" / "PhaseQA30_unseen_benchmark"
        )
        self.test_input = self.engine_root.parent / "Test_Input"

    def locate_set(self, set_key: str = "Fourth") -> SetArtefacts:
        mirror = self.qa30_root / f"{set_key}_Set_Drawings"
        meta = {}
        if (mirror / "run_metadata.json").exists():
            meta = json.loads((mirror / "run_metadata.json").read_text(encoding="utf-8"))
        drawing_set = meta.get("drawing_set") or f"{set_key} Set Drawings"
        run_root = Path(meta["run_root"]) if meta.get("run_root") else None
        if run_root is None or not run_root.exists():
            # fallback newest matching web_run
            web = self.engine_root / "data" / "web_runs"
            cands = sorted(
                web.glob(f"qa2_{set_key}_Set_Drawings_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ) if web.exists() else []
            run_root = cands[0] if cands else None

        out = (run_root / "data" / "output") if run_root else None
        art = SetArtefacts(
            drawing_set=drawing_set,
            set_key=set_key,
            mirror_dir=mirror,
            run_root=run_root,
            output_root=out,
        )

        # Reinforcement DXF from Test_Input
        ti = self.test_input / f"{set_key} Set Drawings"
        if ti.exists():
            reinf = list((ti / "reinforcement").glob("*.dxf")) if (ti / "reinforcement").exists() else []
            if not reinf:
                reinf = list(ti.rglob("*.dxf"))
            # prefer reinforcement-named
            scored = sorted(
                reinf,
                key=lambda p: (
                    ("reinforc" in p.name.lower() or "beam" in p.name.lower()),
                    p.stat().st_size,
                ),
                reverse=True,
            )
            art.reinforcement_dxf = scored[0] if scored else None

        if out and out.exists():
            art.paths.update(
                {
                    "geometry_envelopes": out
                    / "PhaseT1_geometric_stirrup_evidence"
                    / "geometry_envelopes.json",
                    "beam_ownership": out / "PhaseT18_beam_ownership" / "BeamOwnership.json",
                    "beam_scoped": out
                    / "PhaseT18_beam_ownership"
                    / "BeamScopedAnnotations.json",
                    "ownership_diagnostics": out
                    / "PhaseT18_beam_ownership"
                    / "OwnershipDiagnostics.json",
                    "render_extent_qa": out
                    / "PhaseT182_adaptive_render_extent"
                    / "RenderExtentQA.json",
                    "merged_ownership": out
                    / "PhaseT183_shared_engineering_ownership"
                    / "MergedOwnership.json",
                    "merged_ownership_dedup": out
                    / "PhaseT1831_shared_scope_dedup"
                    / "MergedOwnership.json",
                    "t16_ownership": out
                    / "PhaseT16_entity_ownership"
                    / "beam_entity_ownership.json",
                    "t16_stats": out
                    / "PhaseT16_entity_ownership"
                    / "ownership_statistics.json",
                    "annotation_graph_by_beam": out
                    / "PhaseT17_annotation_graph"
                    / "annotation_graph_by_beam.json",
                    "graph_qa": out
                    / "PhaseT17_annotation_graph"
                    / "graph_qa_diagnostics.json",
                    "render_validation": out
                    / "PhaseT181_render_validation"
                    / "RenderValidation.json",
                    "t182_comparison": out
                    / "PhaseT182_adaptive_render_extent"
                    / "Comparison",
                    "t181_comparison": out
                    / "PhaseT181_render_validation"
                    / "Comparison",
                    "t182_renders": out
                    / "PhaseT182_adaptive_render_extent"
                    / "RenderedBeams",
                    "bbs_summary": out / "Production_Output" / "bbs_summary.json",
                }
            )
        # Mirror fallbacks
        art.paths["mirror_t182"] = mirror / "ComparisonRenders" / "t182_comparison"
        art.paths["mirror_ownership"] = mirror / "EngineeringSummaries" / "BeamOwnership.json"
        art.paths["mirror_merged"] = mirror / "EngineeringSummaries" / "MergedOwnership.json"
        art.paths["benchmark_result"] = mirror / "benchmark_result.json"
        art.paths["production_result"] = mirror / "production_result.json"

        # Prefer mirror comparison if web path missing
        if not art.get("t182_comparison") and art.get("mirror_t182"):
            art.paths["t182_comparison"] = art.paths["mirror_t182"]
        if not art.get("beam_ownership") and art.get("mirror_ownership"):
            art.paths["beam_ownership"] = art.paths["mirror_ownership"]
        if not art.get("merged_ownership") and art.get("mirror_merged"):
            art.paths["merged_ownership"] = art.paths["mirror_merged"]

        # Prefer dedup merged if present
        if art.get("merged_ownership_dedup"):
            art.paths["merged_ownership"] = art.paths["merged_ownership_dedup"]

        return art

    def load_bundle(self, art: SetArtefacts) -> Dict[str, Any]:
        keys = [
            "geometry_envelopes",
            "beam_ownership",
            "beam_scoped",
            "ownership_diagnostics",
            "render_extent_qa",
            "merged_ownership",
            "t16_ownership",
            "t16_stats",
            "annotation_graph_by_beam",
            "graph_qa",
            "render_validation",
            "bbs_summary",
            "benchmark_result",
        ]
        return {k: art.load_json(k) for k in keys}
