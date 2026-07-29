"""
Phase V.ROOT.1 -- drawing_manifest_builder.py
Discover all DXF files in an input folder and build a drawing manifest.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import pathlib
from datetime import datetime
from typing import Any, Dict, List

from drawing_classifier import DrawingClassifier


class DrawingManifestBuilder:
    """
    Recursively find all DXF files in a folder, classify them,
    and return a structured manifest.
    """

    def __init__(self) -> None:
        self._classifier = DrawingClassifier()

    def build(self, source_folder: pathlib.Path) -> Dict[str, Any]:
        source_folder = source_folder.resolve()
        dxf_files: List[pathlib.Path] = []

        for ext in ('*.dxf', '*.DXF'):
            dxf_files.extend(source_folder.rglob(ext))

        dxf_files = sorted(set(dxf_files), key=lambda p: p.name)

        classified: Dict[str, str] = self._classifier.classify_all(dxf_files)

        drawings: List[Dict[str, Any]] = []
        for path in dxf_files:
            rel  = path.relative_to(source_folder)
            dtype = classified.get(str(path), 'UNKNOWN')
            drawings.append({
                'drawing_id':   f"DRW::{dtype[:3]}::{path.stem[:32].upper()}",
                'filename':     path.name,
                'stem':         path.stem,
                'relative_path': str(rel),
                'absolute_path': str(path),
                'drawing_type': dtype,
                'size_bytes':   path.stat().st_size if path.exists() else 0,
                'parent_folder': path.parent.name,
            })

        primary_reinf = self._classifier.primary_reinforcement_drawing(classified)
        primary_frame = self._classifier.primary_framing_drawing(classified)

        type_counts: Dict[str, int] = {}
        for d in drawings:
            type_counts[d['drawing_type']] = type_counts.get(d['drawing_type'], 0) + 1

        return {
            'source_folder': str(source_folder),
            'generated_at':  datetime.now().isoformat(),
            'total_drawings': len(drawings),
            'type_counts':   type_counts,
            'primary_reinforcement_drawing': str(primary_reinf) if primary_reinf else None,
            'primary_framing_drawing': str(primary_frame) if primary_frame else None,
            'has_reinforcement_drawing': primary_reinf is not None,
            'has_framing_drawing': primary_frame is not None,
            'drawings':      drawings,
        }
