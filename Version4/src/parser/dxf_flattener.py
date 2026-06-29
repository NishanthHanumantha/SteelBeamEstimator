"""Flatten DXF modelspace entities, expanding INSERT block references."""

from typing import Any, Iterable, Iterator, List

from ezdxf.entities.dxfgfx import DXFGraphic
from loguru import logger


def flatten_entities(entities: Iterable[DXFGraphic]) -> List[DXFGraphic]:
    """Return a flat list of entities, expanding INSERT virtual entities."""
    flat: List[DXFGraphic] = []
    for entity in entities:
        _flatten_one(entity, flat)
    logger.debug("Flattened {} top-level entities to {}", _count_top(entities), len(flat))
    return flat


def _count_top(entities: Iterable[DXFGraphic]) -> int:
    return sum(1 for _ in entities)


def _flatten_one(entity: DXFGraphic, out: List[DXFGraphic]) -> None:
    if entity.dxftype() == "INSERT":
        try:
            for virtual in entity.virtual_entities():
                _flatten_one(virtual, out)
        except Exception as exc:
            handle = getattr(entity.dxf, "handle", "unknown")
            logger.warning("Could not expand INSERT handle={}: {}", handle, exc)
        return
    out.append(entity)


def iter_flat_entities(entities: Iterable[DXFGraphic]) -> Iterator[DXFGraphic]:
    """Lazily yield flattened entities."""
    for entity in entities:
        if entity.dxftype() == "INSERT":
            try:
                yield from iter_flat_entities(entity.virtual_entities())
            except Exception:
                continue
        else:
            yield entity
