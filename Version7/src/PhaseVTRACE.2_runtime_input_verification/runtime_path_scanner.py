"""
runtime_path_scanner.py — Scans every file that InterpretationCollector opens at runtime.
MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
import hashlib
import json
import pathlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .runtime_models import RuntimeFile

WORKSPACE = pathlib.Path(r"C:\Users\nishanth.h\SteelBeamEstimator")

# The EXACT path mapping from InterpretationCollector.__init__
# (mirrored here for read-only inspection — InterpretationCollector NOT called directly)
def _build_l2_input_paths(project_root: pathlib.Path) -> Dict[str, pathlib.Path]:
    v6_out = project_root / "data/output"
    v5_out = project_root.parent / "Version5/data/output"
    v5_i   = v5_out / "phase_i"
    return {
        "v5_engineering_objects":   v5_out / "phase_g/g_5_1_engineering_objects/engineering_objects.json",
        "v5_reinforcement_objects": v5_i   / "i_2_reinforcement_engine/reinforcement_objects.json",
        "v5_beam_schedule":         v5_i   / "i_15_beam_schedule/beam_schedule_results.json",
        "v5_recovery":              v5_out / "engineering_recovery/recovered_engineering_objects.json",
        "v5_general_notes":         v5_out / "phase_e/general_notes.json",
        "v5_steel_weight":          v5_i   / "i_11_steel_weight/steel_weight_results.json",
        "v5_beam_geometry":         v5_out / "phase_f/beam_geometry_model.json",
        "v5_engineering_gap":       v5_out / "engineering_analysis/engineering_gap_analysis.json",
        "l1_role_gap":              v6_out / "PhaseL.1 - accuracy_sprint_1_estimator_gap_closure/reinforcement_role_gap_analysis.json",
        "l2_audit":                 v6_out / "PhaseL.2 - engineering_rule_audit/role_audit.json",
    }


def _sha256(path: pathlib.Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "ERROR"


def _detect_version(path: pathlib.Path) -> str:
    norm = str(path).replace("\\", "/")
    if "/Version7/" in norm:   return "Version7"
    if "/Version6/" in norm:   return "Version6"
    if "/Version5/" in norm:   return "Version5"
    return "UNKNOWN"


def _detect_benchmark(data: dict) -> str:
    """Best-effort benchmark set identification from JSON content."""
    text = json.dumps(data, ensure_ascii=False).lower()
    if "galera" in text or "benchmark_set_2" in text:
        return "Benchmark_Set_2"
    if "clubhouse" in text or "benchmark_set_1" in text:
        return "Benchmark_Set_1"
    # Look for Benchmark Set 2 exclusive beam IDs
    bench2_exclusive = {"b14a", "b20a", "b29a", "b31a", "b35a", "b39a", "b48a",
                        "b25", "b26", "b27", "b38", "b45", "b50", "b51", "br1"}
    for bid in bench2_exclusive:
        if f'"{bid}"' in text or f"'{bid}'" in text:
            return "Benchmark_Set_2"
    return "UNKNOWN"


def _beam_count_and_ids(data: dict) -> tuple:
    """Extract beam count and IDs from any known artefact format."""
    for key in ("objects", "results", "beams", "models", "bars", "geometries"):
        val = data.get(key)
        if isinstance(val, list) and val:
            ids = []
            for item in val:
                if isinstance(item, dict):
                    bid = (item.get("beam_mark") or item.get("beam_id")
                           or item.get("id") or item.get("beam_id", ""))
                    if bid:
                        ids.append(str(bid))
            if ids:
                return len(ids), sorted(set(ids))
            return len(val), []
        if isinstance(val, dict):
            return len(val), sorted(val.keys())
    # Scalar count fields
    for key in ("beam_count", "object_count", "model_count", "determination_count", "bar_count"):
        if key in data:
            return int(data[key]), []
    return 0, []


def _mtime_iso(path: pathlib.Path) -> Optional[str]:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return None


class RuntimePathScanner:
    """Scans every input file the InterpretationCollector will open."""

    def __init__(self, project_root: pathlib.Path):
        self._root   = project_root
        self._paths  = _build_l2_input_paths(project_root)

    def scan_all(self) -> Dict[str, RuntimeFile]:
        files: Dict[str, RuntimeFile] = {}
        for key, path in self._paths.items():
            files[key] = self._scan_one(key, path)
        return files

    def _scan_one(self, key: str, path: pathlib.Path) -> RuntimeFile:
        exists = path.exists()
        if not exists:
            return RuntimeFile(
                key=key, absolute_path=str(path),
                relative_path=str(path.relative_to(WORKSPACE) if WORKSPACE in path.parents else path),
                exists=False, size_bytes=0, mtime_epoch=None, mtime_iso=None,
                sha256=None, version=_detect_version(path), benchmark_id=None,
                model_version=None, beam_count=0, beam_ids=[], phase_origin=None,
                load_status="MISSING",
            )

        size  = path.stat().st_size
        mtime = path.stat().st_mtime
        sha   = _sha256(path)
        miso  = _mtime_iso(path)

        try:
            data = json.loads(path.read_text("utf-8"))
        except Exception:
            data = {}

        beam_count, beam_ids = _beam_count_and_ids(data)
        mv          = data.get("model_version") or data.get("version")
        phase_orig  = data.get("phase") or data.get("phase_id")
        benchmark   = _detect_benchmark(data) if data else "UNKNOWN"
        version     = _detect_version(path)
        load_status = "LOADED" if size > 2 else "EMPTY"

        try:
            rel = str(path.relative_to(WORKSPACE))
        except ValueError:
            rel = str(path)

        return RuntimeFile(
            key=key, absolute_path=str(path), relative_path=rel,
            exists=True, size_bytes=size, mtime_epoch=mtime, mtime_iso=miso,
            sha256=sha, version=version, benchmark_id=benchmark,
            model_version=str(mv) if mv else None,
            beam_count=beam_count, beam_ids=beam_ids,
            phase_origin=str(phase_orig) if phase_orig else None,
            load_status=load_status,
        )
