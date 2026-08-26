"""Build a W.12 result-delivery tarball. No .env, no caches, no web_runs."""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w12_runtime.tar.gz")

FILES = [
    "webapp/config.py",
    "webapp/routes.py",
    "webapp/templates/index.html",
    "webapp/static/js/app.js",
    "webapp/static/css/app.css",
    "webapp/services/estimation_service.py",
    "webapp/services/result_registry.py",
    "webapp/deployment/steel-beam-estimator-v10.service",
]


def main() -> None:
    missing = [rel for rel in FILES if not (ENGINE / rel).is_file()]
    if missing:
        raise SystemExit("missing: " + ", ".join(missing))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(OUT, "w:gz") as tar:
        for rel in FILES:
            tar.add(ENGINE / rel, arcname="Version10/" + rel.replace("\\", "/"))
    print("FILES", len(FILES))
    print("OUT", OUT)
    print("BYTES", OUT.stat().st_size)


if __name__ == "__main__":
    main()
