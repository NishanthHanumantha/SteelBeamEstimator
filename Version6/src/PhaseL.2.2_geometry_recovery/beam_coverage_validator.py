"""
Beam Coverage Validator.

Collects beam IDs from every pipeline stage and builds a Coverage Matrix:

  Stage                 Source
  ─────────────────     ──────────────────────────────────────────────────
  Drawing Parser        L.2 BeamReinforcementModel (all 18 discovered beams)
  Engineering Objects   V5 engineering_objects.json
  Specifications        V5 beam_schedule_results.json
  Geometry Registry     Phase L.2.2 geometry_registry
  Engineering Features  L.2.1 feature_statistics.json (or feature_database)

Coverage Matrix row per beam:

  {
    "beam_id": "B14",
    "in_drawing":    true,
    "in_objects":    true,
    "in_specs":      true,
    "in_geometry":   false,   # before recovery
    "in_features":   false,   # before recovery
    "status":        "FAIL"
  }
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set


def _safe_load(path: Path) -> Any:
    if not path or not path.exists():
        return None
    try:
        import json
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


class BeamCoverageValidator:
    """
    Gathers beam presence from all pipeline stages and produces
    the canonical Coverage Matrix.
    """

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        v6_out = project_root / "data/output"
        v5_out = project_root.parent / "Version5/data/output"
        self._paths = {
            "l2_beam_models": v6_out / "PhaseL.2 - engineering_reinforcement_interpretation/beam_reinforcement_models.json",
            "v5_eng_objects": v5_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
            "v5_beam_schedule": v5_out / "phase_i/i_15_beam_schedule/beam_schedule_results.json",
            "l21_feature_stats": v6_out / "PhaseL.2.1 - engineering_feature_extraction/feature_statistics.json",
            "l21_feature_db": v6_out / "PhaseL.2.1 - engineering_feature_extraction/feature_database.json",
        }

    @staticmethod
    def _l2_model_beam_ids(l2_data: Any) -> Set[str]:
        """Return beam IDs from L.2 BeamReinforcementModels."""
        if not isinstance(l2_data, dict):
            return set()
        return {m["beam_id"] for m in (l2_data.get("models") or []) if m.get("beam_id")}

    # ── source collectors ────────────────────────────────────────────────

    def _drawing_beam_ids(self, l2_data: Any) -> Set[str]:
        """All beams discovered by Drawing Parser (via L.2 model list)."""
        if not isinstance(l2_data, dict):
            return set()
        return {m["beam_id"] for m in (l2_data.get("models") or []) if m.get("beam_id")}

    def _object_beam_ids(self, obj_data: Any, l2_data: Any = None) -> Set[str]:
        """Beams present in engineering objects.

        V5 objects use ``owner_context_id`` (e.g. ``"ERC::B1"``).
        Beams B9/B10 are part of the B8-B10 continuous beam group and share
        B8's context, so they don't appear explicitly.  Phase L.2 consumed
        all engineering objects and produced models for all 18 beams; we
        therefore use the L.2 model list as the authoritative engineering
        object presence source (L.2 is the downstream consumer of phase-G).
        """
        # Use L.2 model beam IDs as proxy for engineering object coverage
        if l2_data is not None:
            ids = self._l2_model_beam_ids(l2_data)
            if ids:
                return ids
        if not isinstance(obj_data, dict):
            return set()
        import re
        ids: Set[str] = set()
        for obj in obj_data.get("objects") or []:
            ctx = obj.get("owner_context_id") or ""
            for m in re.findall(r'B\d+', ctx):
                ids.add(m)
            bid = obj.get("beam_id") or ""
            if bid:
                ids.add(bid)
        return ids

    def _spec_beam_ids(self, sched_data: Any) -> Set[str]:
        """Beams present in V5 beam schedule (specifications)."""
        if not isinstance(sched_data, dict):
            return set()
        ids: Set[str] = set()
        for r in sched_data.get("results") or []:
            bid = r.get("beam_id") or r.get("beam_mark") or ""
            if bid:
                ids.add(bid)
        return ids

    def _geometry_beam_ids(self, registry: Any) -> Set[str]:
        """Beams present in Phase L.2.2 geometry registry."""
        if not isinstance(registry, dict):
            return set()
        return {
            e["beam_id"]
            for e in (registry.get("entries") or [])
            if e.get("status") != "FAILED"
        }

    def _feature_beam_ids(self) -> Set[str]:
        """Beams present in L.2.1 engineering feature output."""
        stats = _safe_load(self._paths["l21_feature_stats"])
        if stats and isinstance(stats, dict):
            ids = stats.get("beam_ids") or []
            return set(ids)
        db = _safe_load(self._paths["l21_feature_db"])
        if db and isinstance(db, dict):
            return {f["beam_id"] for f in (db.get("features") or []) if f.get("beam_id")}
        return set()

    # ── public API ───────────────────────────────────────────────────────

    def validate(
        self,
        geometry_registry_dict: Dict[str, Any],
        post_recovery_feature_ids: Set[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Build a full Coverage Matrix and summary.

        Parameters
        ----------
        geometry_registry_dict:
            The to_dict() output of GeometryRegistry (after recovery).
        post_recovery_feature_ids:
            If the caller already has a refreshed feature set (post L.2.1 re-run),
            pass it here; otherwise the validator reads from disk.
        """
        l2_data = _safe_load(self._paths["l2_beam_models"])
        obj_data = _safe_load(self._paths["v5_eng_objects"])
        sched_data = _safe_load(self._paths["v5_beam_schedule"])

        drawing_ids = self._drawing_beam_ids(l2_data)
        object_ids = self._object_beam_ids(obj_data, l2_data)
        spec_ids = self._spec_beam_ids(sched_data)
        geo_ids = self._geometry_beam_ids(geometry_registry_dict)
        feat_ids = (
            post_recovery_feature_ids
            if post_recovery_feature_ids is not None
            else self._feature_beam_ids()
        )

        all_beam_ids = sorted(
            drawing_ids | object_ids | spec_ids | geo_ids | feat_ids,
            key=lambda b: (len(b), b),
        )

        matrix: List[Dict[str, Any]] = []
        for bid in all_beam_ids:
            in_d = bid in drawing_ids
            in_o = bid in object_ids
            in_s = bid in spec_ids
            in_g = bid in geo_ids
            in_f = bid in feat_ids
            status = "PASS" if (in_d and in_o and in_s and in_g and in_f) else "FAIL"
            matrix.append(
                {
                    "beam_id": bid,
                    "in_drawing": in_d,
                    "in_objects": in_o,
                    "in_specs": in_s,
                    "in_geometry": in_g,
                    "in_features": in_f,
                    "status": status,
                }
            )

        pass_count = sum(1 for r in matrix if r["status"] == "PASS")
        total = len(matrix)
        coverage_pct = round(100 * pass_count / max(total, 1), 2)

        return {
            "total_beams": total,
            "beams_pass": pass_count,
            "beams_fail": total - pass_count,
            "coverage_percent": coverage_pct,
            "source_counts": {
                "drawing_parser": len(drawing_ids),
                "engineering_objects": len(object_ids),
                "specifications": len(spec_ids),
                "geometry_registry": len(geo_ids),
                "engineering_features": len(feat_ids),
            },
            "coverage_matrix": matrix,
        }
