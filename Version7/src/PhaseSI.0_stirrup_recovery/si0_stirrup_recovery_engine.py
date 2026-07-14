"""
Stirrup Recovery Engine — Phase SI.0 MODULE 5

For every beam model:
  • validate existing STIRRUP objects
  • if valid → retain (BENCHMARK_RETAINED)
  • if invalid → attempt recovery in priority order:
      1. Direct annotation match
      2. Shared drawing group
      3. Span-proximity candidate
      4. IS 456 engineering inference
  • if beam has no stirrup entry → skip (not our concern)
"""
from typing import List, Dict, Any, Optional

from si0_stirrup_recovery_models import (
    BeamRecoveryResult, RecoveryDecision, RecoverySource,
    InvalidReason, StirrupCandidate,
)
from si0_stirrup_role_validator import is_valid_stirrup, is_invalid_label
from si0_stirrup_geometry_matcher import StirrupGeometryMatcher
from si0_stirrup_annotation_parser import parse_stirrup_callout

_MATCHER = StirrupGeometryMatcher()

# Beams confirmed as benchmark — must NEVER be overwritten
BENCHMARK_BEAMS = {"B1", "B2", "B8", "B9", "B10"}


class StirrupRecoveryEngine:
    """
    Main decision engine: validates and recovers one beam at a time.
    """

    def recover_beam(
        self,
        model: Dict[str, Any],
        candidates: List[StirrupCandidate],
    ) -> BeamRecoveryResult:
        beam_id = str(model.get("beam_id", ""))
        geom    = model.get("geometry") or {}
        span_mm = float(geom.get("clear_span_mm") or 0)
        depth   = geom.get("depth_mm")
        width   = geom.get("width_mm")

        stirrups = model.get("stirrups") or []

        # Beam has no stirrup entry at all → skip
        if not stirrups:
            return BeamRecoveryResult(
                beam_id=beam_id,
                span_mm=span_mm,
                depth_mm=depth,
                width_mm=width,
                decision=RecoveryDecision.RETAINED,
                source=RecoverySource.NO_STIRRUP,
                invalid_reason=None,
                original_label=None,
                recovered_label=None,
                recovered_diameter_mm=None,
                recovered_spacing_mm=None,
                engineering_evidence="Beam has no stirrup entries in L.2",
            )

        bar = stirrups[0]
        label = str(bar.get("bar_label") or "")
        valid, reason = is_valid_stirrup(bar)

        # Benchmark beams must always be retained unchanged
        if beam_id in BENCHMARK_BEAMS:
            return BeamRecoveryResult(
                beam_id=beam_id,
                span_mm=span_mm,
                depth_mm=depth,
                width_mm=width,
                decision=RecoveryDecision.RETAINED,
                source=RecoverySource.BENCHMARK,
                invalid_reason=None,
                original_label=label,
                recovered_label=label,
                recovered_diameter_mm=float(bar.get("diameter_mm") or 8),
                recovered_spacing_mm=float(bar.get("spacing_mm") or 0),
                recovery_confidence=1.0,
                engineering_evidence=f"Benchmark beam {beam_id}: retained unchanged",
                traceability={"phase": "SI.0", "decision": "BENCHMARK_PROTECTED"},
            )

        if valid:
            return BeamRecoveryResult(
                beam_id=beam_id,
                span_mm=span_mm,
                depth_mm=depth,
                width_mm=width,
                decision=RecoveryDecision.RETAINED,
                source=RecoverySource.BENCHMARK,
                invalid_reason=None,
                original_label=label,
                recovered_label=label,
                recovered_diameter_mm=float(bar.get("diameter_mm") or 8),
                recovered_spacing_mm=float(bar.get("spacing_mm") or 0),
                recovery_confidence=1.0,
                engineering_evidence=f"{beam_id}: existing stirrup is valid",
            )

        # ── INVALID: attempt recovery ─────────────────────────────────────────
        candidate, src_str, evidence = _MATCHER.match(beam_id, span_mm, candidates)

        if candidate is not None:
            parsed = parse_stirrup_callout(candidate.callout)
            src_enum = RecoverySource(src_str) if src_str in RecoverySource._value2member_map_ else RecoverySource.INFERENCE

            return BeamRecoveryResult(
                beam_id=beam_id,
                span_mm=span_mm,
                depth_mm=depth,
                width_mm=width,
                decision=RecoveryDecision.RECOVERED,
                source=src_enum,
                invalid_reason=reason,
                original_label=label,
                recovered_label=parsed["bar_label"],
                recovered_diameter_mm=parsed["diameter_mm"],
                recovered_spacing_mm=float(parsed["spacings_mm"][0]) if parsed["spacings_mm"] else None,
                recovered_spacings_mm=parsed["spacings_mm"],
                recovered_legs=parsed["legs"],
                recovery_confidence=candidate.confidence,
                engineering_evidence=evidence,
                traceability={
                    "phase": "SI.0",
                    "decision": "RECOVERED",
                    "source": src_str,
                    "candidate_feature_id": candidate.feature_id,
                    "original_label": label,
                    "recovered_label": parsed["bar_label"],
                },
            )

        # ── Inference fallback ────────────────────────────────────────────────
        inferred_label, dia, spc, conf = _MATCHER.infer_stirrup(span_mm)
        parsed = parse_stirrup_callout(inferred_label)

        return BeamRecoveryResult(
            beam_id=beam_id,
            span_mm=span_mm,
            depth_mm=depth,
            width_mm=width,
            decision=RecoveryDecision.RECOVERED,
            source=RecoverySource.INFERENCE,
            invalid_reason=reason,
            original_label=label,
            recovered_label=inferred_label,
            recovered_diameter_mm=dia,
            recovered_spacing_mm=spc,
            recovered_spacings_mm=parsed["spacings_mm"],
            recovered_legs=2,
            recovery_confidence=conf,
            engineering_evidence=(
                f"{beam_id} span={span_mm:.0f}mm: IS 456 engineering inference → {inferred_label}"
            ),
            traceability={
                "phase": "SI.0",
                "decision": "RECOVERED",
                "source": "ENGINEERING_INFERENCE",
                "rule": "IS456_Table26_MinimumShearReinforcement",
                "original_label": label,
                "recovered_label": inferred_label,
            },
        )
