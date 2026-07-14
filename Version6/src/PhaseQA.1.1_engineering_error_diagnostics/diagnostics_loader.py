"""
Phase QA.1.1 — Engineering Error Diagnostics & Root Cause Analysis Engine
diagnostics_loader.py — Load QA.1 reports, pipeline outputs, and ground truth.
MODEL_VERSION: 6.5.2
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional


class DiagnosticsLoadError(Exception):
    pass


def _base() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    return here.parents[2]   # Version6/


def _out(subfolder: str) -> pathlib.Path:
    return _base() / "data" / "output" / subfolder


def _benchmarks() -> pathlib.Path:
    return _base() / "data" / "benchmarks"


def _v5_out(subfolder: str) -> pathlib.Path:
    v5 = _base().parent / "Version5" / "data" / "output" / "phase_i"
    return v5 / subfolder


def _read(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        raise DiagnosticsLoadError(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _try_read(path: pathlib.Path) -> Optional[Dict[str, Any]]:
    try:
        return _read(path)
    except (DiagnosticsLoadError, Exception):
        return None


QA1_DIR  = "PhaseQA.1_engineering_accuracy_validation"
L2_DIR   = "PhaseL.2 - engineering_reinforcement_interpretation"
L21_DIR  = "PhaseL.2.1 - engineering_feature_extraction"
L22_DIR  = "PhaseL.2.2_geometry_recovery"
L3_DIR   = "PhaseL.3_beam_pattern_recognition"


class DiagnosticsLoader:
    """Loads all inputs for Phase QA.1.1 (read-only)."""

    # ── QA.1 reports ──────────────────────────────────────────────────────
    def load_qa1_error_analysis(self) -> Dict[str, Any]:
        return _read(_out(QA1_DIR) / "error_analysis.json")

    def load_qa1_accuracy_summary(self) -> Dict[str, Any]:
        return _read(_out(QA1_DIR) / "engineering_accuracy_summary.json")

    def load_qa1_engineering_score(self) -> Dict[str, Any]:
        return _read(_out(QA1_DIR) / "engineering_score.json")

    def load_qa1_confusion_matrices(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(QA1_DIR) / "confusion_matrices.json")

    def load_qa1_beam_accuracy(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(QA1_DIR) / "beam_accuracy_report.json")

    def load_qa1_reinforcement_accuracy(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(QA1_DIR) / "reinforcement_accuracy_report.json")

    def load_qa1_bbs_accuracy(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(QA1_DIR) / "bbs_accuracy_report.json")

    def load_qa1_pattern_accuracy(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(QA1_DIR) / "pattern_accuracy_report.json")

    def load_qa1_full_report(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(QA1_DIR) / "engineering_accuracy_report.json")

    # ── Phase L.2 ──────────────────────────────────────────────────────────
    def load_l2_models(self) -> Dict[str, Any]:
        return _read(_out(L2_DIR) / "beam_reinforcement_models.json")

    def get_l2_models_by_beam(self) -> Dict[str, Any]:
        data = self.load_l2_models()
        return {m["beam_id"]: m for m in data.get("models", []) if "beam_id" in m}

    # ── Phase L.2.1 ────────────────────────────────────────────────────────
    def load_l21_feature_database(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(L21_DIR) / "engineering_feature_database.json")

    def get_l21_features_by_beam(self) -> Dict[str, List[Dict[str, Any]]]:
        data = self.load_l21_feature_database()
        if not data:
            return {}
        result: Dict[str, List] = {}
        for f in data.get("features", []):
            bid = f.get("beam_id")
            if bid:
                result.setdefault(bid, []).append(f)
        return result

    def load_l21_feature_statistics(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(L21_DIR) / "feature_statistics.json")

    # ── Phase L.2.2 ────────────────────────────────────────────────────────
    def load_l22_extended_models(self) -> Optional[Dict[str, Any]]:
        p1 = _out(L22_DIR) / "extended_beam_reinforcement_models.json"
        p2 = _out(L22_DIR) / "beam_reinforcement_models_extended.json"
        return _try_read(p1) or _try_read(p2)

    def load_l22_coverage_matrix(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(L22_DIR) / "beam_coverage_matrix.json")

    def load_l22_recovery_report(self) -> Optional[Dict[str, Any]]:
        return _try_read(_out(L22_DIR) / "geometry_recovery_report.json")

    # ── Phase L.3 ──────────────────────────────────────────────────────────
    def load_l3_patterns(self) -> Dict[str, Any]:
        return _read(_out(L3_DIR) / "engineering_patterns.json")

    def get_l3_patterns_by_beam(self) -> Dict[str, Any]:
        data = self.load_l3_patterns()
        return {p["beam_id"]: p for p in data.get("patterns", []) if "beam_id" in p}

    # ── Ground truth ───────────────────────────────────────────────────────
    def load_ground_truth(self, filename: str = "benchmark_drawing_1.json") -> Dict[str, Any]:
        return _read(_benchmarks() / filename)

    # ── V5 reference data ──────────────────────────────────────────────────
    def load_v5_bbs(self) -> Optional[Dict[str, Any]]:
        return _try_read(_v5_out("i_10_bbs") / "bbs_results.json")

    def get_v5_bbs_by_beam(self) -> Dict[str, List[Dict[str, Any]]]:
        data = self.load_v5_bbs()
        if not data:
            return {}
        result: Dict[str, List] = {}
        for entry in data.get("results", []):
            for bid in entry.get("member_beams", []):
                result.setdefault(bid, []).append(entry)
        return result

    def load_v5_cut_lengths(self) -> Optional[Dict[str, Any]]:
        return _try_read(_v5_out("i_6_cut_length") / "cut_length_results.json")

    # ── Convenience: load all ──────────────────────────────────────────────
    def load_all(self) -> Dict[str, Any]:
        return {
            "qa1_errors":       self.load_qa1_error_analysis(),
            "qa1_summary":      self.load_qa1_accuracy_summary(),
            "qa1_score":        self.load_qa1_engineering_score(),
            "qa1_confusion":    self.load_qa1_confusion_matrices(),
            "qa1_beam":         self.load_qa1_beam_accuracy(),
            "qa1_rein":         self.load_qa1_reinforcement_accuracy(),
            "qa1_bbs":          self.load_qa1_bbs_accuracy(),
            "qa1_pattern":      self.load_qa1_pattern_accuracy(),
            "l2_by_beam":       self.get_l2_models_by_beam(),
            "l21_by_beam":      self.get_l21_features_by_beam(),
            "l22_extended":     self.load_l22_extended_models(),
            "l3_by_beam":       self.get_l3_patterns_by_beam(),
            "ground_truth":     self.load_ground_truth(),
            "v5_bbs_by_beam":   self.get_v5_bbs_by_beam(),
        }
