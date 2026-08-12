"""Contact sheets for P2.5.2.2 render-safe crops."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence

# Reuse P2.5.2.1 contact-sheet builder
from PhaseP2521_crop_readability_refinement.contact_sheet import build_contact_sheet

MODEL_VERSION = "10.6.7"


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
        loc = m.get("local_render_safe") or {}
        ctx = m.get("beam_context_render_safe") or {}
        local_tiles.append(
            {
                "path": folder / "local_render_safe.png",
                "status": loc.get("readability_status"),
                "label_lines": [
                    f"{beam} | local | iter {loc.get('iterations_used')}",
                    f"{loc.get('readability_status')}",
                    f"{(m.get('raw_text') or '')[:40]}",
                ],
            }
        )
        ctx_tiles.append(
            {
                "path": folder / "beam_context_render_safe.png",
                "status": ctx.get("readability_status"),
                "label_lines": [
                    f"{beam} | context | iter {ctx.get('iterations_used')}",
                    f"{ctx.get('readability_status')}",
                    f"{(m.get('raw_text') or '')[:40]}",
                ],
            }
        )
    local_sheet = build_contact_sheet(
        tiles=local_tiles,
        out_path=contact_root / "contact_sheet_local_render_safe.png",
        title="P2.5.2.2 — Local Render-Safe Crops (ACTIVE)",
        tile_size=(360, 270),
    )
    ctx_sheet = build_contact_sheet(
        tiles=ctx_tiles,
        out_path=contact_root / "contact_sheet_beam_context_render_safe.png",
        title="P2.5.2.2 — Beam-Context Render-Safe Crops (ACTIVE)",
        tile_size=(360, 270),
    )
    return {
        "local_contact_sheet": local_sheet,
        "beam_context_contact_sheet": ctx_sheet,
        "individual_crops_root": str(candidates_root),
    }


__all__ = ["build_inspection_package"]
