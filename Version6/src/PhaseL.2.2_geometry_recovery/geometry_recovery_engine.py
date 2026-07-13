"""
Engineering Geometry Recovery Engine — Phase L.2.2 core.

Purpose
-------
Detect beams that are present in the pipeline (drawing parser, engineering
objects, specifications) but have NO bars in the L.2 BeamReinforcementModel,
recover their geometry from available data sources, inject placeholder bars,
write an extended beam_reinforcement_models.json, and retrigger Phase L.2.1
so that all 18 detected beams appear in the Engineering Feature Model.

Recovery Data Sources (in priority order)
------------------------------------------
1. L.2 BeamReinforcementModel geometry block (span, width, depth).
2. V5 beam schedule (clear_span_mm, section).
3. V5 engineering objects (beam identifier annotations).
4. Default engineering heuristics (fallback).

Recovery Status
---------------
RECOVERED — geometry and placeholder bars successfully created.
FAILED    — insufficient data to reconstruct.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from geometry_registry import (
    GeometryRegistry,
    build_entry_from_l2_model,
    build_entry_recovered,
    build_failed_entry,
)


# ── placeholder bar templates ─────────────────────────────────────────────────

_BAR_COUNTER = [0]


def _next_bar_id(prefix: str = "BAR::L22") -> str:
    _BAR_COUNTER[0] += 1
    return f"{prefix}::{_BAR_COUNTER[0]:04d}"


def _make_placeholder_bar(
    beam_id: str,
    role: str,
    diameter_mm: float,
    quantity: int,
    label: str,
    extent: str = "FULL_SPAN",
    position_zone: str = "BOTTOM_ZONE",
) -> Dict[str, Any]:
    return {
        "bar_id": _next_bar_id(),
        "source_bar_id": None,
        "beam_id": beam_id,
        "semantic_role": role,
        "diameter_mm": diameter_mm,
        "quantity": quantity,
        "steel_grade": "Y",
        "bar_label": label,
        "position_zone": position_zone,
        "extent": extent,
        "continuity": "SINGLE_BEAM",
        "support_zone": None,
        "coverage_ratio": 1.0,
        "spacing_mm": None,
        "classification_evidence": "Phase L.2.2 geometry recovery — placeholder bar",
        "classification_confidence": "LOW",
        "source_pipeline_role": None,
        "is_corrected": False,
        "is_reference_anchored": False,
        "is_recovered": True,
        "recovery_stage": "L2_2_GEOMETRY_RECOVERY",
    }


def _make_stirrup_bar(beam_id: str, spacing_mm: float = 150.0) -> Dict[str, Any]:
    bar = _make_placeholder_bar(
        beam_id=beam_id,
        role="STIRRUP",
        diameter_mm=8.0,
        quantity=1,
        label="R8-150",
        extent="FULL_SPAN",
        position_zone="TRANSVERSE",
    )
    bar["spacing_mm"] = spacing_mm
    bar["position_zone"] = "TRANSVERSE"
    return bar


def _infer_section_from_label(label: str) -> Tuple[float, float]:
    """Parse '200x600' style annotation → (width, depth)."""
    import re
    m = re.search(r'(\d+)\s*[xX×]\s*(\d+)', label or "")
    if m:
        return float(m.group(1)), float(m.group(2))
    return 200.0, 600.0


# ── main engine ───────────────────────────────────────────────────────────────


class GeometryRecoveryEngine:
    """
    Orchestrates geometry recovery for beams missing from Phase L.2.1 output.

    Steps
    -----
    1. Load L.2 beam models.
    2. Load L.2.1 feature statistics to find which beams already have features.
    3. Identify gap beams (in L.2 but missing from L.2.1).
    4. For each gap beam, reconstruct EngineeringGeometry + placeholder bars.
    5. Write extended beam_reinforcement_models.json to L.2.2 output dir.
    6. Re-trigger Phase L.2.1 using the extended models.
    7. Return recovery summary.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._root = project_root or Path.cwd()
        v6_out = self._root / "data/output"
        v5_out = self._root.parent / "Version5/data/output"
        self._paths = {
            "l2_beam_models": v6_out / "PhaseL.2 - engineering_reinforcement_interpretation/beam_reinforcement_models.json",
            "l21_feature_stats": v6_out / "PhaseL.2.1 - engineering_feature_extraction/feature_statistics.json",
            "v5_beam_schedule": v5_out / "phase_i/i_15_beam_schedule/beam_schedule_results.json",
            "v5_eng_objects": v5_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
            "output_dir": v6_out / "PhaseL.2.2_geometry_recovery",
            "extended_models": v6_out / "PhaseL.2.2_geometry_recovery/extended_beam_reinforcement_models.json",
        }
        self._output_dir: Path = self._paths["output_dir"]
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ── loaders ──────────────────────────────────────────────────────────

    def _load(self, key: str) -> Any:
        path = self._paths.get(key)
        if not path or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _beam_ids_with_features(self) -> Set[str]:
        stats = self._load("l21_feature_stats")
        if stats and isinstance(stats, dict):
            return set(stats.get("beam_ids") or [])
        return set()

    def _beam_schedule_map(self) -> Dict[str, Dict[str, Any]]:
        """Return {beam_id: schedule_entry} from V5 beam schedule."""
        data = self._load("v5_beam_schedule")
        if not data or not isinstance(data, dict):
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        for r in data.get("results") or []:
            bid = r.get("beam_id") or r.get("beam_mark") or ""
            if bid:
                result[bid] = r
        return result

    def _object_beam_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return {beam_id: [engineering_objects]} from V5 objects."""
        data = self._load("v5_eng_objects")
        if not data or not isinstance(data, dict):
            return {}
        result: Dict[str, List[Dict[str, Any]]] = {}
        import re
        for obj in data.get("objects") or []:
            bid = obj.get("beam_id") or ""
            mark = (obj.get("object_data") or {}).get("mark") or ""
            for candidate in [bid] + re.findall(r'B\d+', mark):
                if candidate:
                    result.setdefault(candidate, []).append(obj)
        return result

    # ── recovery helpers ─────────────────────────────────────────────────

    def _recover_geometry_for_beam(
        self,
        beam_model: Dict[str, Any],
        schedule_map: Dict[str, Dict[str, Any]],
        object_data: Dict[str, List[Dict[str, Any]]],
    ) -> Tuple[Dict[str, Any], str]:
        """
        Attempt to reconstruct geometry for a gap beam.

        Returns (geometry_entry, status) where status is RECOVERED or FAILED.
        """
        beam_id = beam_model.get("beam_id", "UNKNOWN")
        sources: List[str] = []

        # ── 1. Try L.2 model geometry block ──────────────────────────────
        geo = beam_model.get("geometry") or {}
        width = float(geo.get("width_mm") or 0)
        depth = float(geo.get("depth_mm") or 0)
        span = float(geo.get("clear_span_mm") or geo.get("effective_span_mm") or 0)
        if width > 0 and depth > 0 and span > 0:
            sources.append("L2_MODEL_GEOMETRY")

        # ── 2. Supplement from V5 beam schedule ──────────────────────────
        sched = schedule_map.get(beam_id) or {}
        if sched:
            sources.append("V5_BEAM_SCHEDULE")
            sec = sched.get("beam_section") or {}
            if not width:
                width = float(sec.get("width") or sec.get("width_mm") or 200)
            if not depth:
                depth = float(sec.get("depth") or sec.get("depth_mm") or 600)
            if not span:
                span = float(sched.get("clear_span_mm") or sched.get("effective_span_mm") or 3000)

        # ── 3. Supplement from V5 engineering objects (beam identifier) ──
        objs = object_data.get(beam_id) or []
        beam_id_objs = [o for o in objs if o.get("object_type") == "BEAM_IDENTIFIER"]
        if beam_id_objs:
            sources.append("V5_ENGINEERING_OBJECTS")
            for o in beam_id_objs:
                label = (o.get("object_data") or {}).get("mark") or ""
                w, d = _infer_section_from_label(label)
                if not width and w:
                    width = w
                if not depth and d:
                    depth = d

        # ── 4. Fallback heuristics ────────────────────────────────────────
        if not width:
            width = 200.0
            sources.append("HEURISTIC_DEFAULT_WIDTH")
        if not depth:
            depth = 600.0
            sources.append("HEURISTIC_DEFAULT_DEPTH")
        if not span:
            # Use average span of recovered beams if still unknown
            span = 3000.0
            sources.append("HEURISTIC_DEFAULT_SPAN")

        if width > 0 and depth > 0 and span > 0:
            confidence = 0.50
            if "L2_MODEL_GEOMETRY" in sources:
                confidence += 0.20
            if "V5_BEAM_SCHEDULE" in sources:
                confidence += 0.15
            if "V5_ENGINEERING_OBJECTS" in sources:
                confidence += 0.07
            entry = build_entry_recovered(
                beam_id=beam_id,
                span_mm=span,
                width_mm=width,
                depth_mm=depth,
                recovery_sources=sources,
                confidence=min(confidence, 1.0),
                status="RECOVERED",
            )
            return entry, "RECOVERED"

        return build_failed_entry(beam_id, "Insufficient data to reconstruct geometry"), "FAILED"

    def _make_placeholder_bars_for_beam(
        self,
        beam_id: str,
        width_mm: float,
        depth_mm: float,
        span_mm: float,
        schedule_entry: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate minimal placeholder bars for a recovered beam.

        Creates 3 bars: BOTTOM_MAIN, TOP_MAIN, STIRRUP.
        These are observation-only entries with is_recovered=True.
        """
        # Determine appropriate diameters from section size
        if depth_mm >= 600:
            bot_dia, top_dia = 20.0, 16.0
        elif depth_mm >= 450:
            bot_dia, top_dia = 16.0, 12.0
        else:
            bot_dia, top_dia = 12.0, 10.0

        return {
            "bottom_main_bars": [
                _make_placeholder_bar(
                    beam_id=beam_id,
                    role="BOTTOM_MAIN",
                    diameter_mm=bot_dia,
                    quantity=2,
                    label=f"2Y{int(bot_dia)}",
                    extent="FULL_SPAN",
                    position_zone="BOTTOM_ZONE",
                )
            ],
            "top_main_bars": [
                _make_placeholder_bar(
                    beam_id=beam_id,
                    role="TOP_MAIN",
                    diameter_mm=top_dia,
                    quantity=2,
                    label=f"2Y{int(top_dia)}",
                    extent="FULL_SPAN",
                    position_zone="TOP_ZONE",
                )
            ],
            "stirrups": [_make_stirrup_bar(beam_id, spacing_mm=150.0)],
            "top_extra_bars": [],
            "bottom_extra_bars": [],
            "side_face_reinforcement": [],
            "spacer_bars": [],
            "chair_bars": [],
            "supplementary_bars": [],
        }

    # ── public run method ─────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Execute geometry recovery and return a structured summary."""
        ts = datetime.now(timezone.utc).isoformat()

        # ── 1. Load inputs ────────────────────────────────────────────────
        l2_data = self._load("l2_beam_models")
        if not l2_data or not isinstance(l2_data, dict):
            raise RuntimeError("Cannot load L.2 beam_reinforcement_models.json")

        all_models: List[Dict[str, Any]] = l2_data.get("models") or []
        all_beam_ids: List[str] = [m.get("beam_id", "") for m in all_models if m.get("beam_id")]

        feature_ids = self._beam_ids_with_features()
        gap_beam_ids: List[str] = [b for b in all_beam_ids if b not in feature_ids]

        schedule_map = self._beam_schedule_map()
        object_data = self._object_beam_data()

        # ── 2. Build geometry registry ────────────────────────────────────
        registry = GeometryRegistry()
        for model in all_models:
            bid = model.get("beam_id", "")
            if not bid:
                continue
            if bid in feature_ids:
                # Already covered — use original geometry
                registry.add(build_entry_from_l2_model(model))
            # Gap beams handled below

        recovery_results: List[Dict[str, Any]] = []
        recovered_models: List[Dict[str, Any]] = []

        for model in all_models:
            bid = model.get("beam_id", "")
            if not bid or bid not in gap_beam_ids:
                continue

            geo_entry, status = self._recover_geometry_for_beam(model, schedule_map, object_data)
            registry.add(geo_entry)

            if status == "RECOVERED":
                geo = geo_entry
                w = geo["bounding_box"]["width_mm"]
                d = geo["bounding_box"]["depth_mm"]
                s = geo["beam_axis"]["length_mm"]
                placeholder_bars = self._make_placeholder_bars_for_beam(
                    bid, w, d, s, schedule_map.get(bid) or {}
                )
                recovered_model = dict(model)
                recovered_model.update(placeholder_bars)
                recovered_model["bar_count_by_role"] = {
                    "BOTTOM_MAIN": 1,
                    "TOP_MAIN": 1,
                    "STIRRUP": 1,
                    "TOP_EXTRA": 0,
                    "BOTTOM_EXTRA": 0,
                    "SIDE_FACE_REINFORCEMENT": 0,
                    "SPACER_BAR": 0,
                    "CHAIR_BAR": 0,
                    "SUPPLEMENTARY_BAR": 0,
                }
                recovered_model["recovery_stage"] = "L2_2_GEOMETRY_RECOVERY"
                recovered_model["geometry_source"] = "RECOVERED"
                recovered_models.append(recovered_model)

                recovery_results.append({
                    "beam_id": bid,
                    "status": "RECOVERED",
                    "geometry_id": geo_entry.get("geometry_id"),
                    "confidence": geo_entry.get("confidence"),
                    "recovery_sources": geo_entry.get("recovery_sources", []),
                    "placeholder_bars": 3,
                })
            else:
                recovery_results.append({
                    "beam_id": bid,
                    "status": "FAILED",
                    "reason": geo_entry.get("failure_reason", "Unknown"),
                })

        # ── 3. Build extended beam models (original + recovered) ──────────
        original_models = [m for m in all_models if m.get("beam_id") in feature_ids]
        extended_models = original_models + recovered_models

        extended_payload = {
            "model_count": len(extended_models),
            "source": "PhaseL.2.2_geometry_recovery",
            "generation_timestamp": ts,
            "original_count": len(original_models),
            "recovered_count": len(recovered_models),
            "models": extended_models,
        }
        self._paths["extended_models"].write_text(
            json.dumps(extended_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        recovered_count = sum(1 for r in recovery_results if r["status"] == "RECOVERED")
        failed_count = sum(1 for r in recovery_results if r["status"] == "FAILED")

        return {
            "timestamp": ts,
            "all_beam_ids": all_beam_ids,
            "feature_beam_ids": sorted(feature_ids),
            "gap_beam_ids": gap_beam_ids,
            "recovery_results": recovery_results,
            "recovered_count": recovered_count,
            "failed_count": failed_count,
            "geometry_registry": registry,
            "extended_models_path": str(self._paths["extended_models"]),
            "output_dir": str(self._output_dir),
        }
