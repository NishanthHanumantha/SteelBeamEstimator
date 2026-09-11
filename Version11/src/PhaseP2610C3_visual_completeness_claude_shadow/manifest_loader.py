"""Read-only C.1+C.2 selection manifest loading. No reselection. No rerender."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import P2610C1C2_OUTPUT_DIRNAME, SELECTION_MANIFEST_NAME
from .evidence_model import beam_from_manifest_row


def sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def selection_manifest_path(v10: Path) -> Path:
    return Path(v10) / "data" / "output" / P2610C1C2_OUTPUT_DIRNAME / SELECTION_MANIFEST_NAME


def load_selection_manifest(v10: Path) -> List[Dict[str, Any]]:
    path = selection_manifest_path(v10)
    if not path.exists():
        raise FileNotFoundError(f"C.1+C.2 selection manifest missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("selection_manifest.json must be a non-empty list")
    return payload


def verify_selected_image(side: Dict[str, Any]) -> Dict[str, Any]:
    path_s = side.get("selected_path")
    expected = side.get("selected_sha256")
    p = Path(path_s) if path_s else None
    exists = bool(p and p.exists() and p.stat().st_size > 200)
    actual = sha256_file(p) if exists else None
    mismatch = bool(exists and expected and actual and actual.lower() != str(expected).lower())
    missing = not exists
    return {
        "path": str(p) if p else None,
        "exists": exists,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "sha_mismatch": mismatch,
        "file_missing": missing,
        "integrity_ok": exists and not mismatch,
    }


def load_beam_evidence(v10: Path) -> List[Any]:
    rows = load_selection_manifest(v10)
    beams = []
    for row in rows:
        beam = beam_from_manifest_row(row)
        beam.context.integrity = verify_selected_image(row.get("context") or {})
        beam.detail.integrity = verify_selected_image(row.get("detail") or {})
        beams.append(beam)
    return beams


__all__ = [
    "load_beam_evidence",
    "load_selection_manifest",
    "selection_manifest_path",
    "sha256_file",
    "verify_selected_image",
]
