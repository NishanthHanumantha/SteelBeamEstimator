"""Create Version4 from Version3 — minimal import for Phase F onward."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "Version3"
V4 = ROOT / "Version4"

# --- Source trees (relative to Version3) ---
SRC_PACKAGES = (
    "src/general_notes",
    "src/estimation",
    "src/framing",
    "src/config",
)

SRC_FILES = (
    "src/__init__.py",
    "src/parser/dxf_reader.py",
    "src/parser/dxf_flattener.py",
    "src/extractor/beam_label_extractor.py",
    "src/utils/text_cleaner.py",
    "src/utils/entities_loader.py",
)

CONFIG_FILES = (
    "config/general_notes.yaml",
    "config/estimator_rules.yaml",
)

RUN_FILES = (
    "Run_PY/run_phase_e_general_notes.py",
)

PHASE_E_OUTPUTS = (
    "general_notes_engineering_rules.json",
    "development_length_table.json",
    "cover_table.json",
    "material_specifications.json",
    "engineering_constants.json",
    "project_defaults.json",
    "project_engineering_report.json",
    "phase_e_summary.json",
    "phase_e_validation.json",
    "estimator_rules.json",
    "project_metadata.json",
    "engineering_traceability_report.json",
    "engineering_value_registry.json",
)


def copy_file(rel: str) -> None:
    src = V3 / rel
    dst = V4 / rel
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(rel: str) -> None:
    src = V3 / rel
    dst = V4 / rel
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def write_bootstrap() -> None:
    content = '''"""Ensure Version4 root is on sys.path and the working directory for runners."""

import os
import sys
from pathlib import Path

VERSION4_ROOT = Path(__file__).resolve().parents[1]


def setup() -> Path:
    os.chdir(VERSION4_ROOT)
    root_str = str(VERSION4_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return VERSION4_ROOT


setup()
'''
    path = V4 / "Run_PY" / "_bootstrap.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_minimal_inits() -> None:
    (V4 / "src" / "parser" / "__init__.py").write_text(
        '"""DXF parsing (minimal subset for framing extraction)."""\n\n'
        "from src.parser.dxf_reader import DxfReader, DxfReadError\n"
        "from src.parser.dxf_flattener import flatten_entities\n\n"
        '__all__ = ["DxfReader", "DxfReadError", "flatten_entities"]\n',
        encoding="utf-8",
    )
    (V4 / "src" / "extractor" / "__init__.py").write_text(
        '"""Beam label helpers (minimal subset)."""\n\n'
        "from src.extractor.beam_label_extractor import BEAM_LABEL_PATTERN\n\n"
        '__all__ = ["BEAM_LABEL_PATTERN"]\n',
        encoding="utf-8",
    )
    (V4 / "src" / "utils" / "__init__.py").write_text(
        '"""Shared utilities (minimal subset)."""\n\n'
        "from src.utils.entities_loader import EntitiesLoadError, load_entities_json\n"
        "from src.utils.text_cleaner import TextCleaner, clean_dxf_text\n\n"
        '__all__ = [\n'
        '    "EntitiesLoadError",\n'
        '    "load_entities_json",\n'
        '    "TextCleaner",\n'
        '    "clean_dxf_text",\n'
        "]\n",
        encoding="utf-8",
    )


def patch_output_paths() -> None:
    path = V4 / "src" / "config" / "output_paths.py"
    text = path.read_text(encoding="utf-8")
    if "PHASE_F" not in text:
        text = text.replace('PHASE_E = "phase_e"', 'PHASE_E = "phase_e"\nPHASE_F = "phase_f"')
        marker = "    # --- Phase E ---"
        phase_f_block = '''
    # --- Phase F ---
    @property
    def phase_f_dir(self) -> Path:
        return phase_dir(self.root, PHASE_F)
'''
        text = text.replace(marker, phase_f_block + "\n" + marker)
        path.write_text(text, encoding="utf-8")


def copy_data_inputs() -> None:
    for folder in ("data/general_notes", "data/framing"):
        src_dir = V3 / folder
        if src_dir.exists():
            copy_tree(folder)
            for pdf in (V4 / folder).glob("*.pdf"):
                pdf.unlink(missing_ok=True)

    out_phase_e = V4 / "data" / "output" / "phase_e"
    out_phase_e.mkdir(parents=True, exist_ok=True)
    src_phase_e = V3 / "data" / "output" / "phase_e"
    for name in PHASE_E_OUTPUTS:
        src = src_phase_e / name
        if src.exists():
            shutil.copy2(src, out_phase_e / name)

    (V4 / "data" / "output" / "phase_f").mkdir(parents=True, exist_ok=True)
    (V4 / "data" / "output" / "phase_f" / ".gitkeep").write_text("", encoding="utf-8")


def write_readme() -> None:
    readme = V4 / "README.md"
    readme.write_text(
        """# Steel Beam Estimator — Version 4

Active development branch for **Phase F (Framing Plan Intelligence)** and beyond.

**Version 3 is frozen** as the stable fallback through Phase E.3 (General Notes + provenance).

## What is included

Imported from Version3 (minimal runtime only):

| Area | Purpose |
|------|---------|
| `src/general_notes/` | Phase E engineering knowledge engine |
| `src/estimation/` | Estimator methodology config loader |
| `src/framing/` | Framing plan beam extraction (Phase A foundation) |
| `src/parser/`, `src/extractor/`, `src/utils/` | DXF + beam label support for framing |
| `config/` | General notes + estimator rules |
| `data/general_notes/` | General Notes DXF input |
| `data/framing/` | Framing plan DXF input |
| `data/output/phase_e/` | Baseline engineering knowledge JSON (from V3) |

Phase D modules, reinforcement pipeline, and debug outputs were **not** copied.

## Setup

```powershell
pip install -r requirements.txt
cd Version4
```

## Run Phase E (refresh engineering knowledge)

```powershell
python Run_PY/run_phase_e_general_notes.py
```

## Architecture

```
Phase D (Drawing Intelligence)     — in Version3 (frozen)
Phase E (General Notes)            — imported + runnable here
Phase F (Framing Plan Intelligence) — start here
Phase G (Engineering Computation)  — planned
```

Future phases consume engineering rules through `EngineeringRuleCache`, not raw JSON.

## Folder structure

```
Version4/
├── Run_PY/              # Runners (_bootstrap sets cwd to Version4)
├── config/              # YAML configuration
├── data/
│   ├── general_notes/   # GN DXF
│   ├── framing/         # Framing plan DXF
│   └── output/
│       ├── phase_e/     # Engineering knowledge baseline
│       └── phase_f/     # Phase F outputs (new)
└── src/
    ├── general_notes/
    ├── estimation/
    ├── framing/
    └── config/
```
""",
        encoding="utf-8",
    )


def freeze_version3_note() -> None:
    note = V3 / "FROZEN.md"
    if note.exists():
        return
    note.write_text(
        """# Version 3 — Frozen

Version 3 is **frozen** at Phase E.3 (Engineering Value Provenance & Traceability).

- Do not add new features here.
- Use as a stable fallback and reference.
- Continue development in **Version4/**.
""",
        encoding="utf-8",
    )


def main() -> None:
    if V4.exists():
        shutil.rmtree(V4)
    V4.mkdir(parents=True)

    shutil.copy2(V3 / "requirements.txt", V4 / "requirements.txt")

    for pkg in SRC_PACKAGES:
        copy_tree(pkg)

    for rel in SRC_FILES:
        copy_file(rel)

    for rel in CONFIG_FILES:
        copy_file(rel)

    for rel in RUN_FILES:
        copy_file(rel)

    write_bootstrap()
    write_minimal_inits()
    patch_output_paths()
    copy_data_inputs()
    write_readme()
    freeze_version3_note()

    file_count = sum(1 for _ in V4.rglob("*") if _.is_file())
    print(f"Version4 created at {V4} ({file_count} files)")


if __name__ == "__main__":
    main()
