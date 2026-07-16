"""
phase_r21d_orchestrator.py — Master orchestrator for Phase R.2.1D.
MODEL_VERSION: 7.12.1

Execution sequence:
  1. Load R.2.1C EngineeringFacts
  2. For each fact: build ObservableEvidence + rank IntentHypotheses
  3. Produce HypothesisEnrichedFact collection
  4. Validate (12 rules)
  5. Compute statistics
  6. Generate report
  7. Export all artefacts

Additive architecture:
  - Reads from R.2.1C output (never modifies it)
  - Writes exclusively to R.2.1D output directory
  - No existing production module is touched
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .evidence_builder import EvidenceBuilder
from .evidence_models import (
    HypothesisEnrichedFact,
    IntentHypothesis,
    INTENT_UNKNOWN,
)
from .hypothesis_export import HypothesisExport
from .hypothesis_ranker import HypothesisRanker
from .hypothesis_reporter import HypothesisReporter
from .hypothesis_statistics import HypothesisStatistics
from .hypothesis_validation import HypothesisValidation

MODEL_VERSION = "7.12.1"
PHASE_ID      = "R.2.1D"

_V7         = pathlib.Path(__file__).parent.parent.parent
_R21C_FACTS = (
    _V7 / "data/output/PhaseR2.1C_engineering_fact_normalization"
    / "EngineeringFacts.json"
)
_OUTPUT_DIR = _V7 / "data/output/PhaseR2.1D_evidence_hypothesis_engine"


class PhaseR21DOrchestrator:
    """
    Master orchestrator for Phase R.2.1D — Evidence & Intent Hypothesis Engine.
    """

    def __init__(
        self,
        r21c_facts_path: Optional[pathlib.Path] = None,
        output_dir:      Optional[pathlib.Path] = None,
    ):
        self.r21c_facts_path = pathlib.Path(r21c_facts_path) if r21c_facts_path else _R21C_FACTS
        self.output_dir      = pathlib.Path(output_dir)      if output_dir      else _OUTPUT_DIR

        self._ev_builder  = EvidenceBuilder()
        self._ranker      = HypothesisRanker()
        self._validator   = HypothesisValidation()
        self._statter     = HypothesisStatistics()
        self._reporter    = HypothesisReporter()
        self._exporter    = HypothesisExport()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        start = datetime.now()
        print(f"[R.2.1D] Evidence & Intent Hypothesis Engine — MODEL_VERSION {MODEL_VERSION}")
        print(f"[R.2.1D] Phase: {PHASE_ID}")
        print(f"[R.2.1D] Input: {self.r21c_facts_path}")
        print(f"[R.2.1D] Output: {self.output_dir}")
        print()

        # Step 1: Load R.2.1C facts
        facts_raw_by_beam = self._load_r21c_facts()
        total_in = sum(len(v) for v in facts_raw_by_beam.values())
        print(f"[R.2.1D] Loaded {total_in} R.2.1C facts from {len(facts_raw_by_beam)} beams")

        # Step 2: Build HypothesisEnrichedFacts
        enriched_by_beam, rules_log = self._build_all(facts_raw_by_beam)
        total_out = sum(len(v) for v in enriched_by_beam.values())
        total_hyp = sum(
            len(f.intent_hypotheses)
            for fl in enriched_by_beam.values()
            for f in fl
        )
        print(f"[R.2.1D] Built {total_out} HypothesisEnrichedFacts ({total_hyp} hypotheses)")

        # Log which reorder rules fired
        rules_fired_total = sum(len(v) for v in rules_log.values())
        print(f"[R.2.1D] Reorder rules applied: {rules_fired_total} times")

        # Step 3: Validate
        validation  = self._validator.validate(enriched_by_beam)
        v_summary   = validation.get("summary", "")
        v_all_pass  = validation.get("all_pass", False)
        ok_icon     = "OK" if v_all_pass else "FAIL"
        print(f"[R.2.1D] Validation: [{ok_icon}] {v_summary}")

        # Step 4: Statistics
        stats = self._statter.compute(enriched_by_beam, rules_log)

        # Step 5: Report
        report_md = self._reporter.generate(enriched_by_beam, stats, validation)

        # Step 6: Export
        self.output_dir.mkdir(parents=True, exist_ok=True)
        exported = self._exporter.export_all(
            enriched_by_beam, stats, validation, report_md, self.output_dir
        )
        print(f"[R.2.1D] Exported {len(exported)} artefacts to {self.output_dir}")

        elapsed = (datetime.now() - start).total_seconds()
        result = {
            "phase_id":           PHASE_ID,
            "model_version":      MODEL_VERSION,
            "beam_count":         len(enriched_by_beam),
            "total_facts":        total_out,
            "total_hypotheses":   total_hyp,
            "validation":         validation,
            "statistics":         stats,
            "exported_artefacts": {k: str(v) for k, v in exported.items()},
            "elapsed_seconds":    round(elapsed, 2),
            "success":            v_all_pass,
        }

        print()
        print(f"[R.2.1D] Completed in {elapsed:.2f}s — {v_summary}")
        if not v_all_pass:
            self._print_failures(validation)

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_r21c_facts(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.r21c_facts_path.exists():
            raise FileNotFoundError(
                f"R.2.1C facts not found: {self.r21c_facts_path}\n"
                "Run Phase R.2.1C first: python Version7/Run_PY/run_phase_r21c_engineering_fact_normalization.py"
            )
        with self.r21c_facts_path.open(encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "by_beam" in data:
            return data["by_beam"]
        if isinstance(data, dict):
            return data
        raise ValueError(f"Unexpected R.2.1C facts structure in {self.r21c_facts_path}")

    def _build_all(
        self,
        facts_raw_by_beam: Dict[str, List[Dict[str, Any]]],
    ) -> Tuple[Dict[str, List[HypothesisEnrichedFact]], Dict[str, List[str]]]:
        """Build HypothesisEnrichedFacts for all beams. Returns (enriched, rules_log)."""
        enriched_by_beam: Dict[str, List[HypothesisEnrichedFact]] = {}
        rules_log:        Dict[str, List[str]] = {}

        for beam_id, raw_facts in facts_raw_by_beam.items():
            beam_enriched = []
            for fd in raw_facts:
                fact, applied = self._build_one(fd, beam_id)
                beam_enriched.append(fact)
                if applied:
                    rules_log[fd.get("annotation_id", "")] = applied
            enriched_by_beam[beam_id] = beam_enriched

        return enriched_by_beam, rules_log

    def _build_one(
        self,
        fact_dict: Dict[str, Any],
        beam_id:   str,
    ) -> Tuple[HypothesisEnrichedFact, List[str]]:
        """Build one HypothesisEnrichedFact from a R.2.1C fact dict."""
        # Ensure beam_id in dict
        if not fact_dict.get("beam_id"):
            fact_dict = {**fact_dict, "beam_id": beam_id}

        # Build ObservableEvidence
        evidence = self._ev_builder.build(fact_dict)

        # Rank hypotheses using observable signals
        ev_signals = {
            "r1_original_role": evidence.r1_original_role,
            "modifiers":        evidence.modifiers,
            "semantic_flags":   evidence.semantic_flags,
            "diameter":         evidence.diameter,
        }
        hypotheses, applied = self._ranker.rank(
            role      = str(fact_dict.get("role") or "UNKNOWN"),
            placement = str(fact_dict.get("placement") or "UNKNOWN"),
            evidence  = ev_signals,
        )

        # intent_candidates preserved for backward compat
        intent_candidates = [h.intent for h in hypotheses]

        return HypothesisEnrichedFact(
            annotation_id          = str(fact_dict.get("annotation_id") or ""),
            beam_id                = beam_id,
            clean_text             = str(fact_dict.get("clean_text") or ""),
            quantity               = int(fact_dict.get("quantity") or 0),
            diameter               = float(fact_dict.get("diameter") or 0.0),
            grade                  = str(fact_dict.get("grade") or "Y460"),
            spacing                = fact_dict.get("spacing"),
            role                   = str(fact_dict.get("role") or "UNKNOWN"),
            placement              = str(fact_dict.get("placement") or "UNKNOWN"),
            intent                 = INTENT_UNKNOWN,
            modifiers              = list(fact_dict.get("modifiers") or []),
            semantic_flags         = list(fact_dict.get("semantic_flags") or []),
            confidence             = str(fact_dict.get("confidence") or "LOW"),
            source                 = str(fact_dict.get("source") or "UNKNOWN"),
            engineering_notes      = list(fact_dict.get("engineering_notes") or []),
            geometry_required      = bool(fact_dict.get("geometry_required", True)),
            intent_deferred_reason = str(fact_dict.get("intent_deferred_reason") or ""),
            observable_evidence    = evidence,
            intent_hypotheses      = hypotheses,
            intent_candidates      = intent_candidates,
        ), applied

    @staticmethod
    def _print_failures(validation: Dict[str, Any]) -> None:
        for rule_id, result in validation.get("rules", {}).items():
            if not result["passed"]:
                print(f"  [FAIL] {rule_id}: {result['detail']}")
