"""
dataset_validator.py — Validate the generated vision dataset for completeness.

Checks performed:
  ✓ Every beam in the registry has a beam crop image.
  ✓ Every beam image has a corresponding annotation JSON.
  ✓ Every annotation JSON references a valid beam ID from the registry.
  ✓ No duplicate beam IDs across annotation JSON files.
  ✓ No orphan annotations (annotations without an annotation_id).
  ✓ No missing metadata files.
  ✓ Image files are non-empty (size > 0 bytes).

Produces dataset_validation.json with full pass / fail report.

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

MODEL_VERSION  = "9.0.0"
SCHEMA_VERSION = "M.1.0"


def validate_dataset(
    dataset_root: Path,
    beam_ids:     List[str],
) -> Dict[str, Any]:
    """
    Validate all artefacts under *dataset_root* against the expected *beam_ids*.

    Parameters
    ----------
    dataset_root : root of the vision dataset run directory.
    beam_ids     : list of beam IDs expected from the pipeline.

    Returns
    -------
    dict ready to be written as dataset_validation.json.
    """
    images_dir  = dataset_root / "images"
    anns_dir    = dataset_root / "annotations"
    meta_dir    = dataset_root / "metadata"

    errors:   List[str] = []
    warnings: List[str] = []

    # ── Collect what exists on disk ───────────────────────────────────────────
    def _stems(directory: Path, pattern: str, strip: str = "") -> Set[str]:
        if not directory.exists():
            return set()
        return {
            p.stem.replace(strip, "")
            for p in directory.glob(pattern)
        }

    existing_images = {
        p.stem.replace("Beam_", "")
        for p in images_dir.glob("Beam_*.png")
        if "_preview" not in p.stem
    } if images_dir.exists() else set()

    existing_anns = {
        p.stem.replace("Beam_", "")
        for p in anns_dir.glob("Beam_*.json")
    } if anns_dir.exists() else set()

    existing_meta = {
        p.stem.replace("Beam_", "").replace("_meta", "")
        for p in meta_dir.glob("Beam_*_meta.json")
    } if meta_dir.exists() else set()

    expected: Set[str] = set(beam_ids)

    # ── Check 1: every expected beam has an image ─────────────────────────────
    for bid in sorted(expected - existing_images):
        errors.append(f"MISSING_IMAGE | Beam_{bid}.png not found in images/")

    # ── Check 2: every image has a JSON ──────────────────────────────────────
    for bid in sorted(existing_images - existing_anns):
        errors.append(
            f"MISSING_ANNOTATION_JSON | Beam_{bid}.json not found "
            f"but Beam_{bid}.png exists"
        )

    # ── Check 3: every JSON references a valid beam ───────────────────────────
    for bid in sorted(existing_anns - expected):
        warnings.append(
            f"ORPHAN_ANNOTATION_JSON | Beam_{bid}.json has no "
            f"matching beam in registry"
        )

    # ── Check 4: no duplicate beam IDs ───────────────────────────────────────
    beam_id_counts: Dict[str, int] = {}
    orphan_ann_count = 0

    for ann_file in sorted(anns_dir.glob("Beam_*.json")) if anns_dir.exists() else []:
        try:
            data = json.loads(ann_file.read_text(encoding="utf-8"))
            bid  = str(data.get("beam_id") or "")
            beam_id_counts[bid] = beam_id_counts.get(bid, 0) + 1

            # ── Check 5: orphan annotations (no annotation_id) ────────────────
            for ann in data.get("annotations") or []:
                if not ann.get("annotation_id"):
                    orphan_ann_count += 1
        except Exception as exc:
            warnings.append(f"JSON_PARSE_ERROR | {ann_file.name}: {exc}")

    for bid, count in sorted(beam_id_counts.items()):
        if count > 1:
            errors.append(f"DUPLICATE_BEAM_ID | {bid} appears {count} times")

    if orphan_ann_count:
        warnings.append(
            f"ORPHAN_ANNOTATIONS | {orphan_ann_count} annotation(s) "
            f"missing annotation_id"
        )

    # ── Check 6: missing metadata ─────────────────────────────────────────────
    for bid in sorted(existing_images - existing_meta):
        warnings.append(
            f"MISSING_METADATA | Beam_{bid}_meta.json not found in metadata/"
        )

    # ── Check 7: empty image files ────────────────────────────────────────────
    if images_dir.exists():
        for img_path in sorted(images_dir.glob("Beam_*.png")):
            if "_preview" not in img_path.stem and img_path.stat().st_size == 0:
                errors.append(f"EMPTY_IMAGE | {img_path.name} has 0 bytes")

    # ── Result ────────────────────────────────────────────────────────────────
    status = "PASS" if not errors else "FAIL"

    return {
        "schema_version":      SCHEMA_VERSION,
        "model_version":       MODEL_VERSION,
        "validation_timestamp": datetime.now(timezone.utc).isoformat(),
        "validation_status":   status,
        "beams_expected":      len(expected),
        "images_found":        len(existing_images),
        "annotations_found":   len(existing_anns),
        "metadata_found":      len(existing_meta),
        "error_count":         len(errors),
        "warning_count":       len(warnings),
        "errors":              errors,
        "warnings":            warnings,
    }
