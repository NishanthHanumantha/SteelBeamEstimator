"""Bounding-box utilities for drawing regions."""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.regions.constants import REGION_TYPES


@dataclass
class BoundingBox:
    xmin: float = math.inf
    ymin: float = math.inf
    xmax: float = -math.inf
    ymax: float = -math.inf
    entity_count: int = 0

    def include(self, x: float, y: float) -> None:
        self.xmin = min(self.xmin, x)
        self.ymin = min(self.ymin, y)
        self.xmax = max(self.xmax, x)
        self.ymax = max(self.ymax, y)
        self.entity_count += 1

    def is_valid(self) -> bool:
        return self.entity_count > 0 and self.xmin <= self.xmax and self.ymin <= self.ymax

    def pad(self, margin: float) -> None:
        if not self.is_valid():
            return
        self.xmin -= margin
        self.ymin -= margin
        self.xmax += margin
        self.ymax += margin

    def contains(self, x: float, y: float) -> bool:
        if not self.is_valid():
            return False
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax

    def as_dict(self, region_type: str, confidence: float) -> dict:
        return {
            "region_type": region_type,
            "xmin": round(self.xmin, 6),
            "ymin": round(self.ymin, 6),
            "xmax": round(self.xmax, 6),
            "ymax": round(self.ymax, 6),
            "confidence": round(confidence, 4),
            "entity_count": self.entity_count,
        }


def empty_region_boxes() -> Dict[str, BoundingBox]:
    return {region: BoundingBox() for region in REGION_TYPES if region != "unassigned"}


def merge_boxes(boxes: List[BoundingBox]) -> BoundingBox:
    merged = BoundingBox()
    for box in boxes:
        if not box.is_valid():
            continue
        merged.xmin = min(merged.xmin, box.xmin)
        merged.ymin = min(merged.ymin, box.ymin)
        merged.xmax = max(merged.xmax, box.xmax)
        merged.ymax = max(merged.ymax, box.ymax)
        merged.entity_count += box.entity_count
    return merged


def distance_to_box(x: float, y: float, box: BoundingBox) -> float:
    if not box.is_valid():
        return math.inf

    dx = 0.0
    if x < box.xmin:
        dx = box.xmin - x
    elif x > box.xmax:
        dx = x - box.xmax

    dy = 0.0
    if y < box.ymin:
        dy = box.ymin - y
    elif y > box.ymax:
        dy = y - box.ymax

    return math.hypot(dx, dy)
