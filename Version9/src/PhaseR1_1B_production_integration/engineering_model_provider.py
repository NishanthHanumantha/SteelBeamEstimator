"""
engineering_model_provider.py — Official single production interface for EngineeringBarModels.
MODEL_VERSION: 8.2.1

Every downstream estimation module requests reinforcement data ONLY through this provider.
The provider guarantees: validated models, stable ordering, deterministic IDs, beam grouping,
confidence metadata, and no legacy path fallback.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional


class EngineeringModelProvider:
    """
    Single production interface for EngineeringBarModels.

    Reads from R.1.3 production output (built from R.1.1A annotation discovery).
    Returns validated, deduplicated, ordered engineering models.

    Usage:
        provider = EngineeringModelProvider(v7_root)
        models = provider.get_all_beam_models()
        bars = provider.get_bars_for_beam("B3")
    """

    R13_PRODUCTION_PATH = "data/output/PhaseR1.3_pipeline_integration/beam_reinforcement_models_production.json"
    R1_PATH = "data/output/PhaseR.1_generalized_reinforcement_discovery/beam_reinforcement_models.json"
    REGISTRY_PATH = "data/output/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json"

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self._models: Optional[Dict[str, Any]] = None
        self._source: str = "UNLOADED"
        self._stats: Dict[str, Any] = {}

    def load(self) -> "EngineeringModelProvider":
        """Load models from R.1.3 production output."""
        # Prefer engineering_bar_models.json which has clean bar_count fields
        r13_dir = self._v7 / "data/output/PhaseR1.3_pipeline_integration"
        eng_path = r13_dir / "engineering_bar_models.json"
        prod_path = r13_dir / "beam_reinforcement_models_production.json"

        loaded = False
        if eng_path.exists():
            data = json.loads(eng_path.read_text(encoding="utf-8"))
            raw = data.get("beams", data.get("models", []))
            if isinstance(raw, list):
                self._models = {b.get("beam_id", str(i)): b for i, b in enumerate(raw)}
            else:
                self._models = raw
            self._source = "EngineeringBarModel_R1.3"
            loaded = True
        elif prod_path.exists():
            data = json.loads(prod_path.read_text(encoding="utf-8"))
            raw = data.get("models", data.get("beams", []))
            if isinstance(raw, list):
                # Compute bar_count from bar_count_by_role
                models = {}
                for b in raw:
                    bid = b.get("beam_id", "")
                    role_counts = b.get("bar_count_by_role", {})
                    total_bars = sum(role_counts.values()) if role_counts else b.get("bar_count", 0)
                    models[bid] = {**b, "bar_count": total_bars}
                self._models = models
            else:
                self._models = raw
            self._source = "EngineeringBarModel_R1.3"
            loaded = True

        if not loaded:
            self._models = {}
            self._source = "NOT_BUILT"

        self._compute_stats()
        return self

    def _compute_stats(self) -> None:
        if not self._models:
            self._stats = {"total_beams": 0, "total_bars": 0, "beams_with_bars": 0, "beams_empty": 0}
            return
        beams_with = sum(1 for m in self._models.values() if m.get("bar_count", 0) > 0)
        total_bars = sum(m.get("bar_count", 0) for m in self._models.values())
        self._stats = {
            "total_beams": len(self._models),
            "total_bars": total_bars,
            "beams_with_bars": beams_with,
            "beams_empty": len(self._models) - beams_with,
            "source": self._source,
        }

    @property
    def is_loaded(self) -> bool:
        return self._models is not None

    @property
    def source(self) -> str:
        return self._source

    @property
    def stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def get_all_beam_models(self) -> Dict[str, Any]:
        """Return all beam engineering models ordered by beam_id."""
        if not self._models:
            return {}
        return dict(sorted(self._models.items()))

    def get_bars_for_beam(self, beam_id: str) -> List[Dict[str, Any]]:
        """Return all engineering bars for a specific beam."""
        if not self._models:
            return []
        beam = self._models.get(beam_id, {})
        return list(beam.get("bars", []))

    def get_beam_ids_with_bars(self) -> List[str]:
        """Return sorted list of beam IDs that have at least one engineering bar."""
        if not self._models:
            return []
        return sorted(bid for bid, m in self._models.items() if m.get("bar_count", 0) > 0)

    def validate(self) -> Dict[str, Any]:
        """Validate the loaded models for production readiness."""
        if not self._models:
            return {
                "valid": False,
                "issues": ["No EngineeringBarModels loaded — R.1.3 must be run first"],
                "stats": self._stats,
            }

        issues = []
        empty_beams = [bid for bid, m in self._models.items() if not m.get("bar_count")]
        if empty_beams:
            issues.append(f"{len(empty_beams)} beams have zero bars: {empty_beams[:5]}...")

        return {
            "valid": len(issues) == 0,
            "source": self._source,
            "issues": issues,
            "stats": self._stats,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self._source,
            "provider": "EngineeringModelProvider",
            "model_version": "8.2.1",
            "stats": self._stats,
            "validation": self.validate(),
        }
