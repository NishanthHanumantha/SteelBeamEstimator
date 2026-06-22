"""Probe DXF geometry near beam labels for tuning."""

import json
from collections import defaultdict
from pathlib import Path

from ezdxf import recover

ROOT = Path(__file__).resolve().parents[1]
DXF = ROOT / "data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf"
LABELS = ROOT / "data/output/beam_labels.json"
ENTITIES = ROOT / "data/output/entities.json"

GEO_LAYERS = {
    "-STR-BEAM",
    "-STR-REINF",
    "-STR-COLUMN",
    "-S-DIM",
    "-STR-RF-DIM",
    "SEC TEXT",
}


def main() -> None:
    doc, _ = recover.readfile(str(DXF))
    msp = doc.modelspace()
    labels = json.loads(LABELS.read_text(encoding="utf-8"))

    for mark in ("B1", "B2", "B3"):
        label = next(item for item in labels if item["beam_mark"] == mark)
        lx, ly = label["x"], label["y"]
        print(f"\n=== {mark} at ({lx:.0f}, {ly:.0f}) ===")

        print("LWPOLYLINE candidates:")
        for entity in msp.query("LWPOLYLINE"):
            if entity.dxf.layer not in GEO_LAYERS:
                continue
            points = list(entity.get_points("xy"))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            xmin, ymin, xmax, ymax = min(xs), min(ys), max(xs), max(ys)
            if abs((xmin + xmax) / 2 - lx) > 3000:
                continue
            if ymax > ly + 500:
                continue
            print(
                f"  h={entity.dxf.handle} layer={entity.dxf.layer} "
                f"bbox=({xmin:.0f},{ymin:.0f},{xmax:.0f},{ymax:.0f}) "
                f"w={xmax - xmin:.0f} h={ymax - ymin:.0f}"
            )

    entities = json.loads(ENTITIES.read_text(encoding="utf-8"))["entities"]
    print("\nAll 499 dimensions:")
    for ent in entities:
        if ent.get("entity_type") != "DIMENSION":
            continue
        text = str(ent.get("clean_text", ""))
        if "499" in text:
            print(f"  ({ent['x']:.0f},{ent['y']:.0f}) {text[:30]}")

    print("\nDimensions near B2 (15500-17500 x, 16500-21500 y):")
    for ent in entities:
        if ent.get("entity_type") != "DIMENSION":
            continue
        x, y = ent["x"], ent["y"]
        if 15500 < x < 17500 and 16500 < y < 21500:
            print(f"  ({x:.0f},{y:.0f}) {str(ent.get('clean_text', ''))[:40]}")

    expected = {
        "B1": ["2-Y16", "2-Y20", "1900", "Ld", "2L-Y10", "4-Y8"],
        "B2": ["2-Y16", "2-Y20", "2-Y12", "500", "2L-Y8"],
    }
    for mark, needles in expected.items():
        label = next(item for item in labels if item["beam_mark"] == mark)
        lx, ly = label["x"], label["y"]
        print(f"\n=== {mark} expected texts ===")
        for needle in needles:
            hits = []
            for ent in entities:
                if ent.get("entity_type") not in {"TEXT", "MTEXT", "DIMENSION"}:
                    continue
                text = str(ent.get("clean_text", ""))
                if needle.lower() in text.lower():
                    hits.append((text, ent["x"], ent["y"]))
            print(f"  {needle}: {len(hits)} hits")
            for text, x, y in hits[:8]:
                print(f"    ({x:.0f},{y:.0f}) {text}")


if __name__ == "__main__":
    main()
