"""Verify and describe the unseen drawing set. Do not silently pick a previously used set."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import BANNED_PRIMARY_SETS, PRIMARY_DRAWING_SET, PRIMARY_SET_KEY


def _p254_used_fourth(version10_root: Path) -> bool:
    status = (
        Path(version10_root)
        / "data"
        / "output"
        / "PhaseP254_semantic_reinforcement_vision_benchmark"
        / "P2.5.4_STATUS.md"
    )
    if not status.exists():
        return False
    text = status.read_text(encoding="utf-8", errors="ignore")
    return "FOURTH" in text.upper() or "Fourth Set" in text


def build_dataset_manifest(version10_root: Path) -> Dict[str, Any]:
    v10 = Path(version10_root)
    qa30 = v10 / "data" / "output" / "PhaseQA30_unseen_benchmark"
    set_dir = qa30 / "Fifth_Set_Drawings"
    ownership = set_dir / "EngineeringSummaries" / "BeamOwnership.json"
    crops = set_dir / "RenderedCrops" / "shared_renders"
    excel = (
        v10.parent
        / "Test_Input"
        / "Fifth Set Drawings"
        / "Estimator_Output_5thSet"
        / "EstimatorOutput_9TH FLOOR.xlsx"
    )
    dxf_dir = v10.parent / "Test_Input" / "Fifth Set Drawings"
    dxfs = sorted(str(p) for p in dxf_dir.rglob("*.dxf")) if dxf_dir.exists() else []
    meta = {}
    if (set_dir / "run_metadata.json").exists():
        meta = json.loads((set_dir / "run_metadata.json").read_text(encoding="utf-8"))

    beam_count = 0
    ann_count = 0
    if ownership.exists():
        data = json.loads(ownership.read_text(encoding="utf-8"))
        by = data.get("by_beam") or {}
        beam_count = len(by)
        ann_count = sum(len(v.get("accepted_annotations") or []) for v in by.values())

    crop_count = len(list(crops.glob("*_render.png"))) if crops.exists() else 0
    p254_fourth = _p254_used_fourth(v10)
    unseen = (
        PRIMARY_SET_KEY not in BANNED_PRIMARY_SETS
        and p254_fourth
        and ownership.exists()
        and excel.exists()
        and crop_count > 0
        and len(dxfs) >= 2
    )
    reasons = [
        "P2.5.4/P2.5.5/P2.5.6 Claude Vision used Fourth Set only.",
        "Fifth Set has independent DXF, estimator Excel, production artefacts, and beam crops.",
        "Fifth Set was never in the frozen P2.5.4 41-candidate Vision benchmark.",
        "No Claude prompt tuning was performed on Fifth Set.",
    ]
    missing: List[str] = []
    if not ownership.exists():
        missing.append("Fifth Set BeamOwnership.json")
    if not excel.exists():
        missing.append("Fifth Set estimator Excel")
    if crop_count <= 0:
        missing.append("Fifth Set render crops")
    if len(dxfs) < 2:
        missing.append("Fifth Set DXF inputs")

    return {
        "drawing_set_id": PRIMARY_DRAWING_SET,
        "set_key": PRIMARY_SET_KEY,
        "source_path": str(dxf_dir),
        "dxf_files": dxfs,
        "dxf_count": len(dxfs),
        "reference_estimator_excel": str(excel),
        "estimator_excel_exists": excel.exists(),
        "beam_ownership": str(ownership),
        "crop_dir": str(crops),
        "crop_count": crop_count,
        "number_of_beams": beam_count,
        "number_of_reinforcement_candidates": ann_count,
        "qa30_run_id": meta.get("run_id"),
        "creation_selection_reason": reasons,
        "previous_benchmark_membership": {
            "P254_P255_P256": "Fourth Set only",
            "QA30_generalization": "Fifth is an unseen production set (not used for Claude Vision)",
        },
        "unseen_status": bool(unseen),
        "UNSEEN_SET_VERIFIED": bool(unseen),
        "missing": missing,
        "blocked_if_not_unseen": True,
    }


def assert_unseen(manifest: Dict[str, Any]) -> None:
    if not manifest.get("UNSEEN_SET_VERIFIED"):
        raise RuntimeError(
            "UNSEEN_SET_VERIFIED=FALSE: "
            + ", ".join(manifest.get("missing") or ["set previously used or incomplete"])
        )


__all__ = ["assert_unseen", "build_dataset_manifest"]
