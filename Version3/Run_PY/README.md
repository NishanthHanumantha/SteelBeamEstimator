# Version3 runners

All phase entry-point scripts live here. Run from anywhere:

```powershell
cd Version3
python Run_PY/run_phase_d33_annotation_ownership.py
```

Or:

```powershell
python Version3/Run_PY/run_phases_abc.py
```

`_bootstrap.py` sets the working directory to `Version3/` and adds it to `sys.path` so `src/` imports and `data/` paths resolve correctly.
