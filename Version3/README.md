# Steel Beam Estimator — Version 3

Focused fork for **Beam Group Detection** and **Shared Annotation Ownership** (Phase D.3).

Version 2 remains frozen as the stable production fallback. All new development happens here.

## Setup

```powershell
pip install -r requirements.txt
cd Version3
$env:PYTHONPATH="."
```

## Phase D.3 — Beam Group Detection

```powershell
python run_phase_d3_beam_group_detection.py
```

**Inputs:** `data/input/` (Version2 JSON snapshots)  
**Outputs:** `data/output/phase_d3/`

| Output | Description |
|--------|-------------|
| `beam_groups.json` | Detected beam groups with geometry |
| `shared_annotations.json` | SINGLE vs GROUP ownership classification |
| `expanded_group_annotations.json` | Per-beam expanded annotations |
| `beam_group_debug.dxf` | Visual debug on layer `DEBUG_BEAM_GROUPS` |

## Architecture

```
Header → Occurrence → Sketch → BEAM GROUP → Engineering Annotation → Beam-wise Expansion
```

## Folder structure

```
Version3/
├── data/input/          # Version2 reference JSON (read-only copy)
├── data/output/phase_d3/
├── src/grouping/        # Phase D.3 modules
├── src/debug/           # Debug DXF exporters
└── run_phase_d3_beam_group_detection.py
```
