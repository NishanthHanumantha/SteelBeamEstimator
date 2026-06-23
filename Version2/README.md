# Steel Beam Estimator — Version 2 (Runtime)

Minimal package to run the Phase 3B reinforcement detail pipeline.

## Setup

```bash
pip install -r requirements.txt
```

## Run (from this folder)

```powershell
$env:PYTHONPATH="."
.\run_pipeline.ps1
```

Or step by step:

```powershell
$env:PYTHONPATH="."
python main.py "data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf"
python extract_beam_labels.py
python detect_drawing_regions.py
python extract_reinforcement_details.py
```

## Included

- CLI entry points: `main.py`, `extract_beam_labels.py`, `detect_drawing_regions.py`, `extract_reinforcement_details.py`
- Full `src/` Python package (parser, extractor, geometry, regions, utils)
- Sample input DXF under `data/dfx/`
- Empty `data/output/` for generated JSON

## Not included (see Version1)

- Debug scripts, docs, prompts, legacy outputs, extra sample DXF files
