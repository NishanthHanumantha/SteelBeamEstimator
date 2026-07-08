"""Determine reinforcement region uniqueness within duplicate groups."""

from __future__ import annotations

from typing import Any, Dict, List


class EngineeringRegionDetector:
    """Detect engineering region differences across duplicate members."""

    def analyze(self, contexts: List[dict[str, Any]]) -> dict[str, Any]:
        regions = [str(item.get("engineering_region") or "UNKNOWN") for item in contexts]
        unique_regions = sorted(set(regions))
        layers = [
            str((item.get("drawing_context") or {}).get("layer") or "UNKNOWN") for item in contexts
        ]
        unique_layers = sorted(set(layers))
        return {
            "regions": regions,
            "unique_regions": unique_regions,
            "region_variant": len(unique_regions) > 1,
            "layers": layers,
            "unique_layers": unique_layers,
            "layer_variant": len(unique_layers) > 1,
        }
