"""Build a W.7 runtime tarball. No .env, no caches, no web_runs."""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w7_runtime.tar.gz")

FILES = [
    "src/PhaseW6_hybrid_production_authority/__init__.py",
    "src/PhaseW6_hybrid_production_authority/__main__.py",
    "src/PhaseW6_hybrid_production_authority/config.py",
    "src/PhaseW6_hybrid_production_authority/coverage.py",
    "src/PhaseW6_hybrid_production_authority/handoff.py",
    "src/PhaseW6_hybrid_production_authority/observability.py",
    "src/PhaseW6_hybrid_production_authority/orchestrator.py",
    "src/PhaseW6_hybrid_production_authority/visuals.py",
    "Run_PY/run_phase_w6_hybrid_production_authority.py",
    "src/PhaseW5_production_hybrid_shadow/adapter.py",
    "src/PhaseW5_production_hybrid_shadow/catalog.py",
    "src/PhaseW5_production_hybrid_shadow/comparison.py",
    "src/PhaseW5_production_hybrid_shadow/config.py",
    "src/PhaseW5_production_hybrid_shadow/cost.py",
    "src/PhaseW5_production_hybrid_shadow/live_invoke.py",
    "src/PhaseW5_production_hybrid_shadow/paths.py",
    "src/PhaseW5_production_hybrid_shadow/semantic.py",
    "src/PhaseW5_production_hybrid_shadow/settings.py",
    "src/PhaseW5_production_hybrid_shadow/visual_sources.py",
    "src/PhaseW5_production_hybrid_shadow/__init__.py",
    "src/PhaseW5_production_hybrid_shadow/__main__.py",
    "webapp/config.py",
    "webapp/routes.py",
    "webapp/services/estimation_service.py",
    "webapp/services/version10_adapter.py",
    "webapp/services/hybrid_shadow_service.py",
    "src/config/run_context.py",
    "webapp/deployment/steel-beam-estimator-v10.service",
    "webapp/deployment/steel-beam-estimator-v10.env.example",
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
