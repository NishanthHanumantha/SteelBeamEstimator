"""Build or reuse Drawing Set versions from drawing identities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.project.drawing_set_version import (
    CHANGE_REASON_DATASET_CHANGED,
    CHANGE_REASON_INITIAL_LOAD,
    DrawingSetVersion,
    compute_version_hash,
    version_id_for,
    VERSION_STATUS_CURRENT,
)


class DrawingSetVersionBuilder:
    """Create drawing set versions and detect dataset changes via version hash."""

    def build(
        self,
        drawing_set: dict[str, Any],
        identities: List[dict[str, Any]],
        previous_versions_path: Optional[Path] = None,
    ) -> DrawingSetVersion:
        floor_slug = str(
            drawing_set.get("metadata", {}).get("floor_slug")
            or drawing_set.get("floor_id", "").replace("FLOOR::", "")
        )
        project_id = str(drawing_set.get("project_id", ""))
        created_from = self._created_from_list(drawing_set, identities)
        drawing_records = self._drawing_records(created_from, identities, project_id)

        version_hash = compute_version_hash(project_id, drawing_records)
        previous = self._load_previous(floor_slug, previous_versions_path)

        if previous and previous.get("version_hash") == version_hash:
            return DrawingSetVersion(
                drawing_set_version=str(previous.get("drawing_set_version", "1.0")),
                version_id=str(previous.get("version_id", version_id_for(floor_slug, "1.0"))),
                created_from=created_from,
                last_updated=previous.get("last_updated"),
                change_reason=str(previous.get("change_reason", CHANGE_REASON_INITIAL_LOAD)),
                version_hash=version_hash,
                status=VERSION_STATUS_CURRENT,
                metadata={"reused": True},
            )

        version_str = "1.0"
        change_reason = CHANGE_REASON_INITIAL_LOAD
        if previous:
            prev_ver = str(previous.get("drawing_set_version", "1.0"))
            try:
                major, minor = prev_ver.split(".", 1)
                version_str = f"{major}.{int(minor) + 1}"
            except ValueError:
                version_str = "2.0"
            change_reason = CHANGE_REASON_DATASET_CHANGED

        return DrawingSetVersion(
            drawing_set_version=version_str,
            version_id=version_id_for(floor_slug, version_str),
            created_from=created_from,
            last_updated=None,
            change_reason=change_reason,
            version_hash=version_hash,
            status=VERSION_STATUS_CURRENT,
            metadata={"reused": False},
        )

    def _created_from_list(
        self,
        drawing_set: dict[str, Any],
        identities: List[dict[str, Any]],
    ) -> List[str]:
        drawings = drawing_set.get("drawings", {})
        ids: List[str] = []
        for key in ("framing", "reinforcement", "general_notes"):
            did = drawings.get(key)
            if did:
                ids.append(did)
        if ids:
            return ids
        identity_ids = {item.get("drawing_id") for item in identities}
        for did in (drawings.get("framing"), drawings.get("reinforcement"), drawings.get("general_notes")):
            if did and did in identity_ids:
                ids.append(did)
        return ids

    def _drawing_records(
        self,
        created_from: List[str],
        identities: List[dict[str, Any]],
        project_id: str,
    ) -> List[dict[str, Any]]:
        by_id = {item["drawing_id"]: item for item in identities}
        records: List[dict[str, Any]] = []
        for did in created_from:
            identity = by_id.get(did, {})
            records.append({
                "drawing_id": did,
                "revision": identity.get("revision", "UNKNOWN"),
                "sheet_number": identity.get("sheet_number", "UNKNOWN"),
                "project_id": project_id,
            })
        return records

    def _load_previous(
        self,
        floor_slug: str,
        path: Optional[Path],
    ) -> Optional[dict[str, Any]]:
        if not path or not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        versions = data.get("versions", [])
        for entry in versions:
            if entry.get("floor_slug") == floor_slug or (
                entry.get("version_id", "").startswith(f"DSV::{floor_slug}::")
            ):
                return entry
        if versions:
            return versions[0]
        return None
