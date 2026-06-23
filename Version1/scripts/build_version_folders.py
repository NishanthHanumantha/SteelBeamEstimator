"""Create Version1 (full snapshot) and Version2 (minimal runtime) folders."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "Version1"
V2 = ROOT / "Version2"

SKIP_DIRS = {
    "Version1",
    "Version2",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "node_modules",
}

SKIP_SUFFIXES = {".pyc", ".pyo"}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    for item in src.rglob("*"):
        if should_skip(item.relative_to(src)):
            continue
        if item.suffix in SKIP_SUFFIXES:
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def build_version1() -> int:
    copy_tree(ROOT, V1)
    return sum(1 for _ in V1.rglob("*") if _.is_file())


def build_version2() -> int:
    if V2.exists():
        shutil.rmtree(V2)
    V2.mkdir(parents=True, exist_ok=True)

    runtime_files = [
        "requirements.txt",
        "main.py",
        "extract_beam_labels.py",
        "detect_drawing_regions.py",
        "extract_reinforcement_details.py",
        ".gitignore",
    ]
    for name in runtime_files:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, V2 / name)

    shutil.copytree(ROOT / "src", V2 / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    dfx_dir = V2 / "data" / "dfx"
    dfx_dir.mkdir(parents=True, exist_ok=True)
    sample = ROOT / "data" / "dfx" / "SteelBeam_Galera_STR&OHT_Top.dxf"
    if sample.exists():
        shutil.copy2(sample, dfx_dir / sample.name)

    out_dir = V2 / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitkeep").write_text("", encoding="utf-8")

    readme = V2 / "README.md"
    readme.write_text(
        """# Steel Beam Estimator — Version 2 (Runtime)

Minimal package to run the Phase 3B reinforcement detail pipeline.

## Setup

```bash
pip install -r requirements.txt
```

## Run (from this folder)

```powershell
$env:PYTHONPATH="."
.\\run_pipeline.ps1
```

Or step by step:

```powershell
$env:PYTHONPATH="."
python main.py "data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf"
python extract_beam_labels.py
python detect_drawing_regions.py
python extract_reinforcement_details.py
```

## Included

- CLI entry points: `main.py`, `extract_beam_labels.py`, `detect_drawing_regions.py`, `extract_reinforcement_details.py`
- Full `src/` Python package (parser, extractor, geometry, regions, utils)
- Sample input DXF under `data/dfx/`
- Empty `data/output/` for generated JSON

## Not included (see Version1)

- Debug scripts, docs, prompts, legacy outputs, extra sample DXF files
""",
        encoding="utf-8",
    )

    run_script = V2 / "run_pipeline.ps1"
    run_script.write_text(
        """# Run the full Steel Beam Estimator pipeline (Version 2)
$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "."

$dxf = "data/dfx/SteelBeam_Galera_STR&OHT_Top.dxf"

python main.py $dxf
python extract_beam_labels.py
python detect_drawing_regions.py
python extract_reinforcement_details.py
""",
        encoding="utf-8",
    )

    manifest = sorted(p.relative_to(V2).as_posix() for p in V2.rglob("*") if p.is_file())
    (V2 / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    return sum(1 for _ in V2.rglob("*") if _.is_file())


def main() -> None:
    v1_count = build_version1()
    v1_readme = V1 / "VERSION_INFO.md"
    v1_readme.write_text(
        f"""# Steel Beam Estimator — Version 1 (Full Snapshot)

Frozen copy of the complete workspace at build time.

Contains source code, scripts, docs, prompts, sample data, and generated outputs.

**File count:** {v1_count}

Use **Version2** for a minimal runtime-only deployment.
""",
        encoding="utf-8",
    )

    v2_count = build_version2()
    print(f"Version1: {v1_count} files (+ VERSION_INFO.md)")
    print(f"Version2: {v2_count} files")


if __name__ == "__main__":
    main()
