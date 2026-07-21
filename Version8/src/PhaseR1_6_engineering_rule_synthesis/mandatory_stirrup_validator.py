"""
RULE-012 mandatory stirrup coverage validator — detection only.
MODEL_VERSION: 8.8.2
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from beam_coverage_model import (
    MODEL_VERSION,
    RULE_ID,
    BeamCoverageRecord,
    ObjectLevelCoverage,
    StagePresence,
)
from coverage_engine import natural_beam_key


class MandatoryStirrupValidator:
    """Per-beam PASS/FAIL/UNKNOWN with pipeline traceability. No corrections."""

    def validate_all(self, inputs: Dict[str, Any]) -> List[BeamCoverageRecord]:
        beam_ids: List[str] = list(inputs.get("beam_ids") or [])
        stage: Dict[str, Set[str]] = inputs.get("stage_stirrup") or {}
        top_beams: Set[str] = set(inputs.get("top_beams") or set())
        bottom_beams: Set[str] = set(inputs.get("bottom_beams") or set())

        records: List[BeamCoverageRecord] = []
        for beam_id in sorted(beam_ids, key=natural_beam_key):
            records.append(
                self.validate_beam(
                    beam_id=beam_id,
                    beam_exists=True,
                    top_exists=beam_id in top_beams,
                    bottom_exists=beam_id in bottom_beams,
                    stage_stirrup=stage,
                )
            )
        return records

    def validate_beam(
        self,
        beam_id: str,
        beam_exists: bool,
        top_exists: bool,
        bottom_exists: bool,
        stage_stirrup: Dict[str, Set[str]],
    ) -> BeamCoverageRecord:
        if not beam_id or not str(beam_id).strip():
            return BeamCoverageRecord(
                beam_id=str(beam_id or ""),
                beam_exists=False,
                top_exists=False,
                bottom_exists=False,
                stirrup_exists=False,
                status="UNKNOWN",
                stage_presence=StagePresence(False, False, False, False, False),
                object_level=ObjectLevelCoverage(False, False, False, False),
                likely_missing_phase=None,
                missing_object="Beam ID",
                evidence=("empty_beam_id",),
                engineering_severity="UNKNOWN",
                engineering_impact="Cannot validate stirrup coverage without a beam identity.",
                expected_stirrup="YES",
                detected_stirrup="UNKNOWN",
            )

        ann = beam_id in (stage_stirrup.get("Annotation Discovery") or set())
        intent = beam_id in (stage_stirrup.get("Intent Resolution") or set())
        detail = beam_id in (stage_stirrup.get("Reinforcement Detail") or set())
        piece = beam_id in (stage_stirrup.get("Piece Generation") or set())
        ebar = beam_id in (stage_stirrup.get("EngineeringBars") or set())

        presence = StagePresence(
            annotation=ann,
            intent=intent,
            detail=detail,
            piece=piece,
            engineering_bar=ebar,
        )
        objects = ObjectLevelCoverage(
            intent=intent,
            detail=detail,
            piece=piece,
            engineering_bar=ebar,
        )

        # Engineering invariant: Intent → Detail → EngineeringBar (Piece included).
        stirrup_ok = intent and detail and piece and ebar
        stirrup_any = ann or intent or detail or piece or ebar

        if not beam_exists:
            status = "UNKNOWN"
        elif stirrup_ok:
            status = "PASS"
        else:
            status = "FAIL"

        missing_phase = None if stirrup_ok else presence.first_missing_stage()
        missing_object = None
        if status == "FAIL":
            missing_object = self._missing_object(presence)

        evidence = self._evidence(beam_id, presence, top_exists, bottom_exists)
        severity, impact = self._severity_impact(
            status=status,
            top_exists=top_exists,
            bottom_exists=bottom_exists,
            stirrup_any=stirrup_any,
            missing_phase=missing_phase,
        )

        return BeamCoverageRecord(
            beam_id=beam_id,
            beam_exists=beam_exists,
            top_exists=top_exists,
            bottom_exists=bottom_exists,
            stirrup_exists=stirrup_ok,
            status=status,
            stage_presence=presence,
            object_level=objects,
            likely_missing_phase=missing_phase,
            missing_object=missing_object,
            evidence=evidence,
            engineering_severity=severity,
            engineering_impact=impact,
            expected_stirrup="YES",
            detected_stirrup="YES" if stirrup_ok else ("PARTIAL" if stirrup_any else "NO"),
        )

    @staticmethod
    def _missing_object(presence: StagePresence) -> str:
        if not presence.annotation:
            return "STIRRUP Annotation"
        if not presence.intent:
            return "STIRRUP Intent"
        if not presence.detail:
            return "STIRRUP Detail"
        if not presence.piece:
            return "STIRRUP Piece"
        if not presence.engineering_bar:
            return "STIRRUP EngineeringBar"
        return "STIRRUP Representation"

    @staticmethod
    def _evidence(
        beam_id: str,
        presence: StagePresence,
        top_exists: bool,
        bottom_exists: bool,
    ) -> Tuple[str, ...]:
        flags = [
            f"beam_id={beam_id}",
            f"annotation_stirrup={'YES' if presence.annotation else 'NO'}",
            f"intent_stirrup={'YES' if presence.intent else 'NO'}",
            f"detail_stirrup={'YES' if presence.detail else 'NO'}",
            f"piece_stirrup={'YES' if presence.piece else 'NO'}",
            f"engineeringbar_stirrup={'YES' if presence.engineering_bar else 'NO'}",
            f"top={'YES' if top_exists else 'NO'}",
            f"bottom={'YES' if bottom_exists else 'NO'}",
            f"rule={RULE_ID}",
            f"model_version={MODEL_VERSION}",
        ]
        return tuple(flags)

    @staticmethod
    def _severity_impact(
        status: str,
        top_exists: bool,
        bottom_exists: bool,
        stirrup_any: bool,
        missing_phase: Optional[str],
    ) -> Tuple[str, str]:
        if status == "PASS":
            return "NONE", "Stirrup representation present through Intent → Detail → Piece → EngineeringBar."
        if status == "UNKNOWN":
            return "UNKNOWN", "Insufficient identity/evidence to validate mandatory stirrup coverage."

        if not stirrup_any:
            severity = "CRITICAL"
            impact = (
                "No stirrup representation at any pipeline stage. "
                "Shear reinforcement absent; cage integrity cannot be guaranteed; "
                "steel weight will under-report stirrups."
            )
        elif top_exists and bottom_exists:
            severity = "HIGH"
            impact = (
                "Top and bottom reinforcement present but stirrup chain incomplete. "
                "Cage integrity and shear reinforcement are compromised at "
                f"{missing_phase or 'unknown stage'}."
            )
        else:
            severity = "HIGH"
            impact = (
                "Stirrup representation lost or incomplete in the pipeline. "
                f"Likely missing phase: {missing_phase or 'unknown'}."
            )
        return severity, impact

    def diagnostics(self, records: List[BeamCoverageRecord]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for r in records:
            if r.status != "FAIL":
                continue
            rows.append({
                "beam_id": r.beam_id,
                "expected_stirrup": r.expected_stirrup,
                "detected_stirrup": r.detected_stirrup,
                "coverage_status": r.status,
                "likely_missing_phase": r.likely_missing_phase,
                "missing_object": r.missing_object,
                "supporting_evidence": list(r.evidence),
                "engineering_severity": r.engineering_severity,
                "engineering_impact": r.engineering_impact,
                "top_exists": r.top_exists,
                "bottom_exists": r.bottom_exists,
                "pipeline_stage_presence": r.stage_presence.to_dict(),
                "rule_id": RULE_ID,
            })
        return rows
