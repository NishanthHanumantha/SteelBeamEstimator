"""
Regression — ensure P2.4 does not mutate prior artefacts.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_fingerprints(paths: Dict[str, Path]) -> Dict[str, Any]:
    out = {}
    for key, path in paths.items():
        if path and path.exists() and path.is_file():
            out[key] = {
                "path": str(path),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        else:
            out[key] = {"path": str(path) if path else None, "missing": True}
    return out


def compare_fingerprints(
    before: Dict[str, Any], after: Dict[str, Any]
) -> Dict[str, Any]:
    changed: List[str] = []
    for key in sorted(set(before) | set(after)):
        b = before.get(key) or {}
        a = after.get(key) or {}
        if b.get("sha256") != a.get("sha256") or b.get("size") != a.get("size"):
            if not (b.get("missing") and a.get("missing")):
                changed.append(key)
    return {
        "unchanged": len(changed) == 0,
        "changed_keys": changed,
        "before": before,
        "after": after,
    }


def load_prior_regression_hashes(
    p22: Optional[Path], p23: Optional[Path], p231: Optional[Path]
) -> Dict[str, Any]:
    import json

    out = {}
    for label, path in (("p22", p22), ("p23", p23), ("p231", p231)):
        if path and path.exists():
            out[label] = {
                "path": str(path),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        else:
            out[label] = {"path": str(path) if path else None, "missing": True}
    return out
