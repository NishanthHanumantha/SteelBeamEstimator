"""
runtime_filter_detector.py — Traces the beam count at every L.2 processing step.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
import json
import pathlib
from typing import Dict, List, Optional

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")


class RuntimeFilterDetector:
    """
    Compares beam counts at each documented internal L.2 processing step:
      1. Input adapter (pre-load)
      2. _discover_beams() output
      3. BeamContextBuilder output (geometries)
      4. L.2 beam_reinforcement_models.json (actual output)
      5. L.2 interpretation_statistics.json (reported count)
    """

    def __init__(self, project_root: pathlib.Path, l2_output_dir: pathlib.Path):
        self._root     = project_root
        self._l2_out   = l2_output_dir

    def analyze(
        self,
        adapter_beam_ids: List[str],
        discover_beams_result: List[str],
    ) -> dict:
        v5  = self._root.parent / "Version5/data/output"
        stages = []

        # Stage 0: V5 adapter (input)
        bs_path = v5 / "phase_i/i_15_beam_schedule/beam_schedule_results.json"
        stages.append(self._stage(
            label         = "0_adapter_input",
            description   = "V5 beam_schedule adapter (what L.2 reads)",
            beam_ids      = adapter_beam_ids,
            source_file   = str(bs_path),
            note          = "Written by V.ROOT.1 engineering_object_initializer.py",
        ))

        # Stage 1: _discover_beams() simulation result
        stages.append(self._stage(
            label         = "1_discover_beams_output",
            description   = "BeamContextBuilder._discover_beams() result (simulated)",
            beam_ids      = discover_beams_result,
            source_file   = "beam_context_builder.py",
            note          = ("Beam IDs extracted from beam_schedule.results[].beam_mark — "
                             "all 65 IDs present.") if len(discover_beams_result) == 65
                             else f"Only {len(discover_beams_result)} IDs extracted. "
                                  "Possible format mismatch.",
        ))

        # Stage 2: L.2 current output artefact
        bm_path = self._l2_out / "beam_reinforcement_models.json"
        l2_ids, l2_note = self._read_l2_output(bm_path)
        stages.append(self._stage(
            label         = "2_l2_output_artefact",
            description   = "L.2 beam_reinforcement_models.json (existing artefact)",
            beam_ids      = l2_ids,
            source_file   = str(bm_path),
            note          = l2_note,
        ))

        # Stage 3: L.2 statistics
        stats_path = self._l2_out / "interpretation_statistics.json"
        stats_ids, stats_note = self._read_stats(stats_path)
        stages.append(self._stage(
            label         = "3_l2_statistics",
            description   = "L.2 interpretation_statistics.json (reported beam count)",
            beam_ids      = stats_ids,
            source_file   = str(stats_path),
            note          = stats_note,
        ))

        # Identify first filter stage
        prev_count = len(adapter_beam_ids)
        first_drop  = None
        first_delta = 0
        for s in stages:
            cnt = s["beam_count"]
            if cnt < prev_count and first_drop is None:
                first_drop  = s["label"]
                first_delta = cnt - prev_count
            prev_count = cnt

        return {
            "stages":             stages,
            "first_drop_stage":   first_drop,
            "first_drop_delta":   first_delta,
            "input_count":        len(adapter_beam_ids),
            "output_count":       len(l2_ids),
            "net_loss":           len(adapter_beam_ids) - len(l2_ids),
            "lost_ids":           sorted(set(adapter_beam_ids) - set(l2_ids)),
        }

    def _stage(self, label, description, beam_ids, source_file, note) -> dict:
        return {
            "label":       label,
            "description": description,
            "beam_count":  len(beam_ids),
            "beam_ids":    sorted(beam_ids),
            "source_file": source_file,
            "note":        note,
        }

    def _read_l2_output(self, path: pathlib.Path):
        if not path.exists():
            return [], "L.2 output artefact MISSING"
        try:
            d    = json.loads(path.read_text("utf-8"))
            models = d.get("models", {})
            ids  = sorted(models.keys()) if isinstance(models, dict) else []
            cnt  = d.get("model_count", len(ids))
            note = (f"Artefact contains {cnt} beams. "
                    f"model_version={d.get('model_version','?')}. "
                    f"run_timestamp={d.get('run_timestamp','?')}")
            return ids, note
        except Exception as e:
            return [], f"Parse error: {e}"

    def _read_stats(self, path: pathlib.Path):
        if not path.exists():
            return [], "Statistics file MISSING"
        try:
            d   = json.loads(path.read_text("utf-8"))
            cnt = d.get("total_beams", 0)
            return [f"BEAM_{i}" for i in range(cnt)], f"Reported total_beams={cnt}"
        except Exception as e:
            return [], f"Parse error: {e}"
