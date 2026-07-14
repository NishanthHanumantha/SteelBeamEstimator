"""Build deterministic engineering detail fingerprints."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from src.reinforcement.detail_fingerprint import (
    FINGERPRINT_VERSION,
    EngineeringDetailFingerprint,
    format_fingerprint_id,
)


class DetailFingerprintBuilder:
    """Create immutable fingerprints from detail identities and geometry references."""

    def __init__(self, bbox_round_mm: float = 1.0) -> None:
        self._bbox_round_mm = bbox_round_mm

    def build(
        self,
        identities: List[dict[str, Any]],
        contexts: List[dict[str, Any]],
        regions: List[dict[str, Any]],
        detail_views: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        region_bbox = {r.get("geometry_id"): r.get("bbox", {}) for r in regions}
        ctx_by_id = {c.get("detail_context_id"): c for c in contexts}
        views_by_id = {
            v.get("view_id", v.get("geometry_id")): v for v in detail_views
        }

        fingerprints: List[dict[str, Any]] = []
        for identity in identities:
            identity_id = identity.get("detail_identity_id", "")
            ctx = ctx_by_id.get(identity.get("detail_context_id", ""), {})
            region_id = ctx.get("region_id", "")
            bbox = region_bbox.get(region_id, {})

            view_ids = list(identity.get("metadata", {}).get("view_ids", ctx.get("view_ids", [])))
            primary = str(identity.get("primary_beam_mark", ""))
            secondary = list(identity.get("secondary_beam_marks", []))
            all_marks = ([primary] if primary else []) + secondary

            geometry_ids: List[str] = []
            text_ids: List[str] = []
            leader_ids: List[str] = []
            block_ids: List[str] = []
            for vid in view_ids:
                view = views_by_id.get(vid, {})
                geometry_ids.extend(view.get("geometry_entities", []))
                text_ids.extend(view.get("text_entities", []))
                leader_ids.extend(view.get("leader_entities", []))
                block_ids.extend(view.get("block_entities", []))

            bbox_h = self._bbox_hash(bbox)
            marks_h = self._beam_marks_hash(all_marks)
            geom_h = self._ids_hash(geometry_ids)
            view_h = self._ids_hash(view_ids)
            overall = self._overall_hash(bbox_h, marks_h, geom_h, view_h)

            fp = EngineeringDetailFingerprint(
                fingerprint_id=format_fingerprint_id(identity_id),
                detail_identity_id=identity_id,
                fingerprint_version=FINGERPRINT_VERSION,
                bbox_hash=bbox_h,
                beam_marks_hash=marks_h,
                geometry_hash=geom_h,
                view_hash=view_h,
                entity_count=len(geometry_ids),
                text_count=len(text_ids),
                leader_count=len(leader_ids),
                block_count=len(block_ids),
                overall_hash=overall,
            )
            fingerprints.append(fp.to_dict())

        return fingerprints

    def _sha256(self, payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _bbox_hash(self, bbox: dict[str, float]) -> str:
        if not bbox:
            return self._sha256("")
        rounded = {
            k: round(float(bbox[k]) / self._bbox_round_mm) * self._bbox_round_mm
            for k in sorted(bbox.keys())
        }
        return self._sha256(json.dumps(rounded, sort_keys=True))

    def _beam_marks_hash(self, marks: List[str]) -> str:
        return self._sha256(json.dumps(sorted(marks), sort_keys=True))

    def _ids_hash(self, ids: List[str]) -> str:
        return self._sha256(json.dumps(sorted(ids), sort_keys=True))

    def _overall_hash(
        self,
        bbox_hash: str,
        beam_marks_hash: str,
        geometry_hash: str,
        view_hash: str,
    ) -> str:
        parts = {
            "fingerprint_version": FINGERPRINT_VERSION,
            "bbox_hash": bbox_hash,
            "beam_marks_hash": beam_marks_hash,
            "geometry_hash": geometry_hash,
            "view_hash": view_hash,
        }
        return self._sha256(json.dumps(parts, sort_keys=True))
