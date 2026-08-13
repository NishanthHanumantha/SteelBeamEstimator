"""Load the FROZEN P2.5.4 41-candidate set. Do not rebuild the benchmark."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import FROZEN_BENCHMARK_COUNT, P251_OUTPUT, P254_OUTPUT


def p254_root(version10_root: Path) -> Path:
    return Path(version10_root) / "data" / "output" / P254_OUTPUT


def load_frozen_benchmark(version10_root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    root = p254_root(version10_root)
    manifest_path = root / "benchmark" / "benchmark_manifest.json"
    gt_path = root / "benchmark" / "ground_truth_reference.json"
    if not manifest_path.exists() or not gt_path.exists():
        raise FileNotFoundError(f"Frozen P2.5.4 benchmark missing under {root}")
    candidates = json.loads(manifest_path.read_text(encoding="utf-8"))
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    if len(candidates) != FROZEN_BENCHMARK_COUNT:
        raise ValueError(
            f"Frozen P2.5.4 benchmark size is {len(candidates)}, expected {FROZEN_BENCHMARK_COUNT}"
        )
    return candidates, gt


def load_frozen_p251_index(version10_root: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    path = Path(version10_root) / "data" / "output" / P251_OUTPUT / "quantity_intent_matrix.json"
    if not path.exists():
        raise FileNotFoundError(f"Frozen P2.5.1 matrix missing: {path}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {(r.get("beam_id"), r.get("annotation_id")): r for r in rows}


def p254_candidate_dir(version10_root: Path, candidate_id: str) -> Path:
    return p254_root(version10_root) / "candidates" / candidate_id.replace("::", "__")


def load_p254_vision_replay(
    version10_root: Path, candidate_id: str
) -> Dict[str, Any]:
    folder = p254_candidate_dir(version10_root, candidate_id)
    def _load(name: str) -> Optional[Dict[str, Any]]:
        p = folder / name
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    validation_wrap = _load("validation.json") or {}
    claude = _load("claude_response.json") or {}
    evaluation_wrap = _load("evaluation.json") or {}
    input_manifest = _load("input_manifest.json") or {}
    validation = validation_wrap.get("validation") or {
        "valid": False,
        "errors": ["MISSING_P254_VALIDATION"],
        "warnings": [],
    }
    return {
        "api_ok": bool(claude.get("success")),
        "claude_call": claude,
        "parsed": validation_wrap.get("parsed"),
        "validation": validation,
        "validated_interpretation": validation.get("validated_interpretation"),
        "evaluation": evaluation_wrap.get("evaluation"),
        "evidence_fingerprint": input_manifest.get("evidence_fingerprint")
        or claude.get("evidence_fingerprint"),
        "prompt_fingerprint": input_manifest.get("prompt_fingerprint")
        or claude.get("prompt_fingerprint"),
        "usage": claude.get("usage") or {},
        "model": claude.get("model"),
        "temperature": claude.get("temperature"),
    }


__all__ = [
    "load_frozen_benchmark",
    "load_frozen_p251_index",
    "load_p254_vision_replay",
    "p254_candidate_dir",
    "p254_root",
]
