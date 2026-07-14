"""
Phase QA.1 — Engineering Accuracy Benchmark & Validation Framework
benchmark_loader.py  — Read-only loader for all previous phase model outputs.
MODEL_VERSION: 6.5.1

IMPORTANT: This module is READ-ONLY. It never writes to or modifies any phase output.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional


class BenchmarkLoadError(Exception):
    pass


# ── Path registry ───────────────────────────────────────────────────────────
def _base() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    # src/PhaseQA.1.../  →  Version6/
    return here.parents[2]


def _out(subfolder: str) -> pathlib.Path:
    return _base() / "data" / "output" / subfolder


def _v5_out(subfolder: str) -> pathlib.Path:
    v5 = _base().parent / "Version5" / "data" / "output" / "phase_i"
    return v5 / subfolder


OUTPUT_PATHS = {
    "l2":   "PhaseL.2 - engineering_reinforcement_interpretation",
    "l21":  "PhaseL.2.1 - engineering_feature_extraction",
    "l22":  "PhaseL.2.2_geometry_recovery",
    "l3":   "PhaseL.3_beam_pattern_recognition",
}


def _read_json(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        raise BenchmarkLoadError(f"File not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BenchmarkLoadError(f"Failed to read {path.name}: {exc}") from exc


def _try_read_json(path: pathlib.Path) -> Optional[Dict[str, Any]]:
    try:
        return _read_json(path)
    except BenchmarkLoadError:
        return None


class ModelOutputLoader:
    """Loads model outputs from all pipeline phases (read-only)."""

    # ── Phase L.2 ──────────────────────────────────────────────────────────
    def load_l2_models(self) -> Dict[str, Any]:
        return _read_json(_out(OUTPUT_PATHS["l2"]) / "beam_reinforcement_models.json")

    def load_l2_bar_assignments(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l2"]) / "bar_beam_assignments.json")

    def load_l2_continuity(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l2"]) / "continuity_groups.json")

    def load_l2_interpretation_report(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l2"]) / "engineering_interpretation_report.json")

    # ── Phase L.2.1 ────────────────────────────────────────────────────────
    def load_l21_features(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l21"]) / "engineering_feature_database.json")

    def load_l21_feature_statistics(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l21"]) / "feature_statistics.json")

    def load_l21_position_features(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l21"]) / "position_features.json")

    # ── Phase L.2.2 ────────────────────────────────────────────────────────
    def load_l22_coverage_matrix(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l22"]) / "beam_coverage_matrix.json")

    def load_l22_recovery_report(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l22"]) / "geometry_recovery_report.json")

    def load_l22_extended_models(self) -> Optional[Dict[str, Any]]:
        # Try both filename variants
        p1 = _out(OUTPUT_PATHS["l22"]) / "extended_beam_reinforcement_models.json"
        p2 = _out(OUTPUT_PATHS["l22"]) / "beam_reinforcement_models_extended.json"
        return _try_read_json(p1) or _try_read_json(p2)

    # ── Phase L.3 ──────────────────────────────────────────────────────────
    def load_l3_patterns(self) -> Dict[str, Any]:
        return _read_json(_out(OUTPUT_PATHS["l3"]) / "engineering_patterns.json")

    def load_l3_pattern_registry(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l3"]) / "engineering_pattern_registry.json")

    def load_l3_pattern_summary(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l3"]) / "pattern_summary.json")

    def load_l3_pattern_matrix(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_out(OUTPUT_PATHS["l3"]) / "beam_pattern_matrix.json")

    # ── V5 reference data (read-only) ──────────────────────────────────────
    def load_v5_bbs(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_v5_out("i_10_bbs") / "bbs_results.json")

    def load_v5_cut_lengths(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_v5_out("i_6_cut_length") / "cut_length_results.json")

    def load_v5_steel_weight(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_v5_out("i_11_steel_weight") / "steel_weight_results.json")

    def load_v5_bar_identity(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_v5_out("i_8_bar_identity") / "bar_identity_results.json")

    def load_v5_beam_schedule(self) -> Optional[Dict[str, Any]]:
        return _try_read_json(_v5_out("i_15_beam_schedule") / "beam_schedule_results.json")

    # ── Convenience: load all at once ─────────────────────────────────────
    def load_all(self) -> Dict[str, Any]:
        return {
            "l2_models":         self.load_l2_models(),
            "l2_bar_assignments":self.load_l2_bar_assignments(),
            "l2_continuity":     self.load_l2_continuity(),
            "l21_features":      self.load_l21_features(),
            "l22_coverage":      self.load_l22_coverage_matrix(),
            "l22_recovery":      self.load_l22_recovery_report(),
            "l22_extended":      self.load_l22_extended_models(),
            "l3_patterns":       self.load_l3_patterns(),
            "l3_summary":        self.load_l3_pattern_summary(),
            "v5_bbs":            self.load_v5_bbs(),
            "v5_cut_lengths":    self.load_v5_cut_lengths(),
            "v5_steel_weight":   self.load_v5_steel_weight(),
        }

    # ── Helper: get L.2 beam models as dict keyed by beam_id ──────────────
    def get_l2_models_by_beam(self) -> Dict[str, Dict[str, Any]]:
        data = self.load_l2_models()
        return {m["beam_id"]: m for m in data.get("models", []) if "beam_id" in m}

    # ── Helper: get L.3 patterns as dict keyed by beam_id ─────────────────
    def get_l3_patterns_by_beam(self) -> Dict[str, Dict[str, Any]]:
        data = self.load_l3_patterns()
        return {p["beam_id"]: p for p in data.get("patterns", []) if "beam_id" in p}

    # ── Helper: get L.2.1 features grouped by beam_id ─────────────────────
    def get_l21_features_by_beam(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns dict of beam_id → list of feature dicts."""
        data = self.load_l21_features()
        if not data:
            return {}
        result: Dict[str, List[Dict[str, Any]]] = {}
        for f in data.get("features", []):
            bid = f.get("beam_id")
            if bid:
                result.setdefault(bid, []).append(f)
        return result

    # ── Helper: get V5 BBS as list ─────────────────────────────────────────
    def get_v5_bbs_list(self) -> List[Dict[str, Any]]:
        data = self.load_v5_bbs()
        if not data:
            return []
        return data.get("results", [])

    # ── Helper: get V5 cut lengths (computed only) ─────────────────────────
    def get_v5_cut_lengths_computed(self) -> List[Dict[str, Any]]:
        data = self.load_v5_cut_lengths()
        if not data:
            return []
        return [r for r in data.get("results", []) if r.get("cut_length_mm")]
