# Steel Beam Estimator

Structural steel beam extraction pipeline from AutoCAD DXF drawings.

## Repository layout

| Folder | Purpose |
|--------|---------|
| **Version1/** | Frozen archive — Phase 3B and earlier |
| **Version2/** | Frozen — Phases A through C.5.2 |
| **Version3/** | Frozen — intermediate development |
| **Version4/** | Frozen — through Phase G.5.3.4 |
| **Version5/** | Frozen — through Phase J.2.1 (5.28.1) |
| **Version6/** | **Active development** — model improvement |

All new work happens in **Version6/**.

## Version 6 — quick start

```powershell
cd Version6
pip install -r requirements.txt
$env:PYTHONPATH="."
python Run_PY/run_phase_e_general_notes.py
python Run_PY/run_phase_f_framing.py
```

See `Version6/README.md` for QA/recovery runners and full pipeline status.

### Inputs

- `Version6/data/framing/Beam_FramingPlan.dxf`
- `Version6/data/framing/Beam_Reinforcement_Details.dxf`
- `Version6/data/general_notes/SE-100-R0-SH-01&SH-02(GENERAL NOTES).dxf`

### Outputs

Pipeline JSON and exports are written to `Version6/data/output/` (regenerated on each run).
