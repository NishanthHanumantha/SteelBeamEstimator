"""
Phase V.A.2 -- benchmark2_loader.py
Discovers and validates all Benchmark Set 2 input files.
MODEL_VERSION: 7.0.0
"""
from __future__ import annotations

import json
import pathlib
import shutil
from datetime import datetime
from typing import List

from benchmark2_models import Benchmark2Manifest, BenchmarkFile

_ROOT   = pathlib.Path(__file__).resolve().parents[3]   # SteelBeamEstimator/
_V7     = _ROOT / "Version8"
_SRC    = _ROOT / "Test_Input" / "Second Set Drawings"
_DST    = _V7   / "data/Benchmark_Set_2"

REQUIRED_TYPES = {"FRAMING_DXF", "REINFORCEMENT_DXF", "GENERAL_NOTES_DXF"}


def _classify(f: pathlib.Path) -> str:
    parent = f.parent.name.lower()
    name   = f.name.lower()
    if parent == "framing" or "framingplan" in name:
        return "FRAMING_DXF"
    if parent == "reinforcement" or "reinforcement" in name:
        return "REINFORCEMENT_DXF"
    if parent == "general_notes" or "notes" in name:
        return "GENERAL_NOTES_DXF"
    if f.suffix.lower() in (".xlsx", ".xls"):
        return "ESTIMATOR_EXCEL"
    if f.suffix.lower() == ".dxf":
        return "DXF_UNKNOWN"
    return "OTHER"


class Benchmark2Loader:
    """
    Scans the Benchmark Set 2 source folder, copies files to Version8,
    identifies file types, and validates required inputs exist.
    """

    def __init__(
        self,
        source_dir: pathlib.Path = _SRC,
        dest_dir:   pathlib.Path = _DST,
    ) -> None:
        self._src = source_dir
        self._dst = dest_dir

    def load(self) -> Benchmark2Manifest:
        timestamp = datetime.now().isoformat()
        issues: List[str] = []
        files:  List[BenchmarkFile] = []

        # If manifest already exists from previous run, load it
        mf_path = self._dst / "benchmark2_manifest.json"
        if mf_path.exists():
            try:
                raw = json.loads(mf_path.read_text(encoding="utf-8"))
                for fr in raw.get("files", []):
                    files.append(
                        BenchmarkFile(
                            filename=fr["filename"],
                            relative_path=fr["relative_path"],
                            file_type=fr["file_type"],
                            size_bytes=fr["size_bytes"],
                            copied_to=fr["copied_to"],
                        )
                    )
                print(f"  Loaded manifest: {len(files)} files from previous copy")
            except Exception:
                files = self._copy_files(issues)
        else:
            files = self._copy_files(issues)

        found_types = {f.file_type for f in files}
        missing = REQUIRED_TYPES - found_types
        for mt in sorted(missing):
            issues.append(f"Required input type missing: {mt}")

        has_excel   = any(f.file_type == "ESTIMATOR_EXCEL" for f in files)
        drawing_name = self._infer_drawing_name(files)

        if not has_excel:
            issues.append(
                "ESTIMATOR_EXCEL not found in Benchmark Set 2 -- "
                "workbook comparison will be skipped."
            )

        manifest = Benchmark2Manifest(
            benchmark_id="BENCHMARK::DRAWING_2_V7",
            timestamp=timestamp,
            source_folder=str(self._src),
            destination_folder=str(self._dst),
            model_version="7.0.0",
            files=files,
            total_files=len(files),
            dxf_count=sum(1 for f in files if "DXF" in f.file_type),
            has_estimator_excel=has_excel,
            drawing_name=drawing_name,
            validation_passed=len([i for i in issues if "ESTIMATOR_EXCEL" not in i]) == 0,
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
            files.append(
                BenchmarkFile(
                    filename=item.name,
                    relative_path=str(rel),
                    file_type=_classify(item),
                    size_bytes=item.stat().st_size,
                    copied_to=str(dst_file),
                )
            )
        return files

    @staticmethod
    def _infer_drawing_name(files: List[BenchmarkFile]) -> str:
        for f in files:
            if f.file_type == "REINFORCEMENT_DXF":
                stem = pathlib.Path(f.filename).stem
                return stem
        return "UNKNOWN_DRAWING"

    def export_manifest(self, manifest: Benchmark2Manifest) -> pathlib.Path:
        out = self._dst / "benchmark2_manifest.json"
        data = {
            "benchmark_id": manifest.benchmark_id,
            "timestamp": manifest.timestamp,
            "source_folder": manifest.source_folder,
            "destination_folder": manifest.destination_folder,
            "model_version": manifest.model_version,
            "drawing_name": manifest.drawing_name,
            "total_files": manifest.total_files,
            "dxf_count": manifest.dxf_count,
            "has_estimator_excel": manifest.has_estimator_excel,
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
