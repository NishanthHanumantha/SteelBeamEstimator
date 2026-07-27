# Active model slot

This directory is the **only** application package path used by deployment.

## Phase D.2

Application framework is ready:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# set STEEL_ENGINE_ROOT in .env
python run.py
```

Do not rename this folder to a version label.
