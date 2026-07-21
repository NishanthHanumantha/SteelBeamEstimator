"""
Project-level stirrup coverage engine (RULE-012).
MODEL_VERSION: 8.8.2
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from beam_coverage_model import MODEL_VERSION, ProjectCoverageMetrics

_NAT_RE = re.compile(r"(\d+)|(\D+)")


def natural_beam_key(beam_id: str) -> Tuple:
    parts: List[Any] = []
    for num, text in _NAT_RE.findall(str(beam_id)):
        if num:
            parts.append(int(num))
        else:
            parts.append(text.upper())
    return tuple(parts)


def _read(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _is_stirrup_role(role: Any) -> bool:
    return str(role or "").strip().upper() == "STIRRUP"


def _is_top_role(role: Any) -> bool:
    r = str(role or "").strip().upper()
    return r.startswith("TOP")


def _is_bottom_role(role: Any) -> bool:
    r = str(role or "").strip().upper()
    return r.startswith("BOTTOM")


class CoverageEngine:
    """Load pipeline artefacts and compute stirrup family coverage."""

    def __init__(self, v8_root: Path):
        self.v8 = Path(v8_root)
        self.out = self.v8 / "data" / "output"

    def load_inputs(self) -> Dict[str, Any]:
        registry = _read(self.out / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json") or {}
        annotations = _read(
            self.out / "PhaseR.1_generalized_reinforcement_discovery" / "reinforcement_annotations.json"
        ) or {}
        intents = _read(self.out / "PhaseR1_2C_engineering_intent_resolution" / "engineering_intents.json") or {}
        details = _read(self.out / "PhaseR1_2D_reinforcement_detailing" / "reinforcement_details.json") or {}
        pieces = _read(self.out / "PhaseR1_3_reinforcement_piece_generation" / "reinforcement_pieces.json") or {}
        bars = _read(self.out / "PhaseR1.3_pipeline_integration" / "engineering_bar_models.json") or {}

        beam_ids = list(registry.get("beam_ids") or [])
        if not beam_ids and isinstance(registry.get("beams"), dict):
            beam_ids = list(registry["beams"].keys())
        beam_ids = sorted({str(b) for b in beam_ids if b}, key=natural_beam_key)

        stage_stirrup = {
            "Annotation Discovery": self._annotation_stirrup_beams(annotations),
            "Intent Resolution": self._intent_role_beams(intents, _is_stirrup_role),
            "Reinforcement Detail": self._detail_role_beams(details, _is_stirrup_role),
            "Piece Generation": self._piece_role_beams(pieces, _is_stirrup_role),
            "EngineeringBars": self._ebar_role_beams(bars, _is_stirrup_role),
        }
        top_beams = self._intent_role_beams(intents, _is_top_role)
        bottom_beams = self._intent_role_beams(intents, _is_bottom_role)
        # Fall back to annotations for top/bottom if intent empty for a beam
        top_beams |= self._annotation_role_beams(annotations, _is_top_role)
        bottom_beams |= self._annotation_role_beams(annotations, _is_bottom_role)

        return {
            "beam_ids": beam_ids,
            "registry": registry,
            "stage_stirrup": stage_stirrup,
            "top_beams": top_beams,
            "bottom_beams": bottom_beams,
            "sources": {
                "beam_registry": str(
                    self.out / "PhaseVROOT.1_dynamic_pipeline_initialization" / "beam_registry.json"
                ),
                "annotations": str(
                    self.out
                    / "PhaseR.1_generalized_reinforcement_discovery"
                    / "reinforcement_annotations.json"
                ),
                "intents": str(
                    self.out / "PhaseR1_2C_engineering_intent_resolution" / "engineering_intents.json"
                ),
                "details": str(
                    self.out / "PhaseR1_2D_reinforcement_detailing" / "reinforcement_details.json"
                ),
                "pieces": str(
                    self.out / "PhaseR1_3_reinforcement_piece_generation" / "reinforcement_pieces.json"
                ),
                "engineering_bars": str(
                    self.out / "PhaseR1.3_pipeline_integration" / "engineering_bar_models.json"
                ),
            },
            "model_version": MODEL_VERSION,
        }

    def compute_metrics(
        self,
        beam_ids: List[str],
        stage_stirrup: Dict[str, Set[str]],
        validations: List[Dict[str, Any]],
    ) -> ProjectCoverageMetrics:
        expected = len(beam_ids)
        # Detected family = beam with at least one STIRRUP representation at any validated stage.
        # Prefer EngineeringBars ∩ Intent ∩ Detail for family count; union of stages with stirrup.
        detected_set: Set[str] = set()
        for stage_set in stage_stirrup.values():
            detected_set |= set(stage_set)
        detected_set &= set(beam_ids)
        detected = len(detected_set)
        coverage = round((detected / expected) * 100.0, 2) if expected else 0.0

        pass_count = sum(1 for v in validations if v.get("status") == "PASS")
        fail_count = sum(1 for v in validations if v.get("status") == "FAIL")
        unknown_count = sum(1 for v in validations if v.get("status") == "UNKNOWN")
        n = len(validations) or expected or 1
        phase_dist: Dict[str, int] = defaultdict(int)
        for v in validations:
            if v.get("status") == "FAIL" and v.get("likely_missing_phase"):
                phase_dist[str(v["likely_missing_phase"])] += 1

        return ProjectCoverageMetrics(
            beam_count=expected,
            detected_stirrup_families=detected,
            coverage_pct=coverage,
            pass_count=pass_count,
            fail_count=fail_count,
            unknown_count=unknown_count,
            pass_pct=round((pass_count / n) * 100.0, 2),
            fail_pct=round((fail_count / n) * 100.0, 2),
            missing_pct=round(((expected - detected) / expected) * 100.0, 2) if expected else 0.0,
            phase_distribution=dict(sorted(phase_dist.items())),
        )

    @staticmethod
    def _annotation_stirrup_beams(annotations: Dict[str, Any]) -> Set[str]:
        return CoverageEngine._annotation_role_beams(annotations, _is_stirrup_role)

    @staticmethod
    def _annotation_role_beams(annotations: Dict[str, Any], pred) -> Set[str]:
        out: Set[str] = set()
        by_beam = annotations.get("by_beam") or {}
        for beam_id, items in by_beam.items():
            rows = items if isinstance(items, list) else []
            if any(pred(a.get("role")) for a in rows if isinstance(a, dict)):
                out.add(str(beam_id))
        return out

    @staticmethod
    def _intent_role_beams(intents: Dict[str, Any], pred) -> Set[str]:
        out: Set[str] = set()
        for item in intents.get("intents") or []:
            if pred(item.get("role")) and item.get("beam_id"):
                out.add(str(item["beam_id"]))
        return out

    @staticmethod
    def _detail_role_beams(details: Dict[str, Any], pred) -> Set[str]:
        out: Set[str] = set()
        for item in details.get("details") or []:
            if pred(item.get("role")) and item.get("beam_id"):
                out.add(str(item["beam_id"]))
        return out

    @staticmethod
    def _piece_role_beams(pieces: Dict[str, Any], pred) -> Set[str]:
        out: Set[str] = set()
        for item in pieces.get("pieces") or []:
            role = item.get("role") or item.get("piece_role")
            if pred(role) and item.get("beam_id"):
                out.add(str(item["beam_id"]))
        return out

    @staticmethod
    def _ebar_role_beams(bars: Dict[str, Any], pred) -> Set[str]:
        out: Set[str] = set()
        for beam in bars.get("beams") or []:
            bid = beam.get("beam_id")
            if not bid:
                continue
            if any(pred(bar.get("bar_role")) for bar in beam.get("bars") or []):
                out.add(str(bid))
        return out
