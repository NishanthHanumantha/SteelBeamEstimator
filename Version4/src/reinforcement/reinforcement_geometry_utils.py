"""Shared DXF geometry helpers for reinforcement intelligence."""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Optional, Tuple

from ezdxf import bbox as ezbbox
from ezdxf.entities import DXFEntity

from src.utils.text_cleaner import clean_dxf_text

Bbox = dict[str, float]

BEAM_SECTION_PATTERN = re.compile(
    r"^(?:%%U)?(B\d+)\s*\(\s*(\d+)\s*[Xx]\s*(\d+)\s*\)\s*$",
    re.IGNORECASE,
)


def entity_center(entity: DXFEntity) -> Optional[Tuple[float, float]]:
    box = entity_bbox(entity)
    if not box:
        return None
    return (
        (box["min_x"] + box["max_x"]) / 2.0,
        (box["min_y"] + box["max_y"]) / 2.0,
    )


def entity_bbox(entity: DXFEntity) -> Optional[Bbox]:
    try:
        ext = ezbbox.extents([entity])
        if ext.has_data:
            return {
                "min_x": round(ext.extmin.x, 3),
                "min_y": round(ext.extmin.y, 3),
                "max_x": round(ext.extmax.x, 3),
                "max_y": round(ext.extmax.y, 3),
            }
    except Exception:
        pass

    dxftype = entity.dxftype()
    try:
        if dxftype in ("TEXT", "ATTRIB"):
            x, y = float(entity.dxf.insert.x), float(entity.dxf.insert.y)
            height = float(getattr(entity.dxf, "height", 250.0) or 250.0)
            return {
                "min_x": round(x, 3),
                "min_y": round(y, 3),
                "max_x": round(x + height * 4, 3),
                "max_y": round(y + height, 3),
            }
        if dxftype == "MTEXT":
            x, y = float(entity.dxf.insert.x), float(entity.dxf.insert.y)
            height = float(getattr(entity.dxf, "char_height", 250.0) or 250.0)
            return {
                "min_x": round(x, 3),
                "min_y": round(y, 3),
                "max_x": round(x + height * 8, 3),
                "max_y": round(y + height * 2, 3),
            }
        if dxftype == "INSERT":
            x, y = float(entity.dxf.insert.x), float(entity.dxf.insert.y)
            return {
                "min_x": round(x, 3),
                "min_y": round(y, 3),
                "max_x": round(x + 500.0, 3),
                "max_y": round(y + 500.0, 3),
            }
    except Exception:
        return None
    return None


def merge_bboxes(boxes: Iterable[Bbox]) -> Optional[Bbox]:
    items = [b for b in boxes if b]
    if not items:
        return None
    return {
        "min_x": min(b["min_x"] for b in items),
        "min_y": min(b["min_y"] for b in items),
        "max_x": max(b["max_x"] for b in items),
        "max_y": max(b["max_y"] for b in items),
    }


def expand_bbox(box: Bbox, margin_x: float, margin_y: float) -> Bbox:
    return {
        "min_x": box["min_x"] - margin_x,
        "min_y": box["min_y"] - margin_y,
        "max_x": box["max_x"] + margin_x,
        "max_y": box["max_y"] + margin_y,
    }


def point_in_bbox(x: float, y: float, box: Bbox) -> bool:
    return box["min_x"] <= x <= box["max_x"] and box["min_y"] <= y <= box["max_y"]


def bbox_contains(outer: Bbox, inner: Bbox) -> bool:
    return (
        outer["min_x"] <= inner["min_x"]
        and outer["min_y"] <= inner["min_y"]
        and outer["max_x"] >= inner["max_x"]
        and outer["max_y"] >= inner["max_y"]
    )


def bbox_center(box: Bbox) -> Tuple[float, float]:
    return (
        (box["min_x"] + box["max_x"]) / 2.0,
        (box["min_y"] + box["max_y"]) / 2.0,
    )


def bbox_area(box: Bbox) -> float:
    return max(0.0, box["max_x"] - box["min_x"]) * max(0.0, box["max_y"] - box["min_y"])


def bbox_aspect_ratio(box: Bbox) -> float:
    width = max(box["max_x"] - box["min_x"], 1.0)
    height = max(box["max_y"] - box["min_y"], 1.0)
    return width / height


def entity_text(entity: DXFEntity) -> str:
    dxftype = entity.dxftype()
    try:
        if dxftype == "MTEXT":
            raw = entity.plain_text() if hasattr(entity, "plain_text") else str(entity.text)
        elif dxftype == "ATTRIB":
            raw = str(entity.dxf.text)
        elif dxftype == "TEXT":
            raw = str(entity.dxf.text)
        else:
            return ""
        return clean_dxf_text(raw)
    except Exception:
        return ""


def layer_name(entity: DXFEntity) -> str:
    try:
        return str(entity.dxf.layer)
    except Exception:
        return ""


def parse_beam_section_label(text: str) -> Optional[dict[str, Any]]:
    match = BEAM_SECTION_PATTERN.match(text.strip())
    if not match:
        return None
    return {
        "beam_mark": match.group(1).upper(),
        "width_mm": int(match.group(2)),
        "depth_mm": int(match.group(3)),
    }


def normalize_layers(config_layers: Any) -> List[str]:
    if isinstance(config_layers, str):
        return [part.strip() for part in config_layers.split(",") if part.strip()]
    if isinstance(config_layers, list):
        return [str(part).strip() for part in config_layers if str(part).strip()]
    return []
