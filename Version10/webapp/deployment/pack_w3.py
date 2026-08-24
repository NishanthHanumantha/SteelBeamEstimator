"""Build a Version10 Lightsail tarball excluding local artefacts (Phase W.3)."""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w3_version10_deploy.tar.gz")

SKIP_DIR_NAMES = {
    "__pycache__",
    ".venv",
    ".venv_w21",
    ".git",
    "uploads",
    "outputs",
    "logs",
}
SKIP_PREFIXES = (
    "src/PhaseP2610",
    "data/output",
    "data/web_runs",
    "webapp/uploads",
    "webapp/outputs",
    "webapp/logs",
)


def skip(rel: str) -> bool:
    posix = rel.replace("\\", "/")
    parts = set(Path(posix).parts)
    if parts & SKIP_DIR_NAMES:
        return True
    if posix.endswith(".pyc") or posix.endswith(".pyo"):
        return True
    if posix.endswith(".env"):
        return True
    for prefix in SKIP_PREFIXES:
        if posix == prefix or posix.startswith(prefix + "/"):
            return True
    return False


def main() -> None:
    files: list[Path] = []
    for path in ENGINE.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ENGINE).as_posix()
        if skip(rel):
            continue
        files.append(path)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(OUT, "w:gz") as tar:
        for path in files:
            tar.add(path, arcname="Version10/" + path.relative_to(ENGINE).as_posix())
    print("FILES", len(files))
    print("OUT", OUT, "MB", round(OUT.stat().st_size / 1048576, 2))


if __name__ == "__main__":
    main()
