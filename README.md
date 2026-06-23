# Steel Beam Estimator

Structural steel beam extraction pipeline from AutoCAD DXF drawings.

## Repository layout

| Folder | Purpose |
|--------|---------|
| **Version1/** | Frozen archive — Phase 3B and earlier (do not modify) |
| **Version2/** | Active development — Phases A through C.5.2 (pre-Phase D) |

All new work happens in **Version2/**.

## Version 2 — current status

Phases completed through **C.5.2** (sketch ownership validation + audit):

- **Phase A** — Framing plan beam extraction (18 beams)
- **Phase B** — Reinforcement header extraction (24 occurrences)
- **Phase C** — Header grid / beam cells
- **Sketch debug** — 38 reinforcement sketches detected
- **Phase C.5** — Sketch-to-header occurrence ownership (PASS)
- **Phase C.5.2** — Audit metrics and warnings (ownership PASS, audit PASS_WITH_WARNINGS)

### Quick start (Version2)

```powershell
cd Version2
pip install -r requirements.txt
$env:PYTHONPATH="."
python docs/run_phases_abc.py
python run_beam_sketches_debug.py
python run_sketch_ownership.py
```

### Documentation

- Workflow guide: `Version2/docs/Version2_Workflow.pdf`
- Markdown source: `Version2/docs/Version2_Workflow.md`

### Inputs

- `Version2/data/framing/Beam_FramingPlan.dxf`
- `Version2/data/reinforcement/Beam_ReinforcementDetails.dxf`

### Outputs

Pipeline JSON and debug DXF files are written to `Version2/data/output/`.

## Version 1

See `Version1/README.md` and `Version1/VERSION_INFO.md` for the legacy Phase 3B pipeline.
