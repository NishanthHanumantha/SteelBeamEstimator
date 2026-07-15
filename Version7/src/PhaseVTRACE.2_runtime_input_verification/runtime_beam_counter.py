"""
runtime_beam_counter.py — Extracts beam counts and IDs from every loaded JSON.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
import json
import pathlib
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def count_beams_in_file(path: pathlib.Path) -> dict:
    """Return detailed beam count breakdown for any known artefact format."""
    if not path.exists():
        return {"status": "MISSING", "beam_count": 0, "beam_ids": [], "source_key": "none"}

    try:
        data = json.loads(path.read_text("utf-8"))
    except Exception as e:
        return {"status": "PARSE_ERROR", "beam_count": 0, "beam_ids": [], "error": str(e)}

    return _extract(data, str(path))


def _extract(data: dict, label: str) -> dict:
    for key in ("objects", "results", "beams", "models", "bars", "geometries"):
        val = data.get(key)
        if isinstance(val, list) and val:
            ids = _ids_from_list(val)
            return {
                "status":     "OK",
                "source_key": key,
                "beam_count": len(ids) if ids else len(val),
                "beam_ids":   sorted(set(ids)),
                "raw_len":    len(val),
            }
        if isinstance(val, dict):
            return {
                "status":     "OK",
                "source_key": key,
                "beam_count": len(val),
                "beam_ids":   sorted(val.keys()),
            }
    # Scalar count
    for key in ("beam_count", "object_count", "model_count", "determination_count", "bar_count"):
        if key in data:
            return {
                "status":     "OK",
                "source_key": key,
                "beam_count": int(data[key]),
                "beam_ids":   [],
                "note":       "beam_ids not enumerable from this format",
            }
    return {"status": "UNKNOWN_FORMAT", "beam_count": 0, "beam_ids": []}


def _ids_from_list(items: list) -> List[str]:
    ids = []
    for item in items:
        if isinstance(item, dict):
            bid = (item.get("beam_mark") or item.get("beam_id")
                   or item.get("id") or "")
            if bid:
                ids.append(str(bid))
    return ids


class RuntimeBeamCounter:
    """
    Inspects the collect() snapshot to answer:
      How many beams does _discover_beams() return with live adapter data?
    """

    def count_from_snapshot(self, snapshot: dict) -> dict:
        """Simulate _discover_beams() logic on the live snapshot."""
        beams = set()
        source = "EMPTY"

        # Replicate BeamContextBuilder._discover_beams()
        bs = snapshot.get("beam_schedule") or {}
        results = bs.get("results") or []
        for r in results:
            bm = str(r.get("beam_mark") or r.get("beam_id") or "")
            if bm:
                beams.add(bm)
        if beams:
            source = "beam_schedule.results"

        ro = snapshot.get("reinforcement_objects") or {}
        bars = ro.get("bars") or []
        for b in bars:
            bm = str(b.get("beam_id") or b.get("beam_mark") or "")
            if bm:
                beams.add(bm)
        if bars and not beams:
            source = "reinforcement_objects.bars"

        if not beams:
            beams = {"B1","B2","B3","B4","B5","B6","B7","B8","B9","B10",
                     "B11","B12","B13","B14","B15","B16","B17","B18"}
            source = "FALLBACK_HARDCODED_18"

        return {
            "beam_ids":           sorted(beams),
            "beam_count":         len(beams),
            "source":             source,
            "fallback_triggered": source == "FALLBACK_HARDCODED_18",
            "note": (
                "CRITICAL: fallback to hardcoded B1-B18 was triggered — "
                "adapter data was not read or was empty."
                if source == "FALLBACK_HARDCODED_18"
                else f"Beam IDs sourced from '{source}'."
            ),
        }
