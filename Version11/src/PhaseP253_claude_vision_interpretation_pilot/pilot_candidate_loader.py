"""Load frozen P2.5.2.3 Vision candidates + evidence images."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    EVIDENCE_MODE_LOCAL_ONLY,
    EVIDENCE_MODE_LOCAL_PLUS_CONTEXT,
    EXPECTED_VISION_CANDIDATES,
    P2523_OUTPUT,
)

MODEL_VERSION = "10.7.0"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return _sha256_bytes(path.read_bytes())


def load_frozen_candidates(version10_root: Path) -> List[Dict[str, Any]]:
    path = (
        Path(version10_root)
        / "data"
        / "output"
        / P2523_OUTPUT
        / "manifests"
        / "TargetBeamCompletenessManifest.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"P2.5.2.3 manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data = sorted(data, key=lambda m: (m.get("beam_id") or "", m.get("annotation_id") or ""))
    if len(data) != EXPECTED_VISION_CANDIDATES:
        raise ValueError(
            f"Expected {EXPECTED_VISION_CANDIDATES} frozen candidates, got {len(data)}"
        )
    return data


def _encode_image(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    raw = path.read_bytes()
    return {
        "path": str(path),
        "media_type": "image/png",
        "data_base64": base64.standard_b64encode(raw).decode("ascii"),
        "sha256": _sha256_bytes(raw),
        "size_bytes": len(raw),
    }


def build_evidence_package(
    *,
    candidate: Dict[str, Any],
    version10_root: Path,
    evidence_mode: str = EVIDENCE_MODE_LOCAL_PLUS_CONTEXT,
) -> Dict[str, Any]:
    """Assemble Claude-facing evidence without ground truth."""
    cid = candidate["candidate_id"]
    folder = (
        Path(version10_root)
        / "data"
        / "output"
        / P2523_OUTPUT
        / "candidates"
        / cid.replace("::", "__")
    )
    local_path = folder / "local_target_complete.png"
    ctx_path = folder / "beam_context_target_complete.png"

    images = []
    local_img = _encode_image(local_path)
    if local_img:
        local_img["role"] = "local_crop"
        images.append(local_img)
    if evidence_mode == EVIDENCE_MODE_LOCAL_PLUS_CONTEXT:
        ctx_img = _encode_image(ctx_path)
        if ctx_img:
            ctx_img["role"] = "beam_context_crop"
            images.append(ctx_img)

    metadata = {
        "candidate_id": cid,
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "raw_text": candidate.get("raw_text"),
        "normalized_text": candidate.get("normalized_text"),
        "candidate_priority": candidate.get("candidate_priority"),
        "candidate_reason_codes": candidate.get("candidate_reason_codes"),
        "outcome": candidate.get("outcome"),
        "overall_completeness_upstream": candidate.get("overall_completeness"),
        "evidence_mode": evidence_mode,
        # Do NOT include expected answers / ground truth
    }

    evidence_fp = _sha256_bytes(
        json.dumps(
            {
                "metadata": metadata,
                "image_hashes": [im.get("sha256") for im in images],
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    )

    return {
        "candidate_id": cid,
        "metadata": metadata,
        "images": images,
        "local_image_path": str(local_path) if local_path.exists() else None,
        "context_image_path": str(ctx_path) if ctx_path.exists() else None,
        "evidence_fingerprint": evidence_fp,
        "evidence_mode": evidence_mode,
    }


__all__ = ["build_evidence_package", "load_frozen_candidates"]
