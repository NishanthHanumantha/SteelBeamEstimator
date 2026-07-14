"""
Phase QA.1 — Engineering Accuracy Benchmark & Validation Framework
ground_truth_loader.py  — Load manually verified benchmark files (JSON / CSV / Excel).
MODEL_VERSION: 6.5.1
"""
from __future__ import annotations

import csv
import json
import pathlib
from typing import Any, Dict, List, Optional


class GroundTruthLoadError(Exception):
    pass


class GroundTruth:
    """Parsed ground truth data for one benchmark drawing."""

    def __init__(self, raw: Dict[str, Any]):
        self._raw = raw

    # ── identity ───────────────────────────────────────────────────────────
    @property
    def benchmark_id(self) -> str:
        return self._raw.get("benchmark_id", "UNKNOWN")

    @property
    def drawing_name(self) -> str:
        return self._raw.get("drawing_name", "UNKNOWN")

    @property
    def benchmark_version(self) -> str:
        return self._raw.get("benchmark_version", "1.0")

    # ── beam detection ─────────────────────────────────────────────────────
    @property
    def expected_beam_ids(self) -> List[str]:
        return self._raw.get("beam_detection", {}).get("expected_beam_ids", [])

    @property
    def expected_beam_count(self) -> int:
        return self._raw.get("beam_detection", {}).get("expected_beam_count", len(self.expected_beam_ids))

    # ── reinforcement ──────────────────────────────────────────────────────
    @property
    def expected_original_bar_count(self) -> int:
        return self._raw.get("reinforcement", {}).get("expected_original_bar_count", 0)

    @property
    def expected_total_bar_count(self) -> int:
        return self._raw.get("reinforcement", {}).get("expected_total_bar_count_after_recovery", 0)

    def expected_bars_for_beam(self, beam_id: str) -> Optional[Dict[str, Any]]:
        return self._raw.get("reinforcement", {}).get("expected_bars_per_beam", {}).get(beam_id)

    # ── geometry ───────────────────────────────────────────────────────────
    @property
    def geometry_tolerance_mm(self) -> float:
        return self._raw.get("geometry", {}).get("tolerance_mm", 2.0)

    def expected_span_mm(self, beam_id: str) -> Optional[float]:
        return self._raw.get("geometry", {}).get("expected_spans_mm", {}).get(beam_id)

    def expected_depth_mm(self, beam_id: str) -> Optional[float]:
        return self._raw.get("geometry", {}).get("expected_depths_mm", {}).get(beam_id)

    def expected_width_mm(self, beam_id: str) -> Optional[float]:
        return self._raw.get("geometry", {}).get("expected_widths_mm", {}).get(beam_id)

    # ── top/bottom classification ──────────────────────────────────────────
    def expected_top_bottom(self, beam_id: str) -> Optional[Dict[str, Any]]:
        return self._raw.get("top_bottom_classification", {}).get("expected_per_beam", {}).get(beam_id)

    @property
    def expected_tb_correct_count(self) -> int:
        return self._raw.get("top_bottom_classification", {}).get("expected_correct_count", 0)

    @property
    def expected_tb_total(self) -> int:
        return self._raw.get("top_bottom_classification", {}).get("expected_total_classifiable", 0)

    # ── patterns ───────────────────────────────────────────────────────────
    def expected_pattern(self, beam_id: str) -> Optional[Dict[str, Any]]:
        return self._raw.get("patterns", {}).get("expected_per_beam", {}).get(beam_id)

    @property
    def expected_correct_span_pattern(self) -> int:
        return self._raw.get("patterns", {}).get("expected_correct_span_pattern", 0)

    @property
    def expected_correct_continuity(self) -> int:
        return self._raw.get("patterns", {}).get("expected_correct_continuity", 0)

    # ── features ───────────────────────────────────────────────────────────
    @property
    def expected_feature_count(self) -> int:
        return self._raw.get("features", {}).get("expected_feature_count", 0)

    def expected_has_top_bars(self) -> List[str]:
        return self._raw.get("features", {}).get("expected_has_top_bars", [])

    def expected_has_bottom_bars(self) -> List[str]:
        return self._raw.get("features", {}).get("expected_has_bottom_bars", [])

    def expected_has_stirrups(self) -> List[str]:
        return self._raw.get("features", {}).get("expected_has_stirrups", [])

    def expected_continuity_beams(self) -> List[str]:
        return self._raw.get("features", {}).get("expected_continuity_beams", [])

    # ── BBS / cut length / steel weight ───────────────────────────────────
    @property
    def expected_bbs_count(self) -> int:
        return self._raw.get("bbs", {}).get("expected_count", 0)

    @property
    def steel_weight_available(self) -> bool:
        return self._raw.get("steel_weight", {}).get("available", False)

    # ── raw access ─────────────────────────────────────────────────────────
    def raw(self) -> Dict[str, Any]:
        return self._raw


class GroundTruthLoader:
    """Loads ground truth from JSON, CSV, or Excel files."""

    def load(self, path: str | pathlib.Path) -> GroundTruth:
        p = pathlib.Path(path)
        if not p.exists():
            raise GroundTruthLoadError(f"Ground truth file not found: {p}")

        suffix = p.suffix.lower()
        if suffix == ".json":
            return self._load_json(p)
        if suffix == ".csv":
            return self._load_csv(p)
        if suffix in (".xlsx", ".xls"):
            return self._load_excel(p)
        raise GroundTruthLoadError(f"Unsupported ground truth format: {suffix}")

    # ── JSON ───────────────────────────────────────────────────────────────
    def _load_json(self, p: pathlib.Path) -> GroundTruth:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            raise GroundTruthLoadError(f"Failed to parse JSON ground truth: {exc}") from exc
        self._validate_required_keys(raw, p)
        return GroundTruth(raw)

    # ── CSV ────────────────────────────────────────────────────────────────
    def _load_csv(self, p: pathlib.Path) -> GroundTruth:
        """
        Expect minimal CSV format:
        benchmark_id, drawing_name, beam_ids (comma-joined), expected_beam_count
        """
        try:
            with p.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
        except Exception as exc:
            raise GroundTruthLoadError(f"Failed to parse CSV ground truth: {exc}") from exc

        if not rows:
            raise GroundTruthLoadError("CSV ground truth is empty")

        row = rows[0]
        beam_ids = [b.strip() for b in row.get("beam_ids", "").split("|") if b.strip()]
        raw = {
            "benchmark_id": row.get("benchmark_id", "BENCHMARK::CSV"),
            "drawing_name": row.get("drawing_name", "UNKNOWN"),
            "benchmark_version": row.get("benchmark_version", "1.0"),
            "beam_detection": {
                "expected_beam_ids": beam_ids,
                "expected_beam_count": int(row.get("expected_beam_count", len(beam_ids))),
            },
            "reinforcement": {
                "expected_original_bar_count": int(row.get("expected_bar_count", 0)),
                "expected_total_bar_count_after_recovery": int(row.get("expected_total_bar_count", 0)),
                "expected_bars_per_beam": {},
            },
            "geometry": {"expected_spans_mm": {}, "tolerance_mm": 2.0},
            "top_bottom_classification": {"expected_per_beam": {}},
            "patterns": {"expected_per_beam": {}},
            "features": {"expected_feature_count": len(beam_ids)},
            "bbs": {"expected_count": 0},
            "steel_weight": {"available": False},
        }
        return GroundTruth(raw)

    # ── Excel ──────────────────────────────────────────────────────────────
    def _load_excel(self, p: pathlib.Path) -> GroundTruth:
        try:
            import openpyxl  # type: ignore
        except ImportError as exc:
            raise GroundTruthLoadError("openpyxl is required to read Excel ground truth files: pip install openpyxl") from exc
        try:
            wb = openpyxl.load_workbook(str(p), data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
        except Exception as exc:
            raise GroundTruthLoadError(f"Failed to parse Excel ground truth: {exc}") from exc

        if len(rows) < 2:
            raise GroundTruthLoadError("Excel ground truth must have at least a header row and one data row")

        headers = [str(h).strip() if h else "" for h in rows[0]]
        data = {}
        for row in rows[1:]:
            for h, v in zip(headers, row):
                if h:
                    data[h] = v

        beam_ids_raw = str(data.get("beam_ids", "")).split("|")
        beam_ids = [b.strip() for b in beam_ids_raw if b.strip()]
        raw = {
            "benchmark_id": str(data.get("benchmark_id", "BENCHMARK::EXCEL")),
            "drawing_name": str(data.get("drawing_name", "UNKNOWN")),
            "benchmark_version": "1.0",
            "beam_detection": {
                "expected_beam_ids": beam_ids,
                "expected_beam_count": len(beam_ids),
            },
            "reinforcement": {
                "expected_original_bar_count": int(data.get("expected_bar_count", 0) or 0),
                "expected_total_bar_count_after_recovery": int(data.get("expected_total_bar_count", 0) or 0),
                "expected_bars_per_beam": {},
            },
            "geometry": {"expected_spans_mm": {}, "tolerance_mm": 2.0},
            "top_bottom_classification": {"expected_per_beam": {}},
            "patterns": {"expected_per_beam": {}},
            "features": {"expected_feature_count": len(beam_ids)},
            "bbs": {"expected_count": 0},
            "steel_weight": {"available": False},
        }
        return GroundTruth(raw)

    # ── validation ─────────────────────────────────────────────────────────
    def _validate_required_keys(self, raw: Dict, path: pathlib.Path) -> None:
        required = ["benchmark_id", "drawing_name", "beam_detection"]
        missing = [k for k in required if k not in raw]
        if missing:
            raise GroundTruthLoadError(
                f"Ground truth file {path.name} is missing required keys: {missing}"
            )
