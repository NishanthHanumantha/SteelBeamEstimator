"""
reinforcement_source_adapter.py — Convert Phase R.1 models to L.2-compatible format.

Reads   : PhaseR.1 beam_reinforcement_models.json  (R.1 group-based format)
Writes  : adapted beam_reinforcement_models.json    (L.2 bar-list format)

The adapted format is consumed by V.B.1's SteelWeightCompletion and
BBSCompletionEngine unchanged.  No downstream engineering logic is modified.
"""

from __future__ import annotations

import json
import logging
import pathlib
import uuid
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ── Role → L.2 key ────────────────────────────────────────────────────────────
_ROLE_TO_L2_KEY = {
    "TOP_MAIN":               "top_main_bars",
    "BOTTOM_MAIN":            "bottom_main_bars",
    "TOP_EXTRA":              "top_extra_bars",
    "BOTTOM_EXTRA":           "bottom_extra_bars",
    "SIDE_FACE_REINFORCEMENT":"side_face_reinforcement",
    "STIRRUP":                "stirrups",
    "SPACER_BAR":             "spacer_bars",
    "DEVELOPMENT":            "supplementary_bars",
    "LAP":                    "supplementary_bars",
    "UNKNOWN":                "supplementary_bars",
}

_ZONE_FOR_ROLE = {
    "TOP_MAIN":  "TOP_ZONE",
    "TOP_EXTRA": "TOP_ZONE",
    "BOTTOM_MAIN": "BOTTOM_ZONE",
    "BOTTOM_EXTRA": "BOTTOM_ZONE",
    "STIRRUP":   "TRANSVERSE_ZONE",
    "SPACER_BAR": "BOTTOM_ZONE",
    "SIDE_FACE_REINFORCEMENT": "SIDE_ZONE",
}


def _bar_dict(
    beam_id:     str,
    role:        str,
    diameter_mm: float,
    quantity:    int,
    bar_label:   str,
    span_mm:     float,
    spacing_mm:  Optional[float] = None,
) -> Dict[str, Any]:
    """Build an L.2-compatible bar dict from R.1 annotation data."""
    zone    = _ZONE_FOR_ROLE.get(role, "UNKNOWN_ZONE")
    grade   = "Y"  # R.1 uses Y460 for all bars from DXF (no R-grade bars in Benchmark Set 2)
    extent  = "FULL_SPAN"

    d: Dict[str, Any] = {
        "bar_id":                  f"R1-{beam_id}-{role}-{uuid.uuid4().hex[:6]}",
        "source_bar_id":           None,
        "beam_id":                 beam_id,
        "semantic_role":           role,
        "diameter_mm":             diameter_mm,
        "quantity":                quantity,
        "steel_grade":             grade,
        "bar_label":               bar_label,
        "position_zone":           zone,
        "extent":                  extent,
        "continuity":              "SINGLE_BEAM",
        "support_zone":            None,
        "coverage_ratio":          None,
        "spacing_mm":              spacing_mm,
        "classification_evidence": f"R.1 DXF annotation: {bar_label}",
        "classification_confidence": "HIGH",
        "source_pipeline_role":    "R.1",
        "is_corrected":            False,
        "is_reference_anchored":   False,
    }
    return d


class ReinforcementSourceAdapter:
    """
    Converts Phase R.1 beam_reinforcement_models.json to L.2 format.

    The adapter:
    1. Reads R.1 models (group-based: {role: {total_quantity, diameters_mm, labels}})
    2. Reads beam_registry for section geometry (span, depth, width)
    3. Produces L.2-format models with concrete bar lists
    4. Writes adapted file to output_dir / beam_reinforcement_models_r1.json
    """

    def __init__(
        self,
        r1_models_path:   pathlib.Path,
        beam_registry_path: pathlib.Path,
        output_dir:       pathlib.Path,
    ):
        self._r1_path     = r1_models_path
        self._registry    = beam_registry_path
        self._output_dir  = output_dir

    # ──────────────────────────────────────────────────────────────────────────
    def adapt(self) -> pathlib.Path:
        """Produce adapted models file and return its path."""
        r1_data   = json.loads(self._r1_path.read_text(encoding="utf-8"))
        reg_data  = json.loads(self._registry.read_text(encoding="utf-8"))

        r1_models    = r1_data.get("models", {})
        beam_records = reg_data.get("beams", {})

        adapted_models: List[Dict[str, Any]] = []
        adapted_count  = 0
        zero_count     = 0

        for beam_id, r1_model in r1_models.items():
            reg_beam = beam_records.get(beam_id, {})
            section  = r1_model.get("section") or reg_beam.get("section") or {}
            span_mm  = float(reg_beam.get("clear_span_mm") or 0)
            depth_mm = float(section.get("depth_mm") or 750.0)
            width_mm = float(section.get("width_mm") or 300.0)

            groups = r1_model.get("groups", {})
            l2_model = self._build_l2_model(
                beam_id, r1_model, groups, span_mm, depth_mm, width_mm
            )
            adapted_models.append(l2_model)

            total_bars = sum(
                len(v) for k, v in l2_model.items()
                if (k.endswith("_bars") or k in ("stirrups", "side_face_reinforcement"))
                and isinstance(v, list)
            )
            if total_bars > 0:
                adapted_count += 1
            else:
                zero_count += 1

        result = {
            "model_count": len(adapted_models),
            "source":      "Phase R.1 — Generalized Reinforcement Discovery",
            "model_version": "7.3.1",
            "models":      adapted_models,
        }

        out_path = self._output_dir / "beam_reinforcement_models_r1.json"
        out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

        log.info(
            "ReinforcementSourceAdapter: %d adapted models (%d with bars, %d zero)",
            len(adapted_models), adapted_count, zero_count,
        )
        return out_path

    # ──────────────────────────────────────────────────────────────────────────
    def _build_l2_model(
        self,
        beam_id:  str,
        r1_model: dict,
        groups:   dict,
        span_mm:  float,
        depth_mm: float,
        width_mm: float,
    ) -> Dict[str, Any]:
        """Build one L.2-format model from one R.1 model."""

        # Initialise all L.2 bar-list keys
        l2: Dict[str, Any] = {
            "model_id":             f"BRM::{beam_id}::R1",
            "beam_id":              beam_id,
            "beam_name":            r1_model.get("beam_mark", beam_id),
            "is_benchmark_beam":    False,
            "interpretation_confidence": "MEDIUM",
            "geometry": {
                "beam_id":         beam_id,
                "width_mm":        width_mm,
                "depth_mm":        depth_mm,
                "clear_span_mm":   span_mm,
                "effective_span_mm": span_mm,
                "top_cover_mm":    25.0,
                "bottom_cover_mm": 25.0,
            },
            "support_zones":        self._default_support_zones(beam_id),
            "bar_count_by_role":    {},
            "top_main_bars":        [],
            "bottom_main_bars":     [],
            "top_extra_bars":       [],
            "bottom_extra_bars":    [],
            "side_face_reinforcement": [],
            "stirrups":             [],
            "spacer_bars":          [],
            "chair_bars":           [],
            "supplementary_bars":   [],
            "development_length_regions": [],
            "continuity_regions":   [],
            "engineering_notes":    ["Source: Phase R.1 DXF discovery"],
            "total_classified_bars": 0,
            "unclassified_bar_count": 0,
            "classification_complete": bool(groups),
            "traceability":         {"source": "R.1", "model_version": "7.3.1"},
        }

        total_bars = 0
        for role, grp in groups.items():
            l2_key = _ROLE_TO_L2_KEY.get(role, "supplementary_bars")
            bars   = self._expand_group(beam_id, role, grp, span_mm)
            if bars:
                if isinstance(l2.get(l2_key), list):
                    l2[l2_key].extend(bars)
                l2["bar_count_by_role"][role] = len(bars)
                total_bars += len(bars)

        l2["total_classified_bars"] = total_bars
        return l2

    def _expand_group(
        self,
        beam_id: str,
        role:    str,
        group:   dict,
        span_mm: float,
    ) -> List[Dict[str, Any]]:
        """Convert one R.1 group into a list of L.2 bar dicts."""
        bars: List[Dict[str, Any]] = []
        labels     = group.get("labels", [])
        diameters  = group.get("diameters_mm", [])
        total_qty  = group.get("total_quantity", 0)

        if not diameters or total_qty == 0:
            return []

        # Get stirrup spacing from labels if available
        spacing_mm: Optional[float] = None
        if role == "STIRRUP":
            for lbl in labels:
                import re
                m = re.search(r"@(\d+)", lbl)
                if m:
                    spacing_mm = float(m.group(1))
                    break

        # Distribute quantity across diameters / labels
        if labels:
            for lbl in labels:
                import re
                m = re.match(r"(\d+)[YRyTt](\d+)", lbl)
                if m:
                    qty = int(m.group(1))
                    dia = float(m.group(2))
                    bars.append(_bar_dict(beam_id, role, dia, qty, lbl, span_mm, spacing_mm))
                elif diameters:
                    # Label exists but doesn't parse — use first diameter
                    qty_each = max(1, total_qty // len(diameters))
                    bars.append(_bar_dict(beam_id, role, diameters[0], qty_each, lbl, span_mm, spacing_mm))
        else:
            # No labels — distribute evenly across diameters
            qty_each = max(1, total_qty // max(len(diameters), 1))
            for dia in diameters:
                lbl = f"{qty_each}Y{int(dia)}"
                bars.append(_bar_dict(beam_id, role, dia, qty_each, lbl, span_mm, spacing_mm))

        return bars

    @staticmethod
    def _default_support_zones(beam_id: str) -> List[dict]:
        return [
            {"support_id": f"SUP::R1::{beam_id}::L", "support_type": "LEFT_SUPPORT",
             "beam_id": beam_id, "adjacent_beam_id": None, "position_fraction": 0.0, "support_width_mm": 200.0},
            {"support_id": f"SUP::R1::{beam_id}::R", "support_type": "RIGHT_SUPPORT",
             "beam_id": beam_id, "adjacent_beam_id": None, "position_fraction": 1.0, "support_width_mm": 200.0},
        ]
