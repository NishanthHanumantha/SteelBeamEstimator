#!/bin/bash
set -euo pipefail
cd /opt/steel-beam-estimation/SteelBeamEstimator/Version10/webapp
if [ ! -x .venv/bin/python ]; then
  python3.12 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r ../requirements.txt
.venv/bin/pip install -r requirements.txt
echo PIP_OK
.venv/bin/python <<'PY'
import flask, werkzeug, gunicorn, ezdxf, pandas, numpy, openpyxl, shapely, pydantic, yaml, matplotlib, PIL, cv2
print(
    "IMPORT_OK",
    flask.__version__,
    gunicorn.__version__,
    ezdxf.__version__,
    numpy.__version__,
    cv2.__version__,
)
PY
