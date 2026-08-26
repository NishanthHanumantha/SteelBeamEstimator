"""Build a W.11 reliability tarball. No .env, no caches, no web_runs."""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w11_runtime.tar.gz")

FILES = [
    "src/PhaseW11_hybrid_reliability/__init__.py",
    "src/PhaseW11_hybrid_reliability/bounded.py",
    "src/PhaseW11_hybrid_reliability/config.py",
    "src/PhaseW11_hybrid_reliability/progress.py",
    "src/llm/claude_client.py",
    "src/PhaseP253_claude_vision_interpretation_pilot/claude_vision_client.py",
    "src/PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py",
    "src/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/live_caller.py",
    "src/PhaseW5_production_hybrid_shadow/config.py",
    "src/PhaseW5_production_hybrid_shadow/settings.py",
    "src/PhaseW5_production_hybrid_shadow/live_invoke.py",
    "src/PhaseW5_production_hybrid_shadow/adapter.py",
    "src/PhaseW6_hybrid_production_authority/orchestrator.py",
    "src/PhaseW8_production_vision_evidence/package.py",
    "webapp/config.py",
    "webapp/routes.py",
    "webapp/templates/index.html",
    "webapp/static/js/app.js",
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
