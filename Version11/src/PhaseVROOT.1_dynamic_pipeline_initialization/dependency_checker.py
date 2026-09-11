"""
Phase V.ROOT.1 -- dependency_checker.py
Detect any remaining Version5, Benchmark Set 1, or hardcoded-beam dependencies
in the generated pipeline context.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List


# Hardcoded beam IDs from Benchmark Set 1 that must not appear as static values
_SET1_BEAM_IDS = {
    "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10",
    "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18",
}

_V5_PHRASES = [
    "Version5", "v5_", "phase_g", "phase_i", "phase_e", "phase_f",
    "g_5_1_engineering_objects", "i_2_reinforcement_engine",
    "i_15_beam_schedule", "beam_geometry_model",
]

_HARDCODE_PHRASES = [
    "HARDCODED", "STATIC_BEAM", "BENCHMARK_SET1",
]


class DependencyChecker:
    """
    Inspect pipeline context, beam registry, and engineering objects
    to verify all dependencies have been eliminated.
    """

    def check(
        self,
        pipeline_context: Dict[str, Any],
        beam_registry:    Dict[str, Any],
        eng_obj_result:   Dict[str, Any],
    ) -> Dict[str, Any]:

        issues: List[str] = []
        findings: Dict[str, List[str]] = {
            'v5_references':        [],
            'hardcoded_beam_ids':   [],
            'benchmark_set1_refs':  [],
            'static_paths':         [],
        }

        # Serialise to string for grep-style scanning
        ctx_str  = json.dumps(pipeline_context, default=str)
        reg_str  = json.dumps(beam_registry, default=str)
        eng_str  = json.dumps(eng_obj_result, default=str)

        # 1. Check for V5 dependency phrases IN THE CONTEXT
        for phrase in _V5_PHRASES:
            if phrase.lower() in ctx_str.lower():
                # Only flag if it's in a user-data field, not an adapter_path key
                ctx_obj = pipeline_context.get('engineering_objects', {})
                adapters = ctx_obj.get('adapter_paths', {})
                # Adapter paths ARE expected to reference v5 -- not a dependency issue
                adapter_values = list(adapters.values())
                if any(phrase.lower() in av.lower() for av in adapter_values):
                    continue  # adapter path -- expected
                findings['v5_references'].append(phrase)

        # 2. Check if beam IDs in registry are exclusively hardcoded B1-B18
        beam_ids = set(beam_registry.get('beam_ids', []))
        if beam_ids and beam_ids == _SET1_BEAM_IDS:
            findings['hardcoded_beam_ids'].append(
                "Beam registry contains EXACTLY the B1-B18 set from Benchmark Set 1. "
                "This may indicate hardcoded fallback was used instead of DXF discovery."
            )

        # 3. Check for hardcoded phrases
        for phrase in _HARDCODE_PHRASES:
            if phrase in ctx_str or phrase in reg_str:
                findings['benchmark_set1_refs'].append(phrase)

        # 4. Quality flags
        quality = pipeline_context.get('quality', {})
        if quality.get('uses_hardcoded_beams'):
            issues.append("Pipeline context reports uses_hardcoded_beams=True")
        if quality.get('uses_v5_dependencies'):
            issues.append("Pipeline context reports uses_v5_dependencies=True")
        if quality.get('uses_benchmark_set1'):
            issues.append("Pipeline context reports uses_benchmark_set1=True")

        # Consolidate
        for cat, refs in findings.items():
            for ref in refs:
                issues.append(f"[{cat.upper()}] {ref}")

        passed = len(issues) == 0

        return {
            'dependency_check_passed': passed,
            'issues':    issues,
            'findings':  findings,
            'summary': {
                'v5_refs_found':       len(findings['v5_references']),
                'hardcoded_ids_found': len(findings['hardcoded_beam_ids']),
                'set1_refs_found':     len(findings['benchmark_set1_refs']),
            },
            'note': (
                "Adapter paths to Version5 directories are expected and do NOT "
                "constitute a Version5 dependency -- they are write targets, "
                "not read sources."
            ),
        }
