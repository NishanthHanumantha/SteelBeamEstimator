"""
dataset_exporter.py — Write all dataset artefacts to the dataset root directory.

Manages the dataset directory tree and serialises JSON + image files.

Directory layout (under dataset_root):
  images/         — clean beam crop PNGs  (Beam_<ID>.png)
  annotations/    — annotation JSON files (Beam_<ID>.json)
  metadata/       — metadata JSON files   (Beam_<ID>_meta.json)
  previews/       — quality-inspection PNGs (Beam_<ID>_preview.png)
  dataset_manifest.json
  dataset_validation.json

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

MODEL_VERSION = "9.0.0"

# ── Directory names ───────────────────────────────────────────────────────────
IMAGES_DIR      = "images"
ANNOTATIONS_DIR = "annotations"
METADATA_DIR    = "metadata"
PREVIEWS_DIR    = "previews"


def create_dataset_dirs(dataset_root: Path) -> None:
    """Create the full dataset directory tree under *dataset_root*."""
    for sub in (IMAGES_DIR, ANNOTATIONS_DIR, METADATA_DIR, PREVIEWS_DIR):
        (dataset_root / sub).mkdir(parents=True, exist_ok=True)


def image_path(dataset_root: Path, beam_id: str) -> Path:
    return dataset_root / IMAGES_DIR / f"Beam_{beam_id}.png"


def annotation_path(dataset_root: Path, beam_id: str) -> Path:
    return dataset_root / ANNOTATIONS_DIR / f"Beam_{beam_id}.json"


def metadata_path(dataset_root: Path, beam_id: str) -> Path:
    return dataset_root / METADATA_DIR / f"Beam_{beam_id}_meta.json"


def preview_path(dataset_root: Path, beam_id: str) -> Path:
    return dataset_root / PREVIEWS_DIR / f"Beam_{beam_id}_preview.png"


def manifest_path(dataset_root: Path) -> Path:
    return dataset_root / "dataset_manifest.json"


def validation_path(dataset_root: Path) -> Path:
    return dataset_root / "dataset_validation.json"


def write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write *data* as prettified JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
