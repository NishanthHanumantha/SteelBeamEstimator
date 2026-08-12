"""Contact sheets for P2.5.2.3."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP2521_crop_readability_refinement.contact_sheet import build_contact_sheet

MODEL_VERSION = "10.6.8"


def build_inspection_package(
    *,
    manifests: List[Dict[str, Any]],
    candidates_root: Path,
    contact_root: Path,
) -> Dict[str, Any]:
    contact_root = Path(contact_root)
    contact_root.mkdir(parents=True, exist_ok=True)
    local_tiles = []
    ctx_tiles = []
    for m in manifests:
        cid = m.get("candidate_id") or ""
        beam = m.get("beam_id")
        folder = Path(candidates_root) / cid.replace("::", "__")
        loc = m.get("local_target_complete") or {}
        ctx = m.get("beam_context_target_complete") or {}
        reasons = ",".join((loc.get("completeness_reason_codes") or [])[:3])
        local_tiles.append(
            {
                "path": folder / "local_target_complete.png",
                "status": "READABILITY_" + str(loc.get("target_beam_visual_completeness") or ""),
                "label_lines": [
                    f"{beam} | {aid_short(m)} | {loc.get('target_beam_visual_completeness')}",
                    f"{(m.get('raw_text') or '')[:36]}",
                    reasons[:48],
                ],
            }
        )
        ctx_tiles.append(
            {
                "path": folder / "beam_context_target_complete.png",
                "status": "READABILITY_" + str(ctx.get("target_beam_visual_completeness") or ""),
                "label_lines": [
                    f"{beam} | ctx | {ctx.get('target_beam_visual_completeness')}",
                    f"{(m.get('raw_text') or '')[:36]}",
                    ",".join((ctx.get("completeness_reason_codes") or [])[:3])[:48],
                ],
            }
        )
    return {
        "local_contact_sheet": build_contact_sheet(
            tiles=local_tiles,
            out_path=contact_root / "contact_sheet_local_target_complete.png",
            title="P2.5.2.3 — Local Target-Beam Complete (ACTIVE)",
            tile_size=(380, 280),
        ),
        "beam_context_contact_sheet": build_contact_sheet(
            tiles=ctx_tiles,
            out_path=contact_root / "contact_sheet_beam_context_target_complete.png",
            title="P2.5.2.3 — Beam-Context Target-Beam Complete (ACTIVE)",
            tile_size=(380, 280),
        ),
        "individual_crops_root": str(candidates_root),
    }


def aid_short(m: Dict[str, Any]) -> str:
    a = str(m.get("annotation_id") or "")
    return a[:12] if a else "?"


__all__ = ["build_inspection_package"]
