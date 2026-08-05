"""
QA.2B.0 — Latest production path registry (no legacy Version8 / obsolete caches).
MODEL_VERSION: 9.6.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.6.0"

# Logical → relative paths under {web_run}/data/output/
LATEST_ARTEFACTS: Dict[str, str] = {
    "engineering_excel": "Production_Output/Estimation_Output.xlsx",
    "stirrup_recovery": "PhaseT1_geometric_stirrup_evidence/stirrup_geometry_evidence.json",
    "geometry_envelopes": "PhaseT1_geometric_stirrup_evidence/geometry_envelopes.json",
    "opencv_crops": "PhaseT1_geometric_stirrup_evidence/opencv_renders",
    "entity_ownership": "PhaseT16_entity_ownership/beam_entity_ownership.json",
    "annotation_graph": "PhaseT17_annotation_graph/AnnotationGraph.json",
    "beam_ownership": "PhaseT18_beam_ownership/BeamOwnership.json",
    "beam_scoped": "PhaseT18_beam_ownership/BeamScopedAnnotations.json",
    "adaptive_renders": "PhaseT182_adaptive_render_extent/RenderedBeams",
    "shared_ownership": "PhaseT183_shared_engineering_ownership/MergedOwnership.json",
    "shared_renders": "PhaseT183_shared_engineering_ownership/RenderedBeams",
    "dedup_registry": "PhaseT1831_shared_scope_dedup/SharedAnnotationRegistry.json",
    "dedup_merged": "PhaseT1831_shared_scope_dedup/MergedOwnership.json",
}

# Ordered crop preference (latest → fallback). No Version8 / Track1-legacy first.
CROP_PREFERENCE: List[Tuple[str, str]] = [
    ("shared_ownership_render", "PhaseT183_shared_engineering_ownership/RenderedBeams/{beam}_render.png"),
    ("adaptive_extent_render", "PhaseT182_adaptive_render_extent/RenderedBeams/{beam}_render.png"),
    ("ownership_render_validation", "PhaseT181_render_validation/RenderedBeams/{beam}_render.png"),
    ("t16_owned_render", "PhaseT16_entity_ownership/{beam}/filtered_render.png"),
    ("opencv_crop", "PhaseT1_geometric_stirrup_evidence/opencv_renders/{beam}_crop.png"),
]

LEGACY_FORBIDDEN_SUBSTRINGS = (
    "Version8/",
    "Version8\\",
    "Version7/",
    "Version7\\",
    "_9_3_2_before_backup",
    "t15_benchmark/before",
)


def resolve_latest_web_run(web_runs: Path, set_key: str) -> Optional[Path]:
    """
    set_key examples: First, Second, Third (matched against qa2_* folder names).
    """
    web_runs = Path(web_runs)
    if not web_runs.exists():
        return None
    key = set_key.lower().replace(" ", "_")
    candidates = [
        p
        for p in web_runs.iterdir()
        if p.is_dir() and p.name.lower().startswith("qa2_") and key in p.name.lower()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


def output_root(run_root: Path) -> Path:
    return Path(run_root) / "data" / "output"


def artefact_path(run_root: Path, logical: str) -> Path:
    rel = LATEST_ARTEFACTS[logical]
    return output_root(run_root) / rel


def resolve_beam_crop(run_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    """Return first existing latest crop/render for beam (never legacy-first)."""
    out = output_root(run_root)
    for source, template in CROP_PREFERENCE:
        path = out / template.format(beam=beam_id)
        if path.exists():
            sp = str(path)
            if any(x in sp for x in LEGACY_FORBIDDEN_SUBSTRINGS):
                continue
            return {
                "beam_id": beam_id,
                "path": str(path),
                "source": source,
                "model_version": MODEL_VERSION,
            }
    return None


def list_beam_ids_from_envelopes(run_root: Path) -> List[str]:
    import json

    path = artefact_path(run_root, "geometry_envelopes")
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = sorted((data.get("by_beam") or {}).keys())
        if ids:
            return ids

    # Prefer beams that already have T1 evidence / opencv crops
    ev = artefact_path(run_root, "stirrup_recovery")
    if ev.exists():
        data = json.loads(ev.read_text(encoding="utf-8"))
        ids = sorted((data.get("by_beam") or {}).keys())
        if ids:
            return ids

    crop_dir = artefact_path(run_root, "opencv_crops")
    if crop_dir.exists():
        return sorted(
            {
                p.name.replace("_crop.png", "").replace("_notext.png", "")
                for p in crop_dir.glob("B*_crop.png")
            }
        )
    return []
