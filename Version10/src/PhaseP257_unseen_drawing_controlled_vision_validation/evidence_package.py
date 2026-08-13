"""Fifth Set crop evidence for the frozen P2.5.4 prompt. No ground truth in metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PhaseP254_semantic_reinforcement_vision_benchmark.candidate_loader import (
    claude_safe_metadata,
    encode_image,
)
from PhaseP254_semantic_reinforcement_vision_benchmark.config import PRIMARY_EVIDENCE_MODE
from PhaseP254_semantic_reinforcement_vision_benchmark.vision_prompt import (
    BANNED_KEYS,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_unseen_evidence_package(candidate: Dict[str, Any]) -> Dict[str, Any]:
    crop: Optional[Path] = None
    if candidate.get("crop_path"):
        crop = Path(candidate["crop_path"])
    images: List[Dict[str, Any]] = []
    local = encode_image(crop) if crop is not None else None
    if local:
        local["role"] = "local_crop"
        images.append(local)

    metadata = claude_safe_metadata(candidate)
    metadata["evidence_mode"] = PRIMARY_EVIDENCE_MODE
    metadata["image_roles"] = [im.get("role") for im in images]
    for banned in BANNED_KEYS:
        metadata.pop(banned, None)
    for banned in (
        "ground_truth",
        "expected_role",
        "expected_type",
        "semantic_class",
        "expected_quantity",
        "expected_diameter_mm",
        "expected_spacing_mm",
        "estimator_excel",
        "evaluation_label",
    ):
        metadata.pop(banned, None)

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
        "candidate_id": candidate.get("candidate_id"),
        "metadata": metadata,
        "images": images,
        "local_image_path": str(crop) if crop else None,
        "evidence_fingerprint": evidence_fp,
        "evidence_mode": PRIMARY_EVIDENCE_MODE,
        "evidence_provenance": "FIFTH_SET_SHARED_RENDER_CROP",
    }


__all__ = ["build_unseen_evidence_package"]
