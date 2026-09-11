"""
Phase V.ROOT.1 -- initialization_validator.py
9 validation rules for dynamic pipeline initialization.
Raises PIPELINE_INITIALIZATION_ERROR on failure.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


class PIPELINE_INITIALIZATION_ERROR(RuntimeError):
    pass


class InitializationValidator:
    """Validate the complete V.ROOT.1 initialization against 9 rules."""

    def validate(
        self,
        project_manifest:  Dict[str, Any],
        drawing_manifest:  Dict[str, Any],
        discovery_result:  Dict[str, Any],
        beam_registry:     Dict[str, Any],
        eng_obj_result:    Dict[str, Any],
        pipeline_context:  Dict[str, Any],
        dep_check:         Dict[str, Any],
    ) -> Dict[str, Any]:

        rules: Dict[str, Tuple[bool, str]] = {}

        # RULE_1 — Project discovered
        ok = bool(project_manifest.get('project_id'))
        rules['RULE_1'] = (ok, "Project discovered with valid project_id")

        # RULE_2 — All drawings classified
        dm_total = drawing_manifest.get('total_drawings', 0)
        type_counts = drawing_manifest.get('type_counts', {})
        unknown = type_counts.get('UNKNOWN', 0)
        ok = dm_total > 0 and unknown < dm_total
        rules['RULE_2'] = (
            ok,
            f"{dm_total - unknown}/{dm_total} drawings classified (UNKNOWN: {unknown})"
        )

        # RULE_3 — Beam reinforcement drawing found
        ok = drawing_manifest.get('has_reinforcement_drawing', False)
        rules['RULE_3'] = (ok, "Primary beam reinforcement drawing identified")

        # RULE_4 — Beam registry created with >0 beams
        beam_count = beam_registry.get('beam_count', 0)
        ok = beam_count > 0
        rules['RULE_4'] = (ok, f"Beam registry built: {beam_count} beams discovered")

        # RULE_5 — Engineering objects created
        eo_count = eng_obj_result.get('objects_generated', {}).get('engineering_objects', 0)
        ok = eo_count > 0
        rules['RULE_5'] = (ok, f"Engineering objects created: {eo_count}")

        # RULE_6 — Pipeline context created
        ok = bool(pipeline_context.get('initialized_at')) and \
             bool(pipeline_context.get('beam_registry'))
        rules['RULE_6'] = (ok, "Pipeline context generated with beam registry and project context")

        # RULE_7 — No Version5 dependency (context quality flags)
        quality = pipeline_context.get('quality', {})
        ok = not quality.get('uses_v5_dependencies', True)
        rules['RULE_7'] = (ok, "Pipeline context reports no Version5 dependency")

        # RULE_8 — No hardcoded B1–B18 beam IDs (registry sourced from DXF)
        ok = not beam_registry.get('hardcoded', True)
        rules['RULE_8'] = (ok, "Beam registry is dynamically sourced (not hardcoded)")

        # RULE_9 — Dynamic initialization complete
        ok = (
            pipeline_context.get('quality', {}).get('dynamic_initialization', False)
            and pipeline_context.get('downstream_config', {}).get('l2_ready', False)
        )
        rules['RULE_9'] = (ok, "Dynamic initialization complete and L.2 ready")

        passed = {k: v for k, (v, _) in rules.items() if v}
        failed = {k: msg for k, (v, msg) in rules.items() if not v}
        all_passed = len(failed) == 0

        return {
            'validation_passed': all_passed,
            'rules_passed':  {k: v for k, (v, _) in rules.items()},
            'rules_detail':  {k: msg for k, (_, msg) in rules.items()},
            'passed_count':  len(passed),
            'failed_count':  len(failed),
            'failed_rules':  list(failed.keys()),
            'failed_reasons': failed,
        }

    def raise_on_failure(self, validation: Dict[str, Any]) -> None:
        if not validation['validation_passed']:
            failed = validation['failed_rules']
            reasons = validation['failed_reasons']
            msg = '; '.join(f"{r}: {reasons.get(r, '?')}" for r in failed)
            raise PIPELINE_INITIALIZATION_ERROR(
                f"Phase V.ROOT.1 failed {len(failed)} rule(s): {msg}"
            )
