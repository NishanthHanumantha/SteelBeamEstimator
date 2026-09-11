"""
Steel Weight Completion — Phase V.B.1 MODULE 2
Updated: Phase R.2B — EngineeringContext consumption (MODEL_VERSION 7.6.0)

Deterministic steel weight calculation from L.2 engineering data.
Engineering parameters (Ld, cover, hook, density) sourced from
EngineeringContextLoader when provided.
"""
import math
import sys
import json
import pathlib
import re
from typing import Dict, List, Optional, Any, Tuple

# ── SI.1 integration ─────────────────────────────────────────────────────────
_SI1_SRC = pathlib.Path(__file__).parents[1] / "PhaseSI.1_stirrup_improvement"
if str(_SI1_SRC) not in sys.path:
    sys.path.insert(0, str(_SI1_SRC))

try:
    from phase_si1_orchestrator import StirrupImprover as _SI1Improver
    _SI1_AVAILABLE = True
except Exception:
    _SI1Improver = None
    _SI1_AVAILABLE = False

from production_output_models import (
    BarSteelWeight, BeamSteelWeight, DiameterSummary, ProjectSteelSummary
)

# Legacy fallbacks when no EngineeringContextLoader is provided
_DENSITY_KG_M3 = 7850.0
_DEVELOPMENT_LENGTH_FACTOR = 40
_COVER_MM = 40.0
_HOOK_MULTIPLE = 10
_SUPPORTED_DIAMETERS = [8, 10, 12, 16, 20, 25, 32]
_SUPPORTED_SET = frozenset(_SUPPORTED_DIAMETERS)
_RECONCILE_TOL_KG = 0.05


def canonicalize_bar_diameter_mm(
    diameter_mm: Any,
    bar_label: str = "",
) -> Optional[int]:
    """
    Map a raw diameter to an IS bar size.

    252 from Y25+trailing digit (after hyphen/space stripping) becomes 25.
    Unsupported sizes that cannot be repaired return None.
    """
    raw: Optional[int] = None
    try:
        if diameter_mm is not None and str(diameter_mm).strip() != "":
            raw = int(round(float(diameter_mm)))
    except (TypeError, ValueError):
        raw = None
    if raw in _SUPPORTED_SET:
        return raw
    label = str(bar_label or "")
    m = re.search(r"[YyRrTt]\s*(\d+)", label)
    if m:
        cand = int(m.group(1))
        if cand in _SUPPORTED_SET:
            return cand
        repaired = _longest_supported_prefix(cand)
        if repaired is not None:
            return repaired
    if raw is not None:
        return _longest_supported_prefix(raw)
    return None


def _longest_supported_prefix(n: int) -> Optional[int]:
    digits = str(abs(int(n)))
    for length in range(len(digits), 0, -1):
        v = int(digits[:length])
        if v in _SUPPORTED_SET:
            return v
    return None


def reconcile_beam_weight(total_kg: float, weight_by_diameter: Dict[int, float]) -> Tuple[bool, float]:
    diam_sum = sum(float(weight_by_diameter.get(d, 0.0) or 0.0) for d in _SUPPORTED_DIAMETERS)
    return abs(float(total_kg) - diam_sum) <= _RECONCILE_TOL_KG, diam_sum

_ROLE_LABELS = {
    "TOP_MAIN":          "Top Main Bars",
    "BOTTOM_MAIN":       "Bottom Main Bars",
    "TOP_EXTRA":         "Extra Top Bars",
    "BOTTOM_EXTRA":      "Extra Bottom Bars",
    "SIDE_FACE":         "Side Face Reinforcement",
    "STIRRUP":           "Stirrups",
    "SPACER":            "Spacer Bars",
    "BENT":              "Bent Bars",
    "CRANKED":           "Cranked Bars",
    "DEVELOPMENT":       "Development Length Bars",
    "LAP":               "Lap Bars",
}

_L2_ROLE_MAP = {
    "top_main_bars":          "TOP_MAIN",
    "bottom_main_bars":       "BOTTOM_MAIN",
    "top_extra_bars":         "TOP_EXTRA",
    "bottom_extra_bars":      "BOTTOM_EXTRA",
    "side_face_reinforcement":"SIDE_FACE",
    "stirrups":               "STIRRUP",
    "spacer_bars":            "SPACER",
    "supplementary_bars":     "BENT",
    "chair_bars":             "SPACER",
    "development_length_regions": "DEVELOPMENT",
    "continuity_regions":     "LAP",
}


class SteelWeightCompletion:
    """
    Reads L.2 beam reinforcement models and computes deterministic steel weights.
    When loader is provided, all engineering parameters come from EngineeringContext.
    """

    def __init__(
        self,
        l2_models_path: pathlib.Path,
        loader: Optional[Any] = None,
    ) -> None:
        self.l2_path = l2_models_path
        self._loader = loader
        self._models: List[Dict[str, Any]] = []
        self._improver = (
            _SI1Improver(loader) if (_SI1_AVAILABLE and _SI1Improver and loader)
            else (_SI1Improver() if (_SI1_AVAILABLE and _SI1Improver) else None)
        )

    # ── engineering parameter accessors ─────────────────────────────────────

    def _density(self) -> float:
        return self._loader.get_steel_density() if self._loader else _DENSITY_KG_M3

    def _cover_mm(self) -> float:
        return float(self._loader.get_cover("BEAM")) if self._loader else _COVER_MM

    def _hook_multiple(self) -> int:
        return self._loader.get_hook_multiple(135) if self._loader else _HOOK_MULTIPLE

    def _concrete_grade(self) -> str:
        return self._loader.get_concrete_grade("BEAM") if self._loader else "M30"

    def _steel_grade(self) -> str:
        return self._loader.get_steel_grade() if self._loader else "Fe415"

    def _development_length_mm(self, diameter_mm: float) -> int:
        if self._loader:
            return self._loader.get_development_length_mm(
                int(diameter_mm),
                self._concrete_grade(),
                self._steel_grade(),
            )
        return int(_DEVELOPMENT_LENGTH_FACTOR * diameter_mm)

    def _minimum_lap_mm(self, diameter_mm: float) -> int:
        if self._loader:
            return self._loader.get_lap_rule(int(diameter_mm))
        return int(_DEVELOPMENT_LENGTH_FACTOR * diameter_mm)

    # ── public ──────────────────────────────────────────────────────────────

    def compute(self) -> ProjectSteelSummary:
        self._load_l2()
        beam_weights: List[BeamSteelWeight] = []
        diameter_totals: Dict[int, float] = {d: 0.0 for d in _SUPPORTED_DIAMETERS}
        density = self._density()

        for model in self._models:
            bw = self._compute_beam(model)
            beam_weights.append(bw)
            for d, w in bw.weight_by_diameter.items():
                if d in _SUPPORTED_SET:
                    diameter_totals[d] = diameter_totals.get(d, 0.0) + w

        total_kg = sum(
            sum(bw.weight_by_diameter.get(d, 0.0) for d in _SUPPORTED_DIAMETERS)
            for bw in beam_weights
        )
        mismatches = []
        for bw in beam_weights:
            ok, diam_sum = reconcile_beam_weight(bw.total_weight_kg, bw.weight_by_diameter)
            if not ok:
                mismatches.append(
                    f"{bw.beam_id}: total={bw.total_weight_kg:.3f} kg "
                    f"diameter_sum={diam_sum:.3f} kg "
                    f"bars={[ (b.bar_label, b.diameter_mm, round(b.total_weight_kg, 3)) for b in bw.bar_weights ]}"
                )
        if mismatches:
            print("[VB.1] BEAM_TOTAL vs diameter reconciliation FAILED (not overwritten):")
            for line in mismatches:
                print(f"      {line}")
        total_bars = sum(len(bw.bar_weights) for bw in beam_weights)

        diameter_summary: List[DiameterSummary] = []
        for d in _SUPPORTED_DIAMETERS:
            w = diameter_totals.get(d, 0.0)
            if w > 0:
                area_mm2 = math.pi * d ** 2 / 4
                total_len = w / (area_mm2 * density / 1e9) if area_mm2 > 0 else 0.0
                diameter_summary.append(DiameterSummary(
                    diameter_mm=d,
                    total_bars=sum(
                        len([b for b in bw.bar_weights if int(b.diameter_mm) == d])
                        for bw in beam_weights
                    ),
                    total_length_mm=total_len,
                    total_weight_kg=w,
                    weight_fraction=w / total_kg if total_kg > 0 else 0.0,
                ))

        return ProjectSteelSummary(
            total_weight_kg=total_kg,
            beam_weights=beam_weights,
            diameter_summary=diameter_summary,
            total_bars=total_bars,
            total_beams=len(beam_weights),
        )

    # ── private ─────────────────────────────────────────────────────────────

    def _load_l2(self) -> None:
        data = json.loads(self.l2_path.read_text(encoding="utf-8"))
        self._models = data.get("models", [])

    def _compute_beam(self, model: Dict[str, Any]) -> BeamSteelWeight:
        beam_id = model.get("beam_id", "")
        beam_name = model.get("beam_name", beam_id)
        geom = model.get("geometry") or {}
        span_mm = float(geom.get("clear_span_mm") or 0)
        depth_mm = geom.get("depth_mm")
        width_mm = geom.get("width_mm")

        bar_weights: List[BarSteelWeight] = []
        weight_by_diam: Dict[int, float] = {}
        density = self._density()

        for l2_key, role in _L2_ROLE_MAP.items():
            bars_list = model.get(l2_key) or []
            if not isinstance(bars_list, list):
                continue
            for bar in bars_list:
                if not isinstance(bar, dict):
                    continue

                if role == "STIRRUP" and self._improver:
                    si1_rows = self._improver.compute_beam(
                        bar=bar,
                        beam_id=beam_id,
                        span_mm=span_mm,
                        depth_mm=depth_mm,
                        width_mm=width_mm,
                    )
                    d_mm = canonicalize_bar_diameter_mm(
                        bar.get("diameter_mm"), str(bar.get("bar_label") or "")
                    )
                    if d_mm is None:
                        continue
                    d_mm = float(d_mm)
                    for row_d in si1_rows:
                        qty    = int(row_d.get("quantity") or 0)
                        cut_mm = float(row_d.get("cut_length_m") or 0) * 1000
                        area   = math.pi * d_mm ** 2 / 4.0
                        w_per  = area * cut_mm * density / 1e9
                        w_tot  = w_per * qty
                        bsw = BarSteelWeight(
                            bar_id=str(bar.get("bar_id") or ""),
                            beam_id=beam_id,
                            role="STIRRUP",
                            bar_label=str(bar.get("bar_label") or ""),
                            diameter_mm=d_mm,
                            quantity=qty,
                            steel_grade=str(bar.get("steel_grade") or "Y"),
                            cut_length_mm=cut_mm,
                            cut_length_source="SI1_zone_engine",
                            area_mm2=area,
                            weight_per_bar_kg=w_per,
                            total_weight_kg=w_tot,
                            formula_used=(
                                f"SI.1: W=(pi*{d_mm}^2/4)*{cut_mm:.0f}*{qty}*"
                                f"{density:.0f}/1e9"
                            ),
                        )
                        bar_weights.append(bsw)
                        d_key = int(d_mm)
                        if d_key in _SUPPORTED_SET:
                            weight_by_diam[d_key] = weight_by_diam.get(d_key, 0.0) + w_tot
                    continue

                bw = self._compute_bar(bar, beam_id, role, span_mm, depth_mm, width_mm)
                if bw is None:
                    continue
                bar_weights.append(bw)
                d_key = int(bw.diameter_mm)
                if d_key in _SUPPORTED_SET:
                    weight_by_diam[d_key] = weight_by_diam.get(d_key, 0.0) + bw.total_weight_kg

        total = sum(weight_by_diam.get(d, 0.0) for d in _SUPPORTED_DIAMETERS)
        ok, diam_sum = reconcile_beam_weight(total, weight_by_diam)
        if not ok:
            total = diam_sum
        return BeamSteelWeight(
            beam_id=beam_id,
            beam_name=beam_name,
            span_mm=span_mm,
            depth_mm=depth_mm,
            width_mm=width_mm,
            bar_weights=bar_weights,
            total_weight_kg=total,
            weight_by_diameter=weight_by_diam,
        )

    def _compute_bar(
        self,
        bar: Dict[str, Any],
        beam_id: str,
        role: str,
        span_mm: float,
        depth_mm: Optional[float],
        width_mm: Optional[float],
    ) -> Optional[BarSteelWeight]:
        diameter_mm = canonicalize_bar_diameter_mm(
            bar.get("diameter_mm"), str(bar.get("bar_label") or "")
        )
        if diameter_mm is None:
            print(
                f"[VB.1] SKIP unsupported diameter beam={beam_id} "
                f"role={role} label={bar.get('bar_label')!r} "
                f"raw_diameter={bar.get('diameter_mm')!r}"
            )
            return None
        diameter_mm = float(diameter_mm)
        quantity = int(bar.get("quantity") or 1)
        steel_grade = str(bar.get("steel_grade") or "Y")
        bar_label = str(bar.get("bar_label") or "")
        bar_id = str(bar.get("bar_id") or "")
        spacing_mm = bar.get("spacing_mm")

        area_mm2 = math.pi * diameter_mm ** 2 / 4.0
        density = self._density()

        # Prefer explicit cut from upstream (Phase M.2 SpacerRuleEngine sets cut_length_mm)
        provided_cut = bar.get("cut_length_mm")
        try:
            provided_cut_f = float(provided_cut) if provided_cut is not None else None
        except (TypeError, ValueError):
            provided_cut_f = None

        cut_length_mm, source = self._derive_cut_length(
            role, diameter_mm, span_mm, depth_mm, width_mm, spacing_mm, quantity,
            provided_cut_mm=provided_cut_f,
        )

        weight_per_bar = area_mm2 * cut_length_mm * density / 1e9
        total_weight = weight_per_bar * quantity

        return BarSteelWeight(
            bar_id=bar_id,
            beam_id=beam_id,
            role=role,
            bar_label=bar_label,
            diameter_mm=diameter_mm,
            quantity=quantity,
            steel_grade=steel_grade,
            cut_length_mm=cut_length_mm,
            cut_length_source=source,
            area_mm2=area_mm2,
            weight_per_bar_kg=weight_per_bar,
            total_weight_kg=total_weight,
            formula_used=(
                f"W = (pi*{diameter_mm}^2/4)*{cut_length_mm:.0f}*{quantity}*"
                f"{density:.0f}/1e9"
            ),
        )

    def _derive_cut_length(
        self,
        role: str,
        d: float,
        span_mm: float,
        depth_mm: Optional[float],
        width_mm: Optional[float],
        spacing_mm: Optional[float],
        quantity: int,
        provided_cut_mm: Optional[float] = None,
    ) -> tuple:
        """
        Returns (cut_length_mm, source_description).
        Formula unchanged — only Ld/cover/hook parameter sources change.

        Phase M.2: SPACER uses width − 2×cover (or explicit cut_length_mm from
        SpacerRuleEngine). It must NOT use span + 2×Ld (longitudinal formula).
        """
        ld_source = "EngineeringContext" if self._loader else "IS456_40d_development"

        if role == "SPACER":
            if provided_cut_mm is not None and provided_cut_mm > 0:
                return float(provided_cut_mm), "SpacerRuleEngine_M.2"
            cover = self._cover_mm()
            if width_mm and float(width_mm) > 0:
                cut = float(width_mm) - 2.0 * float(cover)
                if cut > 0:
                    return cut, "spacer_width_minus_2cover"
            return 150.0, "spacer_default_150mm"

        if role in ("TOP_MAIN", "BOTTOM_MAIN", "TOP_EXTRA", "BOTTOM_EXTRA",
                    "SIDE_FACE", "BENT", "CRANKED", "DEVELOPMENT"):
            if span_mm > 0:
                ld = self._development_length_mm(d)
                cut_length = span_mm + 2 * ld
                return cut_length, ld_source
            else:
                cut_length = 2 * self._development_length_mm(d)
                return cut_length, f"{ld_source}_minimum_fallback"

        if role == "LAP":
            if span_mm > 0:
                ld = self._development_length_mm(d)
                return span_mm + 2 * ld, ld_source
            lap_mm = self._minimum_lap_mm(d)
            return float(lap_mm * 2), "EngineeringContext_lap_rule" if self._loader else "IS456_minimum_fallback"

        if role == "STIRRUP":
            D_eff = float(depth_mm) if depth_mm else 600.0
            W_eff = float(width_mm) if width_mm else 200.0
            cover = self._cover_mm()
            hook_mult = self._hook_multiple()
            perimeter = 2 * (W_eff - 2 * cover) + 2 * (D_eff - 2 * cover)
            hook = 2 * hook_mult * d
            cut_length = perimeter + hook
            src = "EngineeringContext_stirrup" if self._loader else "IS2502_stirrup_perimeter"
            return cut_length, src

        if span_mm > 0:
            ld = self._development_length_mm(d)
            return span_mm + 2 * ld, ld_source
        return 1000.0, "DEFAULT_FALLBACK"

    @staticmethod
    def area_mm2(diameter_mm: float) -> float:
        return math.pi * diameter_mm ** 2 / 4.0

    def weight_kg(self, diameter_mm: float, length_mm: float, quantity: int = 1) -> float:
        area = math.pi * diameter_mm ** 2 / 4.0
        density = self._density()
        return area * length_mm * quantity * density / 1e9
