"""
runtime_version_detector.py — Classifies every loaded file by version (V5/V6/V7).
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
from typing import Dict, List
from .runtime_models import RuntimeFile


class RuntimeVersionDetector:

    def detect(self, files: Dict[str, RuntimeFile]) -> dict:
        by_version: Dict[str, List[str]] = {"Version5": [], "Version6": [], "Version7": [], "UNKNOWN": []}
        for key, rf in files.items():
            v = rf.version or "UNKNOWN"
            by_version.setdefault(v, []).append(key)

        return {
            "version_distribution": {v: len(ks) for v, ks in by_version.items()},
            "files_by_version": by_version,
            "dominant_version": max(by_version.items(), key=lambda x: len(x[1]))[0],
            "l2_reads_from_version5": len(by_version.get("Version5", [])) > 0,
            "v5_files": by_version.get("Version5", []),
            "note": (
                "All primary input files are read from Version5/data/output (V5 adapter layer). "
                "This is the expected design for backward compatibility."
            ),
        }
