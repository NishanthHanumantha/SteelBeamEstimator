"""Project-level workspace container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ProjectWorkspace:
    """Owns project metadata, engineering knowledge refs, floors, and services."""

    project_id: str
    project_name: str
    general_notes: dict[str, Any]
    engineering_rules: dict[str, Any]
    floors: List[dict[str, Any]]
    services: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "general_notes": self.general_notes,
            "engineering_rules": self.engineering_rules,
            "floors": self.floors,
            "services": self.services,
            "metadata": self.metadata,
        }
