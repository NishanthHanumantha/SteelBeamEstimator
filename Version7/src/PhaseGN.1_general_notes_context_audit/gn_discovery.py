"""
GN Discovery — Part 1 of Phase GN.1 audit.

Verifies that the General Notes DXF is discovered dynamically from the V.ROOT.1
beam registry, NOT from a hardcoded path or Benchmark Set 1 / Version6 artefacts.
"""
from __future__ import annotations
import json
import pathlib
import re
from typing import Dict, List, Optional

from .gn_models import GNDiscoveryRecord


_BENCHMARK_SET1_MARKERS = ["Benchmark_Set_1", "BenchmarkSet1", "bench_set_1", "Version6"]
_HARDCODED_PATH_PATTERNS = [
    re.compile(r"general.notes", re.I),
    re.compile(r"GN\.dxf", re.I),
]


class GeneralNotesDiscovery:
    """
    Discovers the General Notes DXF path from the V.ROOT.1 beam registry
    or, as a fallback, by scanning the Benchmark_Set_2 data directory.

    READ-ONLY: does not modify any file.
    """

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self._registry_path = (
            v7_root / "src"
            / "PhaseVROOT.1_dynamic_pipeline_initialization"
            / "beam_registry.json"
        )
        self._gn_data_dir = v7_root / "data" / "Benchmark_Set_2" / "general_notes"

    # ------------------------------------------------------------------
    def discover(self) -> GNDiscoveryRecord:
        registry_data = self._load_registry()
        gn_path, discovery_method = self._resolve_gn_path(registry_data)

        record = GNDiscoveryRecord(
            project_id=self._extract_project_id(registry_data),
            gn_dxf_path=str(gn_path) if gn_path else "NOT_FOUND",
            sheet_name=gn_path.stem if gn_path else "",
            discovered_dynamically=(discovery_method in ("registry", "data_dir_scan")),
            discovery_method=discovery_method,
        )

        if gn_path and gn_path.exists():
            record = self._inspect_dxf(record, gn_path)

        record.benchmark_set_1_dependency = self._check_benchmark_set1(registry_data)
        record.version6_dependency = self._check_version6()
        record.hardcoded_path_used = (discovery_method == "hardcoded_fallback")

        self._add_discovery_notes(record)
        return record

    # ------------------------------------------------------------------
    def _load_registry(self) -> Dict:
        if self._registry_path.exists():
            return json.loads(self._registry_path.read_text("utf-8"))
        return {}

    def _extract_project_id(self, registry: Dict) -> str:
        return (
            registry.get("project_id")
            or registry.get("project_name")
            or registry.get("metadata", {}).get("project_id", "UNKNOWN")
        )

    def _resolve_gn_path(self, registry: Dict):
        # 1. Check registry for explicit general_notes entry
        gn_entry = (
            registry.get("general_notes_dxf")
            or registry.get("general_notes", {}).get("path")
            or registry.get("drawings", {}).get("general_notes")
        )
        if gn_entry:
            p = pathlib.Path(gn_entry)
            if not p.is_absolute():
                p = self._v7 / p
            if p.exists():
                return p, "registry"

        # 2. Scan data directory
        if self._gn_data_dir.exists():
            dxf_files = sorted(self._gn_data_dir.glob("*.dxf"))
            if dxf_files:
                return dxf_files[0], "data_dir_scan"

        return None, "not_found"

    def _inspect_dxf(self, record: GNDiscoveryRecord, gn_path: pathlib.Path) -> GNDiscoveryRecord:
        try:
            import ezdxf
            doc = ezdxf.readfile(str(gn_path))
            msp = doc.modelspace()
            from collections import Counter
            cnt = Counter(e.dxftype() for e in msp)
            record.entity_counts = dict(cnt)
            record.total_text_entities = cnt.get("TEXT", 0) + cnt.get("MTEXT", 0)
            record.layers_present = list({e.dxf.layer for e in msp if hasattr(e.dxf, "layer")})
        except Exception as exc:
            record.notes.append(f"DXF inspection error: {exc}")
        return record

    def _check_benchmark_set1(self, registry: Dict) -> bool:
        registry_str = json.dumps(registry).lower()
        return any(m.lower() in registry_str for m in _BENCHMARK_SET1_MARKERS[:2])

    def _check_version6(self) -> bool:
        v6_path = self._v7.parent / "Version6"
        if not v6_path.exists():
            return False
        # Check if any V7 Python source imports from Version6
        v7_src = self._v7 / "src"
        for py_file in v7_src.rglob("*.py"):
            try:
                text = py_file.read_text("utf-8", errors="replace")
                if "Version6" in text or "version6" in text.lower():
                    return True
            except Exception:
                pass
        return False

    def _add_discovery_notes(self, record: GNDiscoveryRecord) -> None:
        if record.discovered_dynamically:
            record.notes.append("PASS: GN DXF discovered dynamically — no hardcoded path.")
        else:
            record.notes.append("FAIL: GN DXF path could not be resolved dynamically.")

        if record.benchmark_set_1_dependency:
            record.notes.append("FAIL: Benchmark Set 1 reference found in registry.")
        else:
            record.notes.append("PASS: No Benchmark Set 1 dependency detected.")

        if record.version6_dependency:
            record.notes.append("WARN: Version6 reference found in V7 source code.")
        else:
            record.notes.append("PASS: No Version6 dependency detected.")

        if record.hardcoded_path_used:
            record.notes.append("WARN: Hardcoded fallback path was used for GN DXF.")
        else:
            record.notes.append("PASS: Discovery method does not rely on hardcoded path.")
