"""
benchmark3_loader.py — Discover and stage Benchmark Set 3 input files.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

import json
import pathlib
import shutil
from datetime import datetime
from typing import Dict, List

from benchmark3_models import Benchmark3Manifest, BenchmarkFile

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SRC  = _ROOT / "Test_Input" / "Third Set Drawings"
_DST  = _ROOT / "Version7" / "data" / "Benchmark_Set_3"

REQUIRED_TYPES = {"FRAMING_DXF", "REINFORCEMENT_DXF", "GENERAL_NOTES_DXF"}


def _classify(f: pathlib.Path) -> str:
    parent = f.parent.name.lower()
    name   = f.name.lower()
    if parent == "framing" or "framingplan" in name or "framing" in name:
        return "FRAMING_DXF"
    if parent == "reinforcement" or "reinforcement" in name:
        return "REINFORCEMENT_DXF"
    if parent == "general_notes" or "general" in name or "notes" in name:
        return "GENERAL_NOTES_DXF"
    if f.suffix.lower() == ".dxf":
        return "ENGINEERING_DXF_OTHER"
    if f.suffix.lower() in (".xlsx", ".xls"):
        return "ESTIMATOR_EXCEL"
    return "OTHER"


class Benchmark3Loader:

    def __init__(
        self,
        source_dir: pathlib.Path = _SRC,
        dest_dir:   pathlib.Path = _DST,
    ) -> None:
        self._src = source_dir
        self._dst = dest_dir

    def load(self) -> Benchmark3Manifest:
        issues: List[str] = []
        files  = self._copy_files(issues)

        found_types = {f.file_type for f in files}
        for mt in sorted(REQUIRED_TYPES - found_types):
            issues.append(f"Required input type missing: {mt}")

        classification: Dict[str, int] = {}
        for f in files:
            classification[f.file_type] = classification.get(f.file_type, 0) + 1

        project_name, building, floor = self._infer_project(files)

        manifest = Benchmark3Manifest(
            benchmark_id="BENCHMARK::DRAWING_3_V8",
            timestamp=datetime.now().isoformat(),
            source_folder=str(self._src),
            destination_folder=str(self._dst),
            model_version="8.1.1",
            project_name=project_name,
            building=building,
            floor=floor,
            files=files,
            total_files=len(files),
            dxf_count=sum(1 for f in files if "DXF" in f.file_type),
            drawing_classification=classification,
            validation_passed=len(issues) == 0,
            issues=issues,
        )
        return manifest

    def _copy_files(self, issues: List[str]) -> List[BenchmarkFile]:
        files: List[BenchmarkFile] = []
        if not self._src.exists():
            issues.append(f"Source folder not found: {self._src}")
            return files

        self._dst.mkdir(parents=True, exist_ok=True)
        for item in sorted(self._src.rglob("*")):
            if not item.is_file():
                continue
            rel      = item.relative_to(self._src)
            dst_file = self._dst / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(item), str(dst_file))
            files.append(BenchmarkFile(
                filename=item.name,
                relative_path=str(rel),
                file_type=_classify(item),
                size_bytes=item.stat().st_size,
                copied_to=str(dst_file),
            ))
        return files

    @staticmethod
    def _infer_project(files: List[BenchmarkFile]):
        project_name = "UNKNOWN_PROJECT"
        building     = "UNKNOWN_BUILDING"
        floor        = "UNKNOWN_FLOOR"
        for f in files:
            if f.file_type == "REINFORCEMENT_DXF":
                stem = pathlib.Path(f.filename).stem
                parts = stem.replace("_", " ").split()
                if parts:
                    project_name = parts[0]
                if "TF" in stem.upper():
                    floor = "TF"
                elif "GF" in stem.upper():
                    floor = "GF"
                if "Galera" in stem:
                    building = "Galera"
                break
        return project_name, building, floor

    def export_manifest(self, manifest: Benchmark3Manifest) -> pathlib.Path:
        out = self._dst / "benchmark3_manifest.json"
        data = {
            "benchmark_id": manifest.benchmark_id,
            "timestamp": manifest.timestamp,
            "source_folder": manifest.source_folder,
            "destination_folder": manifest.destination_folder,
            "model_version": manifest.model_version,
            "project_name": manifest.project_name,
            "building": manifest.building,
            "floor": manifest.floor,
            "total_files": manifest.total_files,
            "dxf_count": manifest.dxf_count,
            "drawing_classification": manifest.drawing_classification,
            "validation_passed": manifest.validation_passed,
            "issues": manifest.issues,
            "files": [
                {
                    "filename": f.filename,
                    "relative_path": f.relative_path,
                    "file_type": f.file_type,
                    "size_bytes": f.size_bytes,
                    "copied_to": f.copied_to,
                }
                for f in manifest.files
            ],
        }
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return out
