"""Load production T18 BeamScoped geometry. Read-only. Not used by P2.6.4 routing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseQA31_pipeline_diagnostics.artefact_locator import ArtefactLocator


def beam_scoped_path(version10_root: Path, set_key: str) -> Optional[Path]:
    locator = ArtefactLocator(Path(version10_root))
    art = locator.locate_set(set_key)
    return art.get("beam_scoped")


def load_beam_scoped_index(version10_root: Path, set_key: str) -> Dict[str, Dict[str, Any]]:
    path = beam_scoped_path(version10_root, set_key)
    if path is None or not path.exists():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    by_beam = doc.get("by_beam") or {}
    if not isinstance(by_beam, dict):
        return {}
    return {str(k): v for k, v in by_beam.items() if isinstance(v, dict)}


__all__ = ["beam_scoped_path", "load_beam_scoped_index"]
