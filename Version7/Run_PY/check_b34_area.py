"""Check annotations near B34, B35, B43 in the reinforcement DXF."""
import ezdxf, re, pathlib

dxf_path = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator\Version7\data\Benchmark_Set_2\reinforcement\Galera_GF_BeamReinforcementDetails.dxf")
doc = ezdxf.readfile(str(dxf_path))
msp = doc.modelspace()

def clean(t):
    t = re.sub(r"\\[A-Za-z][^;]*;", "", t)
    t = re.sub(r"%%[A-Za-z]", "", t)
    return t.strip()

centroids = {
    "B34": (78535.41, 29940.36),
    "B35": (80697.83, 30165.42),
    "B43": (77300.65, 26480.29),
}

for beam_id, (cx, cy) in centroids.items():
    print(f"\n=== {beam_id} centroid=({cx:.0f},{cy:.0f}) === Searching radius 8000 ===")
    nearby = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                x, y = e.dxf.insert.x, e.dxf.insert.y
            except Exception:
                continue
            dist = ((x-cx)**2 + (y-cy)**2)**0.5
            if dist < 8000:
                if e.dxftype() == "TEXT":
                    raw = e.dxf.text
                else:
                    raw = e.plain_mtext() if hasattr(e, "plain_mtext") else e.text
                nearby.append((dist, x, y, e.dxftype(), clean(raw)))
    nearby.sort()
    if not nearby:
        print("  [NO TEXT ENTITIES FOUND WITHIN 8000 UNITS]")
    for dist, x, y, typ, text in nearby[:15]:
        print(f"  dist={dist:.0f} ({x:.0f},{y:.0f}) [{typ}] {repr(text[:60])}")
