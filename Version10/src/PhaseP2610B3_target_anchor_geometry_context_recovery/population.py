"""Fourth-set discovery wrapper. Reuses frozen P2.6.10-B.1 discovery. No R.1."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PhaseP2610B1_population_generalization.population import discover_fourth_set_population as _discover


def discover_fourth_set_population(version10_root: Path, msp: Any) -> Dict[str, Any]:
    return _discover(version10_root, msp)


__all__ = ["discover_fourth_set_population"]
