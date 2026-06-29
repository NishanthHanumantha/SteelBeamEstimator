"""Drawing Set version tracking for estimator dataset changes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VERSION_STATUS_CURRENT = "CURRENT"
VERSION_STATUS_SUPERSEDED = "SUPERSEDED"
CHANGE_REASON_INITIAL_LOAD = "INITIAL_LOAD"
CHANGE_REASON_DATASET_CHANGED = "DATASET_CHANGED"


def version_id_for(floor_slug: str, version: str) -> str:
    return f"DSV::{floor_slug}::{version}"


def compute_version_hash(
    project_id: str,
    drawing_records: List[dict[str, Any]],
) -> str:
    """Deterministic hash from drawing IDs, revisions, sheet numbers, and project ID."""
    lines: List[str] = []
    for record in sorted(drawing_records, key=lambda r: str(r.get("drawing_id", ""))):
        lines.append(
            "|".join([
                str(record.get("drawing_id", "")),
                str(record.get("revision", "UNKNOWN")),
                str(record.get("sheet_number", "UNKNOWN")),
            ])
        )
    lines.append(str(project_id))
    payload = "\n".join(lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class DrawingSetVersion:
    """Estimator engine version of a complete drawing set."""

    drawing_set_version: str
    version_id: str
    created_from: List[str]
    last_updated: Optional[str]
    change_reason: str
    version_hash: str
    status: str = VERSION_STATUS_CURRENT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drawing_set_version": self.drawing_set_version,
            "version_id": self.version_id,
            "created_from": list(self.created_from),
            "last_updated": self.last_updated,
            "change_reason": self.change_reason,
            "version_hash": self.version_hash,
            "status": self.status,
            "metadata": self.metadata,
        }
