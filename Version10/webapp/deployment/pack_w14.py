"""Build a W.14 telemetry tarball. No .env, no caches, no web_runs."""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w14_runtime.tar.gz")

FILES = [
    "src/PhaseW5_production_hybrid_shadow/adapter.py",
    "src/PhaseW6_hybrid_production_authority/resolution_trace.py",
    "src/PhaseW6_hybrid_production_authority/unit_tests.py",
    "webapp/config.py",
    "webapp/routes.py",
    "webapp/tests/test_w12_result_delivery.py",
    "webapp/tests/test_w13_hybrid_download.py",
    "webapp/tests/test_w5_hybrid_shadow.py",
    "webapp/tests/test_w6_hybrid_authority.py",
    "webapp/tests/test_w14_hybrid_recovery.py",
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
