"""Discover C.3 + C.5 Vision observations. Deduplicate generically. No beam-ID tables."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    C3_SIX_BEAM_NAME,
    C5_MANIFEST_NAME,
    C5_SAMPLE_NAME,
    P2610C3_OUTPUT_DIRNAME,
    P2610C5_OUTPUT_DIRNAME,
)


def is_live_vision_observation(record: Dict[str, Any], parsed: Dict[str, Any]) -> bool:
    if not parsed:
        return False
    if record.get("called") is False:
        return False
    if parsed.get("usable") is False and not (parsed.get("groups") or parsed.get("reinforcement_groups") or parsed.get("stirrups")):
        return False
    return True


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _c3_observations(v10: Path) -> List[Dict[str, Any]]:
    root = Path(v10) / "data" / "output" / P2610C3_OUTPUT_DIRNAME
    path = root / C3_SIX_BEAM_NAME
    payload = _load(path)
    out = []
    for row in (payload or {}).get("rows") or []:
        claude = row.get("claude") or {}
        parsed = claude.get("parsed") or {}
        if not is_live_vision_observation(claude, parsed):
            continue
        cmp = row.get("comparison") or {}
        det = list(cmp.get("deterministic") or [])
        if not det:
            packed = _load(root / "beams" / str(row.get("beam_id")) / "comparison.json") or {}
            det = list(packed.get("deterministic") or [])
        out.append(
            {
                "beam_id": str(row.get("beam_id")),
                "source_phase": "P2.6.10-C.3",
                "source_path": str(path),
                "schema_version": parsed.get("schema_version"),
                "usable": bool(parsed.get("usable")),
                "parsed": parsed,
                "detected_groups": det,
                "expected_groups": list(cmp.get("p269_expected") or []),
                "set_key": row.get("set_key"),
            }
        )
    return out


def _c5_observations(v10: Path) -> List[Dict[str, Any]]:
    root = Path(v10) / "data" / "output" / P2610C5_OUTPUT_DIRNAME
    sample = _load(root / C5_SAMPLE_NAME) or {}
    manifest = _load(root / C5_MANIFEST_NAME)
    by_manifest: Dict[str, Dict[str, Any]] = {}
    if isinstance(manifest, list):
        for row in manifest:
            if isinstance(row, dict) and row.get("beam_id"):
                by_manifest[str(row.get("beam_id"))] = row
    ids: List[str] = []
    for bid in sample.get("ids") or sample.get("selected_ids") or []:
        if str(bid) not in ids:
            ids.append(str(bid))
    review = root / "review"
    if review.exists():
        for child in sorted(review.iterdir()):
            if child.is_dir() and (child / "vision_result.json").exists() and child.name not in ids:
                ids.append(child.name)
    out = []
    for bid in ids:
        vis = _load(review / bid / "vision_result.json") or {}
        parsed = vis.get("parsed") or {}
        if not is_live_vision_observation(vis, parsed):
            continue
        packed = _load(review / bid / "deterministic_result.json") or {}
        man = by_manifest.get(bid) or {}
        det = list(man.get("detected_groups") or packed.get("detected_groups") or [])
        out.append(
            {
                "beam_id": bid,
                "source_phase": "P2.6.10-C.5",
                "source_path": str(review / bid / "vision_result.json"),
                "schema_version": parsed.get("schema_version"),
                "usable": bool(parsed.get("usable")),
                "parsed": parsed,
                "detected_groups": det,
                "expected_groups": list(man.get("expected_groups") or packed.get("expected_groups") or []),
                "set_key": man.get("set_key") or "Fourth",
            }
        )
    return out


_PHASE_RANK = {"P2.6.10-C.5": 2, "P2.6.10-C.3": 1}


def dedupe_observations(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_id.setdefault(str(row.get("beam_id")), []).append(row)
    chosen = []
    for bid, items in sorted(by_id.items(), key=lambda kv: kv[0]):
        if len(items) == 1:
            chosen.append(items[0])
            continue
        valid = [x for x in items if x.get("usable")]
        pool = valid or items
        pool_sorted = sorted(
            pool,
            key=lambda x: (-_PHASE_RANK.get(str(x.get("source_phase")), 0), str(x.get("source_phase"))),
        )
        winner = dict(pool_sorted[0])
        winner["dedupe"] = {
            "sources": [x.get("source_phase") for x in items],
            "preferred": winner.get("source_phase"),
            "rule": "latest_valid_usable_then_phase_rank",
        }
        chosen.append(winner)
    return chosen


def discover_benchmark_population(v10: Path) -> Dict[str, Any]:
    c3 = _c3_observations(v10)
    c5 = _c5_observations(v10)
    merged = dedupe_observations(c3 + c5)
    return {
        "ok": bool(merged),
        "c3_count": len(c3),
        "c5_count": len(c5),
        "discovered_count": len(c3) + len(c5),
        "deduplicated_count": len(merged),
        "records": merged,
        "beam_ids": [r.get("beam_id") for r in merged],
    }


__all__ = ["dedupe_observations", "discover_benchmark_population", "is_live_vision_observation"]
