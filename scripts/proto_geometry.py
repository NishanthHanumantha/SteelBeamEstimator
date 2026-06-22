"""Prototype geometry-driven detail extraction — dev only."""

import math
import re
from collections import defaultdict, deque

import ezdxf

from src.regions.text_normalizer import normalize_drawing_text

TARGET_LAYERS = frozenset({"-STR-BEAM", "-STR-REINF", "-STR-COLUMN", "-S-DIM"})
CONNECT_TOL = 2.0
MAX_BRIDGE = 6000.0
TEXT_PAD = 400.0
SEED_BBOX_DIST = 4500.0
MAX_LABEL_DIST = 5200.0
MAX_DETAIL_SPAN = 12000.0


def pt_key(x: float, y: float) -> tuple[float, float]:
    return (round(x / CONNECT_TOL) * CONNECT_TOL, round(y / CONNECT_TOL) * CONNECT_TOL)


def seg_len(x1, y1, x2, y2) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def dist_point_bbox(px: float, py: float, xmin, ymin, xmax, ymax) -> float:
    dx = max(xmin - px, 0, px - xmax)
    dy = max(ymin - py, 0, py - ymax)
    return math.hypot(dx, dy)


def bbox_intersects(bb1, bb2) -> bool:
    return not (
        bb1[2] < bb2[0]
        or bb1[0] > bb2[2]
        or bb1[3] < bb2[1]
        or bb1[1] > bb2[3]
    )


def extract_segments(msp) -> list[tuple]:
    segments: list[tuple] = []
    poly_bboxes: list[tuple] = []

    for entity in msp.query("LINE"):
        if entity.dxf.layer not in TARGET_LAYERS:
            continue
        x1, y1 = entity.dxf.start.x, entity.dxf.start.y
        x2, y2 = entity.dxf.end.x, entity.dxf.end.y
        if seg_len(x1, y1, x2, y2) > MAX_BRIDGE:
            continue
        segments.append((x1, y1, x2, y2, entity.dxf.handle))

    for entity in msp.query("LWPOLYLINE"):
        if entity.dxf.layer not in TARGET_LAYERS:
            continue
        points = list(entity.get_points("xy"))
        if not points:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        poly_bboxes.append((min(xs), min(ys), max(xs), max(ys), entity.dxf.handle))
        for i in range(len(points) - 1):
            x1, y1 = points[i][0], points[i][1]
            x2, y2 = points[i + 1][0], points[i + 1][1]
            if seg_len(x1, y1, x2, y2) > MAX_BRIDGE:
                continue
            segments.append((x1, y1, x2, y2, entity.dxf.handle))
        if len(points) > 2 and points[0] != points[-1]:
            x1, y1 = points[-1][0], points[-1][1]
            x2, y2 = points[0][0], points[0][1]
            if seg_len(x1, y1, x2, y2) <= MAX_BRIDGE:
                segments.append((x1, y1, x2, y2, entity.dxf.handle))

    return segments, poly_bboxes


def run(label_xy: tuple[float, float], mark: str) -> None:
    doc = ezdxf.readfile("data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf")
    msp = doc.modelspace()
    segments, poly_bboxes = extract_segments(msp)

    segment_bboxes = []
    for segment in segments:
        xs = (segment[0], segment[2])
        ys = (segment[1], segment[3])
        segment_bboxes.append((min(xs), min(ys), max(xs), max(ys)))

    lx, ly = label_xy
    candidates = []
    for bb in poly_bboxes:
        xmin, ymin, xmax, ymax = bb[0], bb[1], bb[2], bb[3]
        width = xmax - xmin
        height = ymax - ymin
        if width > MAX_DETAIL_SPAN or height > MAX_DETAIL_SPAN:
            continue
        if ymax > ly + 200.0:
            continue
        dist = dist_point_bbox(lx, ly, xmin, ymin, xmax, ymax)
        if dist <= SEED_BBOX_DIST:
            candidates.append((dist, bb))

    if not candidates:
        print(mark, "no seed polyline")
        return

    _, seed_poly = min(candidates, key=lambda item: item[0])
    seed_bb = (seed_poly[0], seed_poly[1], seed_poly[2], seed_poly[3])
    pad = 200.0
    seed_bb = (
        seed_bb[0] - pad,
        seed_bb[1] - pad,
        seed_bb[2] + pad,
        seed_bb[3] + pad,
    )

    seeds = [
        i
        for i, bb in enumerate(segment_bboxes)
        if bbox_intersects(bb, seed_bb)
    ]
    print(mark, "seed poly", seed_poly[:4], "seed segments", len(seeds))

    node_segs: dict[tuple[float, float], list[int]] = defaultdict(list)
    for index, segment in enumerate(segments):
        node_segs[pt_key(segment[0], segment[1])].append(index)
        node_segs[pt_key(segment[2], segment[3])].append(index)

    def neighbors(index: int):
        segment = segments[index]
        for key in (pt_key(segment[0], segment[1]), pt_key(segment[2], segment[3])):
            for other in node_segs[key]:
                if other != index:
                    yield other

    def near_label(segment: tuple) -> bool:
        return any(
            math.hypot(x - lx, y - ly) <= MAX_LABEL_DIST
            for x, y in ((segment[0], segment[1]), (segment[2], segment[3]))
        )

    visited: set[int] = set()
    component: list[tuple] = []
    queue: deque[int] = deque(seeds)
    while queue:
        index = queue.popleft()
        if index in visited:
            continue
        segment = segments[index]
        if not near_label(segment):
            continue
        visited.add(index)
        component.append(segment)
        for neighbor in neighbors(index):
            if neighbor not in visited:
                queue.append(neighbor)

    xs = [value for segment in component for value in (segment[0], segment[2])]
    ys = [value for segment in component for value in (segment[1], segment[3])]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    print(mark, "comp", len(component), "bbox", bbox)

    hits: list[str] = []
    for entity in msp.query("TEXT MTEXT DIMENSION"):
        if entity.dxftype() == "DIMENSION":
            point = entity.dxf.text_midpoint
            raw = entity.dxf.text
        elif entity.dxftype() == "MTEXT":
            point = entity.dxf.insert
            raw = entity.text
        else:
            point = entity.dxf.insert
            raw = entity.dxf.text
        x, y = point.x, point.y
        if (
            bbox[0] - TEXT_PAD <= x <= bbox[2] + TEXT_PAD
            and bbox[1] - TEXT_PAD <= y <= bbox[3] + TEXT_PAD
        ):
            text = normalize_drawing_text(str(raw))
            text = re.sub(r"\\A\d+;", "", text)
            if text and not re.match(r"^B\d+\(", text, re.I):
                hits.append(text)

    for text in sorted(set(hits)):
        print(" ", text, hits.count(text))


if __name__ == "__main__":
    run((6431.97, 19559.89), "B1")
    run((16292.83, 19801.88), "B2")
    run((21373.11, 19598.32), "B3")
