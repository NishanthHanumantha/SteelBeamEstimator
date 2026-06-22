# Steel Beam Estimator

DXF extraction and structural steel beam estimation pipeline for AutoCAD drawings.

## Phases implemented

| Phase | Description | CLI |
|-------|-------------|-----|
| 1 | DXF entity extraction | `python main.py <dxf_path>` |
| 2A | Beam label extraction | `python extract_beam_labels.py` |
| 3A | Reinforcement block detection (nearest-neighbour) | `python extract_reinforcement_blocks.py` |
| 3A.5 | Drawing region detection | `python detect_drawing_regions.py` |
| 3B | Region-based reinforcement details | `python extract_reinforcement_details.py` |

## Setup

```bash
pip install -r requirements.txt
```

## Pipeline

```bash
python main.py "data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf"
python extract_beam_labels.py
python detect_drawing_regions.py
python extract_reinforcement_details.py
```

## Output

Generated under `data/output/`:

- `entities.json` — raw extracted DXF entities
- `beam_labels.json` — detected beam marks and sizes
- `reinforcement_detail_blocks.json` — per-beam GFC reinforcement texts (region-scoped)
- `drawing_regions.json`, `entity_region_map.json` — sheet region understanding

## Docs

See `docs/Project_FRD.txt` and `docs/Requirement_Rules.txt`.
