"""Debug sketch for a single beam label."""

import sys
from pathlib import Path

from ezdxf import recover

from src.geometry.geometry_graph import GeometryGraphBuilder

ROOT = Path(__file__).resolve().parents[1]
DXF = ROOT / "data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf"

LABELS = {
    "B1": (6431.973576, 19559.895594),
    "B2": (16293.0, 19802.0),  # approximate
    "B3": (21373.0, 19598.0),
}


def main() -> None:
    mark = sys.argv[1] if len(sys.argv) > 1 else "B1"
    lx, ly = LABELS[mark]
    doc, _ = recover.readfile(str(DXF))
    builder = GeometryGraphBuilder()
    sketch = builder.build_sketch(doc, lx, ly)
    if sketch is None:
        print(f"{mark}: no sketch")
        return
    print(f"{mark} seed={sketch.seed_polyline_handle}")
    print(f"bbox={sketch.bbox}")
    print(f"segments={len(sketch.segments)}")
    layers = {}
    for seg in sketch.segments:
        layers[seg[5]] = layers.get(seg[5], 0) + 1
    print("layers:", layers)


if __name__ == "__main__":
    main()
