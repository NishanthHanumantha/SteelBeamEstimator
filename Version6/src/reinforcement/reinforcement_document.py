"""Reinforcement document metadata model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


DRAWING_TYPE_BEAM_REINFORCEMENT = "BEAM_REINFORCEMENT"
STATUS_NOT_LOADED = "NOT_LOADED"
STATUS_LOADING = "LOADING"
STATUS_LOADED = "LOADED"


@dataclass
class ReinforcementDocument:
    """Metadata for a loaded reinforcement detail drawing."""

    document_id: str
    source_file: str
    drawing_name: str
    drawing_type: str = DRAWING_TYPE_BEAM_REINFORCEMENT
    status: str = STATUS_LOADED
    loaded_time: str = ""
    entity_count: int = 0
    layer_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.loaded_time:
            self.loaded_time = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "source_file": self.source_file,
            "drawing_name": self.drawing_name,
            "drawing_type": self.drawing_type,
            "status": self.status,
            "loaded_time": self.loaded_time,
            "entity_count": self.entity_count,
            "layer_count": self.layer_count,
            "metadata": dict(self.metadata),
        }
