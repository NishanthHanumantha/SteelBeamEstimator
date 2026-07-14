"""
Phase SI.1 Orchestrator — Stirrup Improvement Engine
MODEL_VERSION: 6.6.1

Orchestration sequence:
  1. Load L.2 reinforcement models
  2. Parse stirrup notation (MODULE 1)
  3. Build engineering zones (MODULE 2)
  4. Distribute zones (MODULE 3)
  5. Calculate quantities (MODULE 4)
  6. Compute steel weights (MODULE 6)
  7. Validate (MODULE 7)
  8. Generate statistics (MODULE 8)
  9. Build report (MODULE 9)
  10. Export JSON artefacts (MODULE 10)

Also provides StirrupImprover.compute_beam() — a single-beam interface
used by Phase V.B.1 bbs_completion_engine.py to replace ONLY the
stirrup portion of the BBS generation.
"""
import json
import math
import pathlib
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

_SRC = pathlib.Path(__file__).parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from stirrup_models import (
    StirrupType, ZoneRole, ParsedStirrupNotation,
    StirrupZone, StirrupGroup, BeamStirrupResult, StirrupEngineResult,
)
from stirrup_notation_parser import StirrupNotationParser
from stirrup_zone_builder import StirrupZoneBuilder
from stirrup_distribution_engine import StirrupDistributionEngine
from stirrup_quantity_engine import StirrupQuantityEngine
from stirrup_weight_engine import StirrupWeightEngine
from stirrup_bbs_builder import StirrupBBSBuilder, group_to_bbs_dict
from stirrup_validator import StirrupValidator, STIRRUP_ENGINE_ERROR
from stirrup_statistics import compute_statistics
from stirrup_reporter import StirrupReporter
from stirrup_export import StirrupExport

_BASE = pathlib.Path(__file__).parents[3]
_V6   = _BASE / "Version7"
_L2_PATH = (
    _V6 / "data/output/PhaseL.2 - engineering_reinforcement_interpretation"
    / "beam_reinforcement_models.json"
)
_OUT_DIR = _V6 / "data/output/PhaseSI.1_stirrup_improvement"

_L2_ROLE_KEY = "stirrups"


class StirrupImprover:
    """
    Single-beam interface consumed by Phase V.B.1 bbs_completion_engine.

    Usage:
        imp = StirrupImprover()
        bbs_dicts = imp.compute_beam(bar_dict, span_mm, depth_mm, width_mm)
        # bbs_dicts is a list of one or more BBSRow-compatible dicts
    """

    def __init__(self) -> None:
        self._parser  = StirrupNotationParser()
        self._zones   = StirrupZoneBuilder()
        self._dist    = StirrupDistributionEngine()
        self._qty     = StirrupQuantityEngine()
        self._weight  = StirrupWeightEngine()
        self._bbs     = StirrupBBSBuilder()

    def compute_beam(
        self,
        bar: Dict[str, Any],
        beam_id: str,
        span_mm: float,
        depth_mm: Optional[float],
        width_mm: Optional[float],
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of BBS row dicts for this stirrup bar.
        Replaces the single-row stirrup logic in V.B.1.

        If the notation is not parseable (e.g. "2Y16" with no spacing),
        falls back to a single legacy row with span-based quantity.
        """
        d_mm   = float(bar.get("diameter_mm") or 8)
        label  = str(bar.get("bar_label") or "")
        grade  = str(bar.get("steel_grade") or "Y")
        spc_mm = bar.get("spacing_mm")
        legs   = 2

        D = float(depth_mm or 600)
        W = float(width_mm or 200)

        parsed = self._parser.parse(
            label,
            fallback_spacing_mm=spc_mm,
            fallback_diameter_mm=d_mm,
            fallback_legs=legs,
            fallback_grade=grade,
        )

        # Not parseable / no spacing → legacy fallback
        if not parsed.is_parseable or not parsed.spacings_mm:
            return self._legacy_row(bar, beam_id, d_mm, D, W, span_mm, label, grade)

        zones  = self._zones.build(parsed, span_mm)
        groups = self._dist.distribute(zones, parsed.stirrup_type)
        cut_mm = self._weight.cut_length_mm(d_mm, W, D)

        bbs_rows = []
        for gi, grp_zones in enumerate(groups):
            qty = self._qty.calculate(grp_zones, parsed.stirrup_type, span_mm)
            is_merged = (
                any(z.role == ZoneRole.LEFT_SUPPORT for z in grp_zones)
                and any(z.role == ZoneRole.RIGHT_SUPPORT for z in grp_zones)
            )
            merge_note = "Left+Right support merged (same spacing)" if is_merged else ""
            spacing = grp_zones[0].spacing_mm

            w_total = self._weight.total_weight_kg(parsed.diameter_mm, cut_mm, qty)

            group = StirrupGroup(
                group_id=f"{beam_id}_STIRRUP_{gi}",
                beam_id=beam_id,
                diameter_mm=parsed.diameter_mm,
                steel_grade=grade,
                legs=parsed.legs,
                spacing_mm=spacing,
                zones=grp_zones,
                quantity=qty,
                cut_length_mm=cut_mm,
                weight_per_unit_kg=self._weight.weight_per_unit_kg(parsed.diameter_mm, cut_mm),
                total_weight_kg=w_total,
                is_merged=is_merged,
                merge_note=merge_note,
            )
            bbs_rows.append(group_to_bbs_dict(group, beam_id))

        return bbs_rows

    def _legacy_row(
        self,
        bar: Dict[str, Any],
        beam_id: str,
        d_mm: float,
        depth_mm: float,
        width_mm: float,
        span_mm: float,
        label: str,
        grade: str,
    ) -> List[Dict[str, Any]]:
        """Produces a single legacy BBS row when notation has no spacing."""
        cut_mm = self._weight.cut_length_mm(d_mm, width_mm, depth_mm)
        qty = int(bar.get("quantity") or 2)
        # If span available and no @ in label, compute from span
        if span_mm > 0 and "@" not in label:
            qty = int(bar.get("quantity") or 2)   # keep bar quantity as-is

        w = self._weight.total_weight_kg(d_mm, cut_mm, qty)
        d_key = int(d_mm)

        dw = {k: None for k in ["weight_d8","weight_d10","weight_d12",
                                  "weight_d16","weight_d20","weight_d25","weight_d32"]}
        col_map = {8:"weight_d8",10:"weight_d10",12:"weight_d12",
                   16:"weight_d16",20:"weight_d20",25:"weight_d25",32:"weight_d32"}
        if d_key in col_map:
            dw[col_map[d_key]] = round(w, 3)

        return [{
            "si_no": None,
            "frame_type": "TF",
            "description": "Stirrups",
            "diameter_mm": d_mm,
            "spacing_m": None,
            "quantity": qty,
            "dvlp_length_m": round(2*10*d_mm/1000, 3),
            "cut_length_m": round(cut_mm/1000, 3),
            "total_length_m": round(cut_mm*qty/1000, 3),
            **dw,
            "total_weight_kg": round(w, 3),
            "is_beam_header": False,
            "beam_id": beam_id,
        }]


class PhaseSI1Orchestrator:
    """Full Phase SI.1 orchestrator — runs all 10 modules."""

    MODEL_VERSION = "6.6.1"

    def __init__(
        self,
        l2_path: Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
    ) -> None:
        self.l2_path   = l2_path or _L2_PATH
        self.output_dir = output_dir or _OUT_DIR
        self._improver = StirrupImprover()

    # ── public ──────────────────────────────────────────────────────────────

    def run(self) -> StirrupEngineResult:
        print("=" * 70)
        print("PHASE SI.1 — STIRRUP IMPROVEMENT ENGINE")
        print(f"MODEL_VERSION: {self.MODEL_VERSION}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Load L.2 models
        l2_data = json.loads(self.l2_path.read_text(encoding="utf-8"))
        models  = l2_data.get("models", [])
        print(f"\nL.2 models loaded: {len(models)}")

        beam_results: List[BeamStirrupResult] = []

        for model in models:
            br = self._process_beam(model)
            if br is not None:
                beam_results.append(br)

        # Aggregate
        total_uniform  = sum(1 for b in beam_results if b.stirrup_type == StirrupType.UNIFORM)
        total_variable = sum(1 for b in beam_results if b.stirrup_type == StirrupType.VARIABLE)
        total_qty      = sum(b.total_quantity for b in beam_results)
        total_wt       = sum(b.total_weight_kg for b in beam_results)
        old_wt         = sum(b.old_weight_kg for b in beam_results)
        merged_rows    = sum(
            1 for b in beam_results for g in b.groups if g.is_merged
        )

        diam_totals: Dict[int, float] = {}
        for br in beam_results:
            for g in br.groups:
                d = int(g.diameter_mm)
                diam_totals[d] = round(diam_totals.get(d, 0.0) + g.total_weight_kg, 3)

        # Validate
        validator = StirrupValidator()
        passed, errors = validator.validate_all(beam_results)

        result = StirrupEngineResult(
            beam_results=beam_results,
            total_uniform_beams=total_uniform,
            total_variable_beams=total_variable,
            total_merged_rows=merged_rows,
            total_quantity=total_qty,
            total_weight_kg=total_wt,
            old_total_weight_kg=old_wt,
            diameter_totals_kg=diam_totals,
            validation_passed=passed,
            validation_errors=errors,
        )

        # Statistics
        stats = compute_statistics(beam_results)

        # Report
        reporter = StirrupReporter(result, stats)
        report   = reporter.build()

        # Export
        exporter = StirrupExport(self.output_dir)
        paths    = exporter.export_all(report, stats, beam_results)

        self._print_summary(result, stats, paths)

        if not passed:
            raise STIRRUP_ENGINE_ERROR(
                f"Validation failed: {'; '.join(errors)}"
            )

        return result

    # ── private ─────────────────────────────────────────────────────────────

    def _process_beam(self, model: Dict[str, Any]) -> Optional[BeamStirrupResult]:
        beam_id = model.get("beam_id", "")
        geom    = model.get("geometry") or {}
        span_mm = float(geom.get("clear_span_mm") or 0)
        depth_mm= float(geom.get("depth_mm") or 600)
        width_mm= float(geom.get("width_mm") or 200)

        stirrups = model.get(_L2_ROLE_KEY) or []
        if not stirrups:
            return None

        # Use first stirrup bar (typically one entry per beam)
        bar = stirrups[0]
        d_mm   = float(bar.get("diameter_mm") or 8)
        label  = str(bar.get("bar_label") or "")
        grade  = str(bar.get("steel_grade") or "Y")
        spc_mm = bar.get("spacing_mm")

        parsed = self._improver._parser.parse(
            label,
            fallback_spacing_mm=spc_mm,
            fallback_diameter_mm=d_mm,
            fallback_legs=2,
            fallback_grade=grade,
        )

        # Old engine quantity (for comparison)
        legacy_spc = parsed.spacings_mm[0] if parsed.spacings_mm else (int(spc_mm) if spc_mm else 100)
        cut_mm = self._improver._weight.cut_length_mm(d_mm, width_mm, depth_mm)
        old_qty = self._improver._qty.legacy_quantity(span_mm, legacy_spc)
        old_wt  = self._improver._weight.total_weight_kg(d_mm, cut_mm, old_qty)

        # New engine
        if not parsed.is_parseable or not parsed.spacings_mm:
            qty = int(bar.get("quantity") or 2)
            w   = self._improver._weight.total_weight_kg(d_mm, cut_mm, qty)
            group = StirrupGroup(
                group_id=f"{beam_id}_STIRRUP_0",
                beam_id=beam_id,
                diameter_mm=d_mm, steel_grade=grade, legs=2,
                spacing_mm=0, zones=[], quantity=qty,
                cut_length_mm=cut_mm,
                weight_per_unit_kg=self._improver._weight.weight_per_unit_kg(d_mm, cut_mm),
                total_weight_kg=w,
            )
            return BeamStirrupResult(
                beam_id=beam_id, span_mm=span_mm, depth_mm=depth_mm, width_mm=width_mm,
                stirrup_type=StirrupType.UNIFORM, groups=[group],
                total_quantity=qty, total_weight_kg=w,
                old_quantity=old_qty, old_weight_kg=old_wt,
                parse_note=parsed.parse_note,
            )

        zones  = self._improver._zones.build(parsed, span_mm)
        groups_raw = self._improver._dist.distribute(zones, parsed.stirrup_type)

        groups: List[StirrupGroup] = []
        total_qty = 0
        total_wt  = 0.0

        for gi, grp_zones in enumerate(groups_raw):
            qty = self._improver._qty.calculate(grp_zones, parsed.stirrup_type, span_mm)
            is_merged = (
                any(z.role == ZoneRole.LEFT_SUPPORT for z in grp_zones)
                and any(z.role == ZoneRole.RIGHT_SUPPORT for z in grp_zones)
            )
            spacing = grp_zones[0].spacing_mm
            w_total = self._improver._weight.total_weight_kg(parsed.diameter_mm, cut_mm, qty)

            groups.append(StirrupGroup(
                group_id=f"{beam_id}_STIRRUP_{gi}",
                beam_id=beam_id,
                diameter_mm=parsed.diameter_mm,
                steel_grade=grade,
                legs=parsed.legs,
                spacing_mm=spacing,
                zones=grp_zones,
                quantity=qty,
                cut_length_mm=cut_mm,
                weight_per_unit_kg=self._improver._weight.weight_per_unit_kg(parsed.diameter_mm, cut_mm),
                total_weight_kg=w_total,
                is_merged=is_merged,
                merge_note="Left+Right support merged" if is_merged else "",
            ))
            total_qty += qty
            total_wt  += w_total

        return BeamStirrupResult(
            beam_id=beam_id, span_mm=span_mm, depth_mm=depth_mm, width_mm=width_mm,
            stirrup_type=parsed.stirrup_type,
            groups=groups,
            total_quantity=total_qty, total_weight_kg=total_wt,
            old_quantity=old_qty, old_weight_kg=old_wt,
        )

    def _print_summary(
        self,
        result: StirrupEngineResult,
        stats: Dict[str, Any],
        paths: Dict[str, pathlib.Path],
    ) -> None:
        print("\n" + "=" * 70)
        print("PHASE SI.1 COMPLETE")
        print("=" * 70)
        print(f"  Beams with stirrups:   {len(result.beam_results)}")
        print(f"  Uniform beams:         {result.total_uniform_beams}")
        print(f"  Variable beams:        {result.total_variable_beams}")
        print(f"  Merged support rows:   {result.total_merged_rows}")
        print(f"  Total stirrup qty:     {result.total_quantity}")
        print(f"\nSteel Weight Comparison:")
        print(f"  Old engine total:      {result.old_total_weight_kg:.3f} kg")
        print(f"  New engine total:      {result.total_weight_kg:.3f} kg")
        print(f"  Change:                {result.total_weight_kg - result.old_total_weight_kg:+.3f} kg")
        print(f"\nDiameter Totals (new engine):")
        for d, w in sorted(result.diameter_totals_kg.items()):
            print(f"  Y{d:2d}: {w:.3f} kg")
        print(f"\nValidation: {'PASS' if result.validation_passed else 'FAIL'}")
        print(f"JSON Reports: {len(paths)} files exported -> {self.output_dir}")
        print("=" * 70)
