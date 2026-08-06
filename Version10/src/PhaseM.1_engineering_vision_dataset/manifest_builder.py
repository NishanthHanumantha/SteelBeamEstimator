"""
manifest_builder.py — Build the dataset_manifest.json.

Aggregates per-beam results into a single summary document covering:
  - Dataset version and generation metadata
  - Beam / image / annotation counts
  - Role distribution
  - Diameter distribution
  - Image resolution
  - Future-format compatibility notes (YOLO / COCO / VOC / Vision LLM / OpenCV)

MODEL_VERSION: 9.0.0
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

MODEL_VERSION      = "9.0.0"
DATASET_VERSION    = "9.0.0"
SCHEMA_VERSION     = "M.1.0"


def build_manifest(
    run_id:         str,
    drawing_files:  List[str],
    ann_jsons:      List[Dict[str, Any]],   # one dict per beam (annotation JSON)
    metadatas:      List[Dict[str, Any]],   # one dict per beam (metadata JSON)
    full_image_size: Tuple[int, int],        # (width_px, height_px) of full DXF render
) -> Dict[str, Any]:
    """
    Aggregate all beam results into the dataset manifest.

    Parameters
    ----------
    run_id          : unique run identifier (timestamp-based).
    drawing_files   : list of DXF source file names.
    ann_jsons       : list of annotation JSON dicts (one per beam).
    metadatas       : list of metadata dicts (one per beam).
    full_image_size : pixel dimensions of the full rendered drawing.

    Returns
    -------
    dict ready to be written as dataset_manifest.json.
    """
    # ── Totals ────────────────────────────────────────────────────────────────
    beam_count  = len(ann_jsons)
    total_anns  = sum(b.get("annotation_count", 0) for b in ann_jsons)

    # ── Role distribution ─────────────────────────────────────────────────────
    role_counts: Counter = Counter()
    for b in ann_jsons:
        for ann in b.get("annotations") or []:
            role = ann.get("role") or "UNKNOWN"
            role_counts[role] += 1

    # ── Diameter distribution (across all beams) ──────────────────────────────
    all_diams: List[float] = []
    for m in metadatas:
        all_diams.extend(m.get("diameters_mm") or [])
    diam_counter = Counter(int(d) for d in all_diams if d)

    # ── Stirrups ──────────────────────────────────────────────────────────────
    stirrup_count = sum(1 for m in metadatas if m.get("stirrup_present"))

    # ── Roles found list ──────────────────────────────────────────────────────
    roles_found = [r for r in role_counts if r != "UNKNOWN"]

    # ── Crop image sizes (representative from first beam) ────────────────────
    crop_sizes = [
        m.get("image_size_pixels")
        for m in metadatas
        if m.get("image_size_pixels")
    ]
    sample_crop = crop_sizes[0] if crop_sizes else None

    return {
        "schema_version":   SCHEMA_VERSION,
        "dataset_version":  DATASET_VERSION,
        "model_version":    MODEL_VERSION,
        "generation_date":  datetime.now(timezone.utc).isoformat(),
        "run_id":           run_id,

        "drawing_files":    drawing_files,

        "beam_count":       beam_count,
        "image_count":      beam_count,
        "annotation_count": total_anns,

        "roles":            {r: c for r, c in sorted(role_counts.items())},
        "roles_found":      sorted(roles_found),

        "image_resolution": {
            "full_render": {
                "width":  full_image_size[0],
                "height": full_image_size[1],
                "format": "PNG",
                "dpi":    200,
            },
            "beam_crop_sample": sample_crop,
        },

        "statistics": {
            "beams_total":              beam_count,
            "beams_with_annotations":   sum(
                1 for b in ann_jsons if b.get("annotation_count", 0) > 0
            ),
            "beams_with_stirrups":      stirrup_count,
            "avg_annotations_per_beam": (
                round(total_anns / beam_count, 2) if beam_count else 0.0
            ),
            "diameter_distribution_mm": dict(sorted(diam_counter.items())),
            "distinct_roles":           len(roles_found),
        },

        "future_format_compatibility": {
            "note":       "Dataset schema is designed for future export to standard formats.",
            "YOLO":       "planned — Phase M.2",
            "COCO":       "planned — Phase M.2",
            "Pascal_VOC": "planned — Phase M.2",
            "Vision_LLM": "planned — Phase M.2",
            "OpenCV":     "planned — Phase M.2",
        },
    }
