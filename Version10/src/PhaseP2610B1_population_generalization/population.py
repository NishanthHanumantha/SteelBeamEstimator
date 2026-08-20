"""Fourth-set population discovery. Reuses P2.6.10-A title localization. No R.1."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from PhaseP2610A_beam_region_crop_audit.dataset import find_reinforcement_dxf_for_set
from PhaseP2610A_beam_region_crop_audit.title_localizer import best_marks_by_beam, collect_beam_titles

from .config import DRAWING_SET_KEY


def discover_fourth_set_population(version10_root: Path, msp: Any) -> Dict[str, Any]:
    dxf = find_reinforcement_dxf_for_set(Path(version10_root), DRAWING_SET_KEY)
    titles = collect_beam_titles(msp)
    marks = best_marks_by_beam(msp, titles)
    counts = Counter(str(t.get("beam_id") or "") for t in titles)
    collapsed = [
        {
            "beam_id": bid,
            "title_hits": n,
            "chosen_score": (marks.get(bid) or {}).get("score"),
            "reason": "DUPLICATE_TITLE_COLLAPSED_TO_BEST_MARK",
        }
        for bid, n in sorted(counts.items())
        if n > 1 and bid in marks
    ]
    ordered = sorted(marks.items(), key=lambda kv: (float(kv[1].get("y") or 0.0), float(kv[1].get("x") or 0.0)))
    return {
        "set_key": DRAWING_SET_KEY,
        "source_dxf": str(dxf),
        "title_hits": len(titles),
        "unique_beam_ids": len(marks),
        "collapsed_duplicates": collapsed,
        "titles": titles,
        "marks": {bid: mark for bid, mark in ordered},
        "beam_ids": [bid for bid, _ in ordered],
        "discovery_method": "collect_beam_titles+best_marks_by_beam",
        "annotation_association_dependency": False,
    }


__all__ = ["discover_fourth_set_population"]
