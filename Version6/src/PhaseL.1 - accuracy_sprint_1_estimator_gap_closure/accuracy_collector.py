"""Collect and index all accuracy sprint inputs from available Version6 data."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from accuracy_loader import AccuracyLoader, load_validation_config


class AccuracyCollector:
    """Collect snapshot for Phase L.1 accuracy analysis. Read-only."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._loader = AccuracyLoader(project_root)

    def collect(self) -> Dict[str, Any]:
        snapshot = self._loader.load()
        config = load_validation_config(self._loader.paths["config"])
        snapshot["config"] = config
        snapshot["load_status_summary"] = {
            "loaded": [k for k, v in snapshot["load_status"].items() if v],
            "missing": [k for k, v in snapshot["load_status"].items() if not v],
        }
        return snapshot
