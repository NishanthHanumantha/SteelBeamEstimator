# Steel Beam Estimator — Version 5

**FROZEN** at Phase J.2.1 (5.28.1). Do not modify.

Active development continues in **Version6/**.

## Historical status

Version 5 continued from **Version 4** through Phase J.2.1 — recovery integration, expansion, and statistics validation.

| Phase | Version | Package |
|-------|---------|---------|
| J.1 | 5.26.0 | `engineering_recovery` |
| J.1.1 | 5.26.1 | `engineering_recovery_validation` |
| J.1.2 | 5.26.2 | `engineering_quantity_validation` |
| J.1.3 | 5.27.0 | `engineering_calculation_integration` |
| J.2 | 5.28.0 | `engineering_recovery_expansion` |
| J.2.1 | 5.28.1 | `recovery_statistics_validation` |

## Setup (archival reference only)

```powershell
pip install -r requirements.txt
cd Version5
$env:PYTHONPATH="."
```

## Run core pipeline

```powershell
python Run_PY/run_phase_e_general_notes.py
python Run_PY/run_phase_f_framing.py
```
