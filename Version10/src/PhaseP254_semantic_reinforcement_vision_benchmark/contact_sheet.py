"""Optional contact sheets for P2.5.4 visual inspection (evaluation labels only)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from PhaseP2521_crop_readability_refinement.contact_sheet import build_contact_sheet

from .candidate_loader import build_evidence_package


def write_contact_sheets(
    *,
    version10_root: Path,
    out_root: Path,
    candidates: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
) -> Dict[str, str]:
    by_id = {r.get("candidate_id"): r for r in results}
    tiles = []
    for c in candidates:
        r = by_id.get(c["candidate_id"]) or {}
        pkg = build_evidence_package(
            candidate=c, version10_root=version10_root, evidence_mode="LOCAL_PLUS_CONTEXT"
        )
        path = pkg.get("local_image_path")
        vi = r.get("validated_interpretation") or {}
        # Evaluation labels only — not Claude-facing
        tiles.append(
            {
                "path": path,
                "status": (r.get("evaluation") or {}).get("evaluation") or "",
                "label_lines": [
                    f"{c.get('beam_id')} {c.get('semantic_class')}",
                    str(c.get("raw_text") or "")[:40],
                    f"{vi.get('semantic_type') or '-'} / {vi.get('role') or '-'}",
                    f"{(r.get('evaluation') or {}).get('evaluation') or '-'}",
                ],
            }
        )
    contact_root = Path(out_root) / "contact_sheets"
    local = build_contact_sheet(
        tiles=tiles,
        out_path=contact_root / "semantic_benchmark_local.png",
        title="P2.5.4 Semantic benchmark (evaluation labels — not Claude-facing)",
        cols=4,
    )
    return {"local": local.get("path")}


__all__ = ["write_contact_sheets"]
