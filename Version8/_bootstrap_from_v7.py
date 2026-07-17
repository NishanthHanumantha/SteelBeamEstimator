"""
Bootstrap Version8 from frozen Version8.

Copies only the active production / engineering spine — no phase outputs,
no forensic one-off packages, no duplicate scratch files.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
V7 = ROOT / "Version8"
V8 = ROOT / "Version8"

# Shared libraries (non-phase)
SHARED_SRC = [
    "ai",
    "config",
    "engineering_geometry",
    "engineering_specifications",
    "extractor",
    "llm",
    "parser",
    "project",
    "property_graph",
    "property_parser",
    "property_resolver",
    "reinforcement",
    "reinforcement_calculation",
    "services",
    "utils",
]

# Active production + next-phase engineering packages only
PHASE_SRC = [
    "PhaseVROOT.1_dynamic_pipeline_initialization",
    "PhaseR.1_generalized_reinforcement_discovery",
    "PhaseR1_1A_annotation_coverage",
    "PhaseR1_1B_production_integration",
    "PhaseR1_2A_geometry_accuracy",
    "PhaseR1.3_pipeline_integration",
    "PhaseR1.4_integrity_validation",
    "PhaseR.2A_engineering_context",
    "PhaseR.2B_engineering_context_consumption",
    "PhaseR3_geometry_context_engine",
    "PhaseR3.1_engineering_relationship_engine",
    "PhaseSI.0_stirrup_recovery",
    "PhaseSI.1_stirrup_improvement",
    "PhaseL.2 - engineering_reinforcement_interpretation",  # fallback only
    "PhaseVB.1_production_output_completion",
    "PhaseVRUN.1_pipeline_reexecution",
    "PhaseVTEST3_benchmark_set3_validation",
    "PhaseVTEST3_2_estimator_comparison_engine",
    "PhaseVA.2_benchmark_set2_validation",
]

# Runners matching included packages (+ bootstrap helper)
RUNNERS = [
    "_bootstrap.py",
    "run_phase_vroot1_dynamic_pipeline_initialization.py",
    "run_phase_vroot1_verify.py",
    "run_phase_r1_generalized_reinforcement_discovery.py",
    "run_phase_r11a_annotation_coverage.py",
    "run_phase_r11b_production_integration.py",
    "run_phase_r12a_geometry_accuracy.py",
    "run_phase_r13_pipeline_integration.py",
    "run_phase_r14_integrity_validation.py",
    "run_phase_r2a_engineering_context.py",
    "run_phase_r2b_engineering_context_consumption.py",
    "run_phase_r3_geometry_context_engine.py",
    "run_phase_r31_engineering_relationship_engine.py",
    "run_phase_si0_stirrup_recovery.py",
    "run_phase_si1_stirrup_improvement.py",
    "run_phase_l2_engineering_reinforcement_interpretation.py",
    "run_phase_vb1_production_output_completion.py",
    "run_phase_vrun1_pipeline_reexecution.py",
    "run_phase_vtest3_benchmark_set3_validation.py",
    "run_phase_vtest32_estimator_comparison_engine.py",
    "run_phase_va2_benchmark_set2_validation.py",
]

DATA_INPUT_DIRS = [
    "Benchmark_Set_2",
    "Benchmark_Set_3",
    "framing",
    "general_notes",
    "Excel_Presentation_Format",
]

SKIP_DIR_NAMES = {"__pycache__", ".pytest_cache", ".git", "Archive"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".log", ".bak"}
SKIP_NAME_PREFIXES = ("~$", "run_", "_probe", "_patch", "_generate")


def _should_skip(path: pathlib.Path) -> bool:
    name = path.name
    if name in SKIP_DIR_NAMES:
        return True
    if name.startswith(SKIP_NAME_PREFIXES):
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return False


def copy_tree(src: pathlib.Path, dst: pathlib.Path) -> int:
    if not src.exists():
        print(f"  SKIP missing: {src}")
        return 0
    count = 0
    for item in src.rglob("*"):
        if any(p.name in SKIP_DIR_NAMES for p in item.parents):
            continue
        if item.is_dir():
            continue
        if _should_skip(item):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        count += 1
    return count


def rewrite_version_paths(root: pathlib.Path) -> int:
    """Replace Version8 path literals with Version8 in text sources."""
    exts = {".py", ".yaml", ".yml", ".md", ".txt", ".json"}
    n = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        if "data" in path.parts and "Benchmark" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if "Version8" not in text:
            continue
        new = text.replace("Version8", "Version8")
        # Keep historical references in freeze notes
        if path.name in {"VERSION_FREEZE.md"}:
            continue
        path.write_text(new, encoding="utf-8")
        n += 1
    return n


def main() -> int:
    if not V7.exists():
        print("Version8 not found")
        return 1

    print(f"Bootstrapping {V8} from {V7}")
    V8.mkdir(parents=True, exist_ok=True)

    # Top-level files
    for name in ("requirements.txt", ".gitignore"):
        src = V7 / name
        if src.exists():
            shutil.copy2(src, V8 / name)
            print(f"  + {name}")

    # config / schemas / prompts
    for folder in ("config", "schemas", "prompts"):
        n = copy_tree(V7 / folder, V8 / folder)
        print(f"  + {folder}/ ({n} files)")

    # shared src
    total = 0
    for name in SHARED_SRC:
        n = copy_tree(V7 / "src" / name, V8 / "src" / name)
        total += n
        print(f"  + src/{name}/ ({n})")
    print(f"  shared src files: {total}")

    # phase src
    total = 0
    for name in PHASE_SRC:
        n = copy_tree(V7 / "src" / name, V8 / "src" / name)
        total += n
        print(f"  + src/{name}/ ({n})")
    print(f"  phase src files: {total}")

    # runners
    (V8 / "Run_PY").mkdir(parents=True, exist_ok=True)
    for name in RUNNERS:
        src = V7 / "Run_PY" / name
        if src.exists():
            shutil.copy2(src, V8 / "Run_PY" / name)
            print(f"  + Run_PY/{name}")
        else:
            print(f"  ! missing runner {name}")

    # input data only
    for name in DATA_INPUT_DIRS:
        n = copy_tree(V7 / "data" / name, V8 / "data" / name)
        print(f"  + data/{name}/ ({n})")

    # empty output placeholder
    out = V8 / "data" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / ".gitkeep").write_text("", encoding="utf-8")
    print("  + data/output/.gitkeep (outputs not copied — regenerate)")

    # rewrite Version8 -> Version8 in copied sources
    rewritten = rewrite_version_paths(V8)
    print(f"  rewrote Version8->Version8 in {rewritten} text files")

    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
