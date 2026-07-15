"""
runtime_adapter_verifier.py — Verifies V.ROOT.1 adapter files contain 65 beams
and identifies the exact source state before L.2 runs.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
import json
import pathlib
from typing import Dict, List, Optional, Tuple

WORKSPACE       = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")
EXPECTED_BEAMS  = 65
EXPECTED_IDS    = sorted([
    "B1","B2","B3","B6","B7","B8","B9","B10","B11","B12","B13","B14","B14A",
    "B15","B16","B17","B18","B19","B20","B20A","B21","B22","B23","B25","B26",
    "B27","B28","B29","B29A","B3","B30","B31","B31A","B32","B33","B34","B35",
    "B35A","B36","B38","B39","B39A","B40","B41","B42","B43","B45","B46","B47",
    "B48","B48A","B49","B50","B51","B52","B53","B54","B55","B56","B57","B58",
    "B59","B60","B61","B63","BR1",
])


class RuntimeAdapterVerifier:
    """Inspects each V5 adapter file produced by V.ROOT.1."""

    ADAPTER_KEYS = [
        "v5_engineering_objects",
        "v5_reinforcement_objects",
        "v5_beam_schedule",
        "v5_beam_geometry",
    ]

    def verify(self, files: Dict) -> List[dict]:
        results = []
        for key in self.ADAPTER_KEYS:
            rf = files.get(key)
            if rf is None:
                results.append({"key": key, "status": "MISSING", "beam_count": 0, "note": "Not in scan"})
                continue
            actual_count = rf.beam_count
            actual_ids   = rf.beam_ids if rf.beam_ids else []
            match_count  = actual_count == EXPECTED_BEAMS
            missing_ids  = sorted(set(EXPECTED_IDS) - set(actual_ids)) if actual_ids else ["IDs not enumerable"]
            unexpected   = sorted(set(actual_ids) - set(EXPECTED_IDS)) if actual_ids else []

            results.append({
                "key":              key,
                "absolute_path":    rf.absolute_path,
                "exists":           rf.exists,
                "beam_count":       actual_count,
                "expected_count":   EXPECTED_BEAMS,
                "count_match":      match_count,
                "benchmark_id":     rf.benchmark_id,
                "model_version":    rf.model_version,
                "mtime_iso":        rf.mtime_iso,
                "missing_ids":      missing_ids,
                "unexpected_ids":   unexpected,
                "status":           "PASS" if match_count and rf.exists else "FAIL",
                "note": (
                    f"Adapter contains {actual_count}/{EXPECTED_BEAMS} beams."
                    if match_count
                    else f"Adapter contains {actual_count} beams — expected {EXPECTED_BEAMS}."
                ),
            })
        return results
