"""Load parsed DXF entity payloads from JSON."""

import json
from pathlib import Path
from typing import Any, List

from loguru import logger


class EntitiesLoadError(Exception):
    """Raised when entities JSON cannot be read or validated."""


def load_entities_json(entities_path: Path) -> List[dict[str, Any]]:
    """
    Load entity records from entities.json.

    Accepts either a top-level list or ``{"entities": [...]}`` wrapper.
    """
    path = Path(entities_path).resolve()

    if not path.exists():
        raise EntitiesLoadError(f"Entities file not found: {path}")

    try:
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as exc:
        raise EntitiesLoadError(f"Invalid JSON in entities file: {path} — {exc}") from exc
    except OSError as exc:
        raise EntitiesLoadError(f"Failed to read entities file: {path} — {exc}") from exc

    if isinstance(payload, list):
        entities = payload
    elif isinstance(payload, dict) and "entities" in payload:
        entities = payload["entities"]
    else:
        raise EntitiesLoadError(
            "Entities file must be a list or contain an 'entities' key"
        )

    if not isinstance(entities, list):
        raise EntitiesLoadError("'entities' must be a list")

    logger.info("Loaded {} entities from {}", len(entities), path)
    return entities
