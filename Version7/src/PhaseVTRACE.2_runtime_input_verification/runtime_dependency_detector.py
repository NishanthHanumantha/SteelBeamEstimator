"""
runtime_dependency_detector.py — Finds all hardcoded paths and dependencies in L.2 source.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
import pathlib
import re
from typing import Dict, List


WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")

_HARDCODE_PATTERNS = [
    (re.compile(r'["\'].*Version5.*["\']'),        "HARDCODED_V5_PATH"),
    (re.compile(r'["\'].*Version6.*["\']'),        "HARDCODED_V6_PATH"),
    (re.compile(r'["\'].*Benchmark.Set.1.*["\']', re.I), "HARDCODED_BENCH1"),
    (re.compile(r'["\'].*Benchmark.Set.2.*["\']', re.I), "HARDCODED_BENCH2"),
    (re.compile(r'\.parent\s*/'),                  "PARENT_RELATIVE_PATH"),
    (re.compile(r'"B\d+"'),                        "HARDCODED_BEAM_ID"),
    (re.compile(r"'B\d+'"),                        "HARDCODED_BEAM_ID"),
    (re.compile(r'beam_schedule_results\.json'),   "HARDCODED_FILENAME"),
    (re.compile(r'engineering_objects\.json'),     "HARDCODED_FILENAME"),
    (re.compile(r'reinforcement_objects\.json'),   "HARDCODED_FILENAME"),
]

_CRITICAL_KEYS = {"HARDCODED_V5_PATH", "HARDCODED_V6_PATH", "HARDCODED_BENCH1", "PARENT_RELATIVE_PATH"}


class RuntimeDependencyDetector:

    def scan_l2_source(self, l2_src_dir: pathlib.Path) -> dict:
        findings: List[dict] = []

        for py_file in sorted(l2_src_dir.glob("*.py")):
            try:
                lines = py_file.read_text("utf-8").splitlines()
            except Exception:
                continue

            for lineno, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern, category in _HARDCODE_PATTERNS:
                    if pattern.search(line):
                        findings.append({
                            "file":     py_file.name,
                            "line":     lineno,
                            "category": category,
                            "snippet":  stripped[:120],
                            "critical": category in _CRITICAL_KEYS,
                        })

        critical = [f for f in findings if f["critical"]]
        non_critical = [f for f in findings if not f["critical"]]

        return {
            "total_findings":    len(findings),
            "critical_findings": len(critical),
            "critical":          critical,
            "non_critical":      non_critical,
            "summary": (
                f"{len(critical)} critical hardcoded dependency/path reference(s) found "
                f"in L.2 source files."
                if critical
                else "No critical hardcoded path dependencies found in L.2 source."
            ),
        }
