"""
beam_count_monitor.py — Reads beam counts from each stage's primary output.
MODEL_VERSION: 7.2.0
"""

from __future__ import annotations
import json
import pathlib
from typing import Dict, List, Optional, Tuple

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
V7        = WORKSPACE / "Version7"

# Primary artefact that carries beam IDs for each stage
STAGE_PRIMARY_ARTEFACT: Dict[str, Tuple[str, str]] = {
    "VROOT1": ("data/output/PhaseVROOT.1_dynamic_pipeline_initialization",
               "beam_registry.json"),
    "L2":     ("data/output/PhaseL.2 - engineering_reinforcement_interpretation",
               "beam_reinforcement_models.json"),
    "SI0":    ("data/output/PhaseSI.0_stirrup_recovery",
               "stirrup_full_report.json"),
    "SI1":    ("data/output/PhaseSI.1_stirrup_improvement",
               "stirrup_improved_report.json"),
    "L22":    ("data/output/PhaseL.2.2_geometry_recovery",
               "geometry_recovery_report.json"),
    "L21":    ("data/output/PhaseL.2.1 - engineering_feature_extraction",
               "feature_collection.json"),
    "L3":     ("data/output/PhaseL.3_beam_pattern_recognition",
               "pattern_recognition_report.json"),
    "VB1":    ("data/output/Production_Output",
               "production_report.json"),
}


def _load_json(path: pathlib.Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return None


def _extract_ids(data: dict) -> List[str]:
    """Try several known schema patterns to extract beam IDs."""
    for key in ("models", "beams", "objects", "results", "bars",
                "sections", "beam_schedule", "patterns", "features"):
        val = data.get(key)
        if isinstance(val, dict):
            return sorted(val.keys())
        if isinstance(val, list):
            ids = []
            for item in val:
                if isinstance(item, dict):
                    bid = (item.get("beam_mark") or item.get("beam_id")
                           or item.get("id") or "")
                    if bid:
                        ids.append(str(bid))
            if ids:
                return sorted(set(ids))
    # Scalar count
    cnt = data.get("beam_count") or data.get("model_count") or data.get("total_beams")
    if cnt:
        return [f"BEAM_{i}" for i in range(int(cnt))]
    return []


class BeamCountMonitor:

    def read_stage_beam_count(self, stage_id: str) -> Tuple[int, List[str]]:
        if stage_id not in STAGE_PRIMARY_ARTEFACT:
            return 0, []
        rel_dir, fname = STAGE_PRIMARY_ARTEFACT[stage_id]
        path = V7 / rel_dir / fname
        if not path.exists():
            # Try any JSON in the directory
            d = V7 / rel_dir
            if d.exists():
                jsons = sorted(d.glob("*.json"))
                for j in jsons:
                    data = _load_json(j)
                    if data:
                        ids = _extract_ids(data)
                        if ids:
                            return len(ids), ids
            return 0, []
        data = _load_json(path)
        if not data:
            return 0, []
        ids = _extract_ids(data)
        return len(ids), ids

    def build_propagation_table(
        self,
        stage_results_order: List[str],
    ) -> List[dict]:
        table  = []
        prev_ids: Optional[List[str]] = None

        for stage_id in stage_results_order:
            cnt, ids = self.read_stage_beam_count(stage_id)
            lost  = sorted(set(prev_ids or []) - set(ids)) if prev_ids else []
            added = sorted(set(ids) - set(prev_ids or [])) if prev_ids else []
            delta = cnt - (len(prev_ids) if prev_ids is not None else cnt)

            table.append({
                "stage_id":    stage_id,
                "beam_count":  cnt,
                "beam_ids":    ids,
                "delta":       delta if prev_ids is not None else 0,
                "lost_beams":  lost,
                "added_beams": added,
            })
            prev_ids = ids or prev_ids

        return table
