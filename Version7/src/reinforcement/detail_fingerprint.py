"""Engineering Detail Fingerprint — immutable deterministic signature."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

FINGERPRINT_VERSION = "1.0"
PREFIX_FINGERPRINT = "FINGERPRINT"


def format_fingerprint_id(detail_identity_id: str) -> str:
    if "::" in detail_identity_id:
        suffix = detail_identity_id.split("::", 1)[1]
        return f"{PREFIX_FINGERPRINT}::{suffix}"
    return f"{PREFIX_FINGERPRINT}::{detail_identity_id}"


@dataclass
class EngineeringDetailFingerprint:
    """Stable engineering signature for a detail identity."""

    fingerprint_id: str
    detail_identity_id: str
    fingerprint_version: str = FINGERPRINT_VERSION
    bbox_hash: str = ""
    beam_marks_hash: str = ""
    geometry_hash: str = ""
    view_hash: str = ""
    entity_count: int = 0
    text_count: int = 0
    leader_count: int = 0
    block_count: int = 0
    overall_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint_id": self.fingerprint_id,
            "detail_identity_id": self.detail_identity_id,
            "fingerprint_version": self.fingerprint_version,
            "bbox_hash": self.bbox_hash,
            "beam_marks_hash": self.beam_marks_hash,
            "geometry_hash": self.geometry_hash,
            "view_hash": self.view_hash,
            "entity_count": self.entity_count,
            "text_count": self.text_count,
            "leader_count": self.leader_count,
            "block_count": self.block_count,
            "overall_hash": self.overall_hash,
        }
