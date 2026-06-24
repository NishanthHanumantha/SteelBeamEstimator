"""Patch run_phase_*.py files to use OutputPaths."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPLACEMENTS = [
    (
        "run_phase_d11_annotation_audit.py",
        [
            (
                "from src.annotations.annotation_ownership_auditor import AnnotationOwnershipAuditor\nfrom src.annotations.annotation_ownership_debug_exporter import (\n    AnnotationOwnershipDebugExporter,\n)",
                "from src.annotations.annotation_ownership_auditor import AnnotationOwnershipAuditor\nfrom src.annotations.annotation_ownership_debug_exporter import (\n    AnnotationOwnershipDebugExporter,\n)\nfrom src.config.output_paths import OutputPaths, OUTPUT_ROOT",
            ),
            (
                "DEFAULT_OUTPUT_DIR = Path(\"data/output\")\nDEFAULT_ANNOTATIONS = DEFAULT_OUTPUT_DIR / \"beam_annotations_raw.json\"\nDEFAULT_SKETCHES = DEFAULT_OUTPUT_DIR / \"beam_sketches_debug.json\"\n",
                "_DEFAULT_PATHS = OutputPaths()\n",
            ),
            ("def parse_args()", "def parse_args() -> argparse.Namespace:\n    paths = OutputPaths()\n"),
            (") -> argparse.Namespace:\n    paths = OutputPaths()\n    parser", ") -> argparse.Namespace:\n    paths = OutputPaths()\n    parser"),
            ("default=DEFAULT_ANNOTATIONS", "default=paths.beam_annotations_raw"),
            ("default=DEFAULT_SKETCHES", "default=paths.beam_sketches_debug"),
            ("default=DEFAULT_OUTPUT_DIR", "default=OUTPUT_ROOT"),
            ("Output directory (default:", "Output root directory (default:"),
            ("output_dir / \"annotation_ownership_audit.json\"", "paths.annotation_ownership_audit"),
            ("output_dir / \"annotation_ownership_validation.json\"", "paths.annotation_ownership_validation"),
            ("output_dir / \"annotation_ownership_summary.txt\"", "paths.annotation_ownership_summary"),
            ("output_path=output_dir / \"annotation_ownership_debug.dxf\"", "output_path=paths.annotation_ownership_debug_dxf"),
            ("output_dir.mkdir(parents=True, exist_ok=True)\n\n    annotations", "paths = OutputPaths(output_dir)\n    paths.phase_d1_1_dir.mkdir(parents=True, exist_ok=True)\n\n    annotations"),
        ],
    ),
]

# Manual approach - use shell to run sed-like replacements for each file via Python exec

PATCHES = {
    "run_phase_d11_annotation_audit.py": {
        "import_add": "from src.config.output_paths import OutputPaths, OUTPUT_ROOT\n",
        "after_import": "from src.annotations.annotation_ownership_debug_exporter import (\n    AnnotationOwnershipDebugExporter,\n)",
        "remove_defaults": True,
        "defaults": "_DEFAULT_PATHS = OutputPaths()\n",
        "parse_paths": True,
        "replacements": {
            "DEFAULT_ANNOTATIONS": "paths.beam_annotations_raw",
            "DEFAULT_SKETCHES": "paths.beam_sketches_debug",
            "DEFAULT_OUTPUT_DIR": "OUTPUT_ROOT",
            "output_dir / \"annotation_ownership_audit.json\"": "paths.annotation_ownership_audit",
            "output_dir / \"annotation_ownership_validation.json\"": "paths.annotation_ownership_validation",
            "output_dir / \"annotation_ownership_summary.txt\"": "paths.annotation_ownership_summary",
            "output_path=output_dir / \"annotation_ownership_debug.dxf\"": "output_path=paths.annotation_ownership_debug_dxf",
        },
        "run_insert": "paths = OutputPaths(output_dir)\n    paths.phase_d1_1_dir.mkdir(parents=True, exist_ok=True)\n",
        "run_replace": "output_dir.mkdir(parents=True, exist_ok=True)\n",
    },
}

def patch_file(name: str, cfg: dict) -> None:
    path = ROOT / name
    text = path.read_text(encoding="utf-8")
    if cfg.get("import_add") and cfg["import_add"] not in text:
        anchor = cfg["after_import"]
        text = text.replace(anchor, anchor + "\n" + cfg["import_add"], 1)
    if cfg.get("remove_defaults"):
        import re
        text = re.sub(
            r"DEFAULT_OUTPUT_DIR = Path\(\"data/output\"\)\n(?:DEFAULT_[^\n]+\n)+",
            cfg["defaults"],
            text,
            count=1,
        )
    if cfg.get("parse_paths"):
        text = text.replace(
            "def parse_args() -> argparse.Namespace:\n    parser",
            "def parse_args() -> argparse.Namespace:\n    paths = OutputPaths()\n    parser",
            1,
        )
    for old, new in cfg["replacements"].items():
        text = text.replace(old, new)
    if cfg.get("run_replace") and cfg.get("run_insert"):
        text = text.replace(cfg["run_replace"], cfg["run_insert"], 1)
    path.write_text(text, encoding="utf-8")
    print(f"Patched {name}")

if __name__ == "__main__":
    for name, cfg in PATCHES.items():
        patch_file(name, cfg)
