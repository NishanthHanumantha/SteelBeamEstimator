# Steel Beam Estimator

Structural steel beam extraction pipeline from AutoCAD DXF drawings.

**Current production:** Version10 Hybrid (release **W.19.1**), entered at `Version10/webapp/wsgi.py`.  
See `PRODUCTION_TRUTH.md` before changing production behaviour.

## Repository layout

| Folder | Purpose |
|--------|---------|
| **Version1/** | Frozen archive — Phase 3B and earlier |
| **Version2/** | Frozen — Phases A through C.5.2 |
| **Version3/** | Frozen — intermediate development |
| **Version4/** | Frozen — through Phase G.5.3.4 |
| **Version5/** | Frozen — through Phase J.2.1 (5.28.1) |
| **Version6/** | Frozen historical engine — **not** current production |
| **Version10/** | **Current production** — Hybrid pipeline (14 stages, W.6 + VB.1) |

Version1–Version9 remain in-tree as historical engines. Do not treat them as the live Lightsail app.

## Version 6 — historical quick start (archive)

The commands below are the **Version6 archive** workflow, not the deployed system.

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
