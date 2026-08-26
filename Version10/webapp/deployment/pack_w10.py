"""Build a W.10 monitoring tarball. No .env, no caches, no web_runs."""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w10_runtime.tar.gz")

FILES = [
    "src/PhaseW10_hybrid_production_monitoring/__init__.py",
    "src/PhaseW10_hybrid_production_monitoring/__main__.py",
    "src/PhaseW10_hybrid_production_monitoring/config.py",
    "src/PhaseW10_hybrid_production_monitoring/monitor.py",
    "src/PhaseW10_hybrid_production_monitoring/sanitize.py",
    "src/PhaseW10_hybrid_production_monitoring/writer.py",
    "src/PhaseW6_hybrid_production_authority/orchestrator.py",
    "webapp/config.py",
    "webapp/routes.py",
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
