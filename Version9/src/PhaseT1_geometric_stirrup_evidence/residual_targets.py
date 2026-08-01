"""Load residual target beams for Track 1 scope. MODEL_VERSION: 9.3.0"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

MODEL_VERSION = "9.3.0"


def load_residual_targets(
    engine_root: Path,
    cfg_path: Optional[str] = None,
) -> Dict[str, Any]:
    rel = cfg_path or "data/output/Track1_geometric_evidence/residual_target_beams.json"
    path = Path(engine_root) / rel
    if not path.exists():
        return {"rows": [], "counts": {}, "path": str(path), "missing_file": True}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["path"] = str(path)
    data["missing_file"] = False
    return data


def included_beam_keys(targets: Dict[str, Any]) -> Set[Tuple[str, str]]:
    """Return {(set_id, beam_id)} for included residual rows."""
    out: Set[Tuple[str, str]] = set()
    for r in targets.get("rows") or []:
        if r.get("included"):
            out.add((str(r.get("set_id") or ""), str(r.get("beam_id") or "")))
    return out


def included_beam_ids_for_set(targets: Dict[str, Any], set_id: str) -> Set[str]:
    return {b for s, b in included_beam_keys(targets) if s == set_id}


def target_groups_for_beam(
    targets: Dict[str, Any], set_id: str, beam_id: str
) -> List[str]:
    groups = []
    for r in targets.get("rows") or []:
        if (
            r.get("included")
            and str(r.get("set_id")) == set_id
            and str(r.get("beam_id")) == beam_id
        ):
            g = r.get("target_group")
            if g and g not in groups:
                groups.append(g)
    return groups


def infer_set_id_from_run_root(run_root: Path) -> str:
    name = run_root.name.lower()
    if "first" in name:
        return "Set1"
    if "second" in name:
        return "Set2"
    if "third" in name:
        return "Set3"
    return "Unknown"
