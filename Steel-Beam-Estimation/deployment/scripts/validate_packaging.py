#!/usr/bin/env python3
"""
Phase D.3 — packaging validation (no AWS).

Run from Steel-Beam-Estimation/ or current_model/:

    python deployment/scripts/validate_packaging.py

Checks folder layout, required modules, .env guidance, and /health contract.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = PACKAGE_ROOT / "current_model"

REQUIRED_DIRS = [
    MODEL_ROOT / "webapp",
    MODEL_ROOT / "config",
    MODEL_ROOT / "templates",
    MODEL_ROOT / "static",
    MODEL_ROOT / "inputs",
    MODEL_ROOT / "outputs",
    MODEL_ROOT / "temp",
    MODEL_ROOT / "logs",
]

REQUIRED_FILES = [
    MODEL_ROOT / "run.py",
    MODEL_ROOT / "wsgi.py",
    MODEL_ROOT / "requirements.txt",
    MODEL_ROOT / ".env.example",
    MODEL_ROOT / "config" / "settings.py",
    MODEL_ROOT / "config" / "paths.py",
    MODEL_ROOT / "config" / "model_info.yaml",
    MODEL_ROOT / "webapp" / "app.py",
    MODEL_ROOT / "webapp" / "routes.py",
    MODEL_ROOT / "webapp" / "services.py",
    MODEL_ROOT / "webapp" / "logging_config.py",
    MODEL_ROOT / "templates" / "index.html",
]


def main() -> int:
    errors: list[str] = []
    print("=== Steel Beam Estimation — D.3 packaging check ===")
    print(f"package_root: {PACKAGE_ROOT}")
    print(f"current_model: {MODEL_ROOT}")

    for d in REQUIRED_DIRS:
        if not d.is_dir():
            errors.append(f"missing directory: {d.relative_to(PACKAGE_ROOT)}")
        else:
            print(f"  OK dir  {d.relative_to(PACKAGE_ROOT)}")

    for f in REQUIRED_FILES:
        if not f.is_file():
            errors.append(f"missing file: {f.relative_to(PACKAGE_ROOT)}")
        else:
            print(f"  OK file {f.relative_to(PACKAGE_ROOT)}")

    if not (MODEL_ROOT / ".env.example").is_file():
        errors.append(".env.example missing")

    # Import app and hit /health
    sys.path.insert(0, str(MODEL_ROOT))
    try:
        from webapp.app import app

        client = app.test_client()
        resp = client.get("/health")
        payload = resp.get_json() or {}
        print(f"  /health status_code={resp.status_code}")
        print(f"  /health body={json.dumps(payload, indent=2)}")
        if resp.status_code != 200:
            errors.append("/health did not return 200")
        for key in ("status", "model_version", "timestamp"):
            if key not in payload:
                errors.append(f"/health missing key: {key}")
        if payload.get("status") != "ok":
            errors.append("/health status is not ok")
    except Exception as exc:
        errors.append(f"failed to load app /health: {exc}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nPASSED — package is deployment-ready for local install.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
