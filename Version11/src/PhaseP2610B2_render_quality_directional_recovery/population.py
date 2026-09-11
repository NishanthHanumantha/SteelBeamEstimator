"""Fourth-set population discovery. Reuses P2.6.10-A title localization. No R.1."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP2610B1_population_generalization.population import discover_fourth_set_population as _discover

from .config import DRAWING_SET_KEY


def discover_fourth_set_population(version10_root: Path, msp: Any) -> Dict[str, Any]:
    out = _discover(Path(version10_root), msp)
    out["set_key"] = DRAWING_SET_KEY
    return out


__all__ = ["discover_fourth_set_population"]
