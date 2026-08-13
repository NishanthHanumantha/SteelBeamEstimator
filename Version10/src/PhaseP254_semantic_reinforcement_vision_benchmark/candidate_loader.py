"""Load frozen P2.5.x evidence for P2.5.4 — no crop regeneration."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    EVIDENCE_MODE_LOCAL_PLUS_CONTEXT,
    P250_OUTPUT,
    P251_OUTPUT,
    P2523_OUTPUT,
)

MODEL_VERSION = "10.8.0"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_quantity_intents(version10_root: Path) -> List[Dict[str, Any]]:
    path = (
        Path(version10_root)
        / "data"
        / "output"
        / P251_OUTPUT
        / "quantity_intent_matrix.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"P2.5.1 intent matrix not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("quantity_intent_matrix.json must be a list")
    return data


def load_p2523_candidates(version10_root: Path) -> List[Dict[str, Any]]:
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
    return sorted(data, key=lambda m: (m.get("beam_id") or "", m.get("annotation_id") or ""))


def load_p250_evidence(version10_root: Path, beam_id: str) -> Optional[Dict[str, Any]]:
    path = (
        Path(version10_root)
        / "data"
        / "output"
        / P250_OUTPUT
        / "beams"
        / beam_id
        / "evidence.json"
    )
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def p250_engineering_crop(version10_root: Path, beam_id: str) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / P250_OUTPUT
        / "beams"
        / beam_id
        / "engineering_crop.png"
    )


def p2523_candidate_dir(version10_root: Path, candidate_id: str) -> Path:
    return (
        Path(version10_root)
        / "data"
        / "output"
        / P2523_OUTPUT
        / "candidates"
        / candidate_id.replace("::", "__")
    )


def encode_image(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return None
    raw = path.read_bytes()
    if not raw:
        return None
    return {
        "path": str(path),
        "media_type": "image/png",
        "data_base64": base64.standard_b64encode(raw).decode("ascii"),
        "sha256": _sha256_bytes(raw),
        "size_bytes": len(raw),
    }


def resolve_evidence_paths(
    *,
    version10_root: Path,
    candidate_id: str,
    beam_id: str,
    source: str,
) -> Dict[str, Optional[Path]]:
    """
    Prefer P2.5.2.3 refined crops when the candidate is in that frozen set.
    Otherwise reuse P2.5.0 engineering crop (no regeneration).
    """
    local: Optional[Path] = None
    context: Optional[Path] = None
    provenance = "P250_ENGINEERING_CROP"
    if source == "P2523":
        folder = p2523_candidate_dir(version10_root, candidate_id)
        loc = folder / "local_target_complete.png"
        ctx = folder / "beam_context_target_complete.png"
        if loc.exists():
            local = loc
            provenance = "P2523_LOCAL_TARGET_COMPLETE"
        if ctx.exists():
            context = ctx
            provenance = "P2523_LOCAL_PLUS_CONTEXT"
    if local is None:
        eng = p250_engineering_crop(version10_root, beam_id)
        if eng.exists():
            local = eng
            provenance = "P250_ENGINEERING_CROP"
        if context is None and eng.exists():
            # Single beam-window crop; do not invent a second image.
            context = None
    return {
        "local": local,
        "context": context,
        "provenance": provenance,  # type: ignore[dict-item]
    }


def claude_safe_metadata(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic context only — no expected answers / GT / semantic class."""
    return {
        "candidate_id": candidate.get("candidate_id"),
        "beam_id": candidate.get("beam_id"),
        "annotation_id": candidate.get("annotation_id"),
        "raw_text": candidate.get("raw_text"),
        "normalized_text": candidate.get("normalized_text"),
        "quantity_intent_status": candidate.get("quantity_status"),
        "deterministic_semantic_type": candidate.get("baseline_semantic_type"),
        "deterministic_role": candidate.get("baseline_role"),
        "candidate_reason": candidate.get("candidate_reason"),
        "candidate_reason_codes": candidate.get("candidate_reason_codes"),
        "beam_depth_mm": candidate.get("beam_depth_mm"),
        "beam_orientation": candidate.get("beam_orientation"),
        "provenance_ids": candidate.get("provenance_ids") or {},
        "upstream_source": candidate.get("evidence_source"),
        "evidence_mode": candidate.get("evidence_mode"),
        "sibling_annotation_count": candidate.get("sibling_annotation_count"),
        "sibling_annotation_texts": candidate.get("sibling_annotation_texts") or [],
    }


def build_evidence_package(
    *,
    candidate: Dict[str, Any],
    version10_root: Path,
    evidence_mode: str = EVIDENCE_MODE_LOCAL_PLUS_CONTEXT,
) -> Dict[str, Any]:
    paths = resolve_evidence_paths(
        version10_root=version10_root,
        candidate_id=candidate["candidate_id"],
        beam_id=candidate["beam_id"],
        source=candidate.get("evidence_source") or "P250",
    )
    images: List[Dict[str, Any]] = []
    local_img = encode_image(paths["local"]) if paths.get("local") else None
    if local_img:
        local_img["role"] = "local_crop"
        images.append(local_img)
    if evidence_mode == EVIDENCE_MODE_LOCAL_PLUS_CONTEXT and paths.get("context"):
        ctx_img = encode_image(paths["context"])
        if ctx_img and ctx_img.get("sha256") != (local_img or {}).get("sha256"):
            ctx_img["role"] = "beam_context_crop"
            images.append(ctx_img)

    metadata = claude_safe_metadata(candidate)
    metadata["evidence_mode"] = evidence_mode
    metadata["image_roles"] = [im.get("role") for im in images]
    # Guard: never leak GT keys
    for banned in (
        "ground_truth",
        "expected_role",
        "expected_type",
        "semantic_class",
        "expected_quantity",
        "expected_diameter_mm",
        "expected_spacing_mm",
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
        "candidate_id": candidate["candidate_id"],
        "metadata": metadata,
        "images": images,
        "local_image_path": str(paths["local"]) if paths.get("local") else None,
        "context_image_path": str(paths["context"]) if paths.get("context") else None,
        "evidence_fingerprint": evidence_fp,
        "evidence_mode": evidence_mode,
        "evidence_provenance": paths.get("provenance"),
    }


__all__ = [
    "build_evidence_package",
    "claude_safe_metadata",
    "load_p250_evidence",
    "load_p2523_candidates",
    "load_quantity_intents",
    "p250_engineering_crop",
]
