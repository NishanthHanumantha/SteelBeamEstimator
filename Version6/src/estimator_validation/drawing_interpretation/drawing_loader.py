"""Load read-only drawing and pipeline JSON — Phase QA.3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.estimator_validation.comparison_utils import load_json_if_exists
from src.estimator_validation.drawing_interpretation.interpretation_types import default_paths


class DrawingLoader:
    """Load existing JSON outputs without parser execution."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.paths = default_paths(project_root)

    def load_all(self) -> dict[str, Any]:
        data: dict[str, Any] = {"paths": {key: str(path) for key, path in self.paths.items()}}
        load_status: Dict[str, bool] = {}

        def load_payload(key: str, list_keys: tuple[str, ...] = ("results",)) -> Any:
            payload = load_json_if_exists(self.paths[key])
            load_status[key] = payload is not None
            return payload

        data["reinforcement_text"] = load_payload("reinforcement_text")
        data["engineering_properties"] = load_payload("engineering_properties")
        data["reinforcement_objects"] = load_payload("reinforcement_objects")
        data["bar_identities"] = self._list(load_payload("bar_identity"), "results")
        data["bar_groups"] = self._list(load_payload("bar_group"), "results")
        data["beam_schedules"] = self._list(load_payload("beam_schedule"), "results")
        data["engineering_reports"] = self._list(load_payload("engineering_report"), "results")
        data["beam_summaries"] = self._list(load_payload("beam_summary"), "results")
        data["calculation_contexts"] = self._list(load_payload("calculation_context"), "contexts")
        data["clear_spans"] = self._list(load_payload("clear_spans"), "beams")
        data["beam_dimensions"] = self._list(load_payload("beam_dimensions"), None)
        framing = load_payload("framing_beams")
        load_status["framing_beams"] = framing is not None
        if isinstance(framing, list):
            data["framing_beams"] = framing
        else:
            data["framing_beams"] = framing.get("beams") or framing.get("results") or [] if framing else []

        data["load_status"] = load_status
        data["schedules_by_beam"] = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in data["beam_schedules"]
        }
        data["reports_by_beam"] = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in data["engineering_reports"]
        }
        data["summaries_by_beam"] = {
            str(item.get("beam_mark") or item.get("beam_id")): item for item in data["beam_summaries"]
        }
        return data

    @staticmethod
    def _list(payload: Any, key: Optional[str]) -> List[dict[str, Any]]:
        if payload is None:
            return []
        if key is None and isinstance(payload, list):
            return payload
        if key and isinstance(payload, dict):
            return payload.get(key) or []
        return []

    @staticmethod
    def beam_mark_from_owner(owner_id: str) -> Optional[str]:
        if not owner_id:
            return None
        if owner_id.startswith("ERC::"):
            return owner_id.split("::", 1)[1]
        return owner_id
