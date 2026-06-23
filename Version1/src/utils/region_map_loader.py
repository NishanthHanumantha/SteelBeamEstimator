"""Load entity-to-region assignments from JSON."""

import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger


class RegionMapLoadError(Exception):
    """Raised when the entity region map cannot be read."""


def load_entity_region_map(map_path: Path) -> Dict[str, str]:
    """
    Load handle → region mapping from entity_region_map.json.

    Accepts a list of ``{handle, region}`` records or a dict keyed by handle.
    """
    path = Path(map_path).resolve()

    if not path.exists():
        raise RegionMapLoadError(f"Region map not found: {path}")

    try:
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as exc:
        raise RegionMapLoadError(f"Invalid JSON in region map: {path} — {exc}") from exc
    except OSError as exc:
        raise RegionMapLoadError(f"Failed to read region map: {path} — {exc}") from exc

    mapping: Dict[str, str] = {}

    if isinstance(payload, dict):
        for handle, value in payload.items():
            if isinstance(value, str):
                mapping[str(handle)] = value
            elif isinstance(value, dict) and "region" in value:
                mapping[str(handle)] = str(value["region"])
    elif isinstance(payload, list):
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            handle = entry.get("handle")
            region = entry.get("region")
            if handle and region:
                mapping[str(handle)] = str(region)
    else:
        raise RegionMapLoadError(
            "Region map must be a list of records or a handle-keyed dict"
        )

    logger.info("Loaded {} entity region assignments from {}", len(mapping), path)
    return mapping


def filter_entities_by_region(
    entities: List[dict[str, Any]],
    region_map: Dict[str, str],
    region: str,
) -> List[dict[str, Any]]:
    """Return entities whose handle is assigned to the given region."""
    filtered = [
        entity
        for entity in entities
        if region_map.get(str(entity.get("handle", ""))) == region
    ]
    logger.info(
        "Filtered {} / {} entities for region '{}'",
        len(filtered),
        len(entities),
        region,
    )
    return filtered
