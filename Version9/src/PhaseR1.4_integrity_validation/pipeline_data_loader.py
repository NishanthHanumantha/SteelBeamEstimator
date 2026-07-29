"""Load pipeline artefacts for integrity validation."""
from __future__ import annotations
import json
import pathlib
from typing import Any, Dict, List, Optional, Set


class PipelineDataLoader:
    """Loads beam registry, engineering bar models, and R.1 discovery data."""

    def __init__(self, v7_root: pathlib.Path, config: Dict[str, Any]):
        self._v7 = v7_root
        self._config = config
        self._registry: Dict[str, Any] = {}
        self._engineering: Dict[str, Any] = {}
        self._r1: Dict[str, Any] = {}
        self._production: Dict[str, Any] = {}

    def load_all(self) -> None:
        self._registry = self._load_json(self._resolve("input.beam_registry"))
        self._engineering = self._load_json(self._resolve("input.engineering_bar_models"))
        self._r1 = self._load_json(self._resolve("input.r1_models"))
        prod_path = self._resolve("input.production_models")
        if prod_path.exists():
            self._production = self._load_json(prod_path)

    def _resolve(self, key: str) -> pathlib.Path:
        parts = key.split(".")
        val = self._config
        for p in parts:
            val = val[p]
        path_str = str(val)
        if path_str.startswith("Version8/"):
            return self._v7 / path_str[len("Version8/"):]
        return self._v7 / path_str

    @staticmethod
    def _load_json(path: pathlib.Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def registry_beam_ids(self) -> Set[str]:
        ids = self._registry.get("beam_ids", [])
        if ids:
            return set(ids)
        beams = self._registry.get("beams", {})
        return set(beams.keys())

    def registry_beam_count(self) -> int:
        count = self._registry.get("beam_count")
        if count is not None:
            return int(count)
        return len(self.registry_beam_ids())

    def engineering_beams(self) -> List[Dict[str, Any]]:
        return self._engineering.get("beams", [])

    def engineering_beam_ids(self) -> Set[str]:
        return {b["beam_id"] for b in self.engineering_beams() if b.get("beam_id")}

    def engineering_bars(self) -> List[Dict[str, Any]]:
        bars = []
        for beam in self.engineering_beams():
            for bar in beam.get("bars", []):
                bars.append({**bar, "_parent_geometry": beam.get("geometry", {})})
        return bars

    def r1_models(self) -> Dict[str, Any]:
        return self._r1.get("models", {})

    def r1_beam_ids(self) -> Set[str]:
        return set(self.r1_models().keys())

    def r1_beam_has_groups(self, beam_id: str) -> bool:
        model = self.r1_models().get(beam_id, {})
        groups = model.get("groups", {})
        return any(
            int(g.get("total_quantity") or 0) > 0
            for g in groups.values()
        )

    def production_models(self) -> List[Dict[str, Any]]:
        return self._production.get("models", [])

    def production_source(self) -> str:
        return self._production.get("source", "")

    def reinforcement_source_path(self) -> Optional[pathlib.Path]:
        return self._resolve("input.production_models")
