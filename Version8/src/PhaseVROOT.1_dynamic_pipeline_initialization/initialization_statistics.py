"""
Phase V.ROOT.1 -- initialization_statistics.py
Aggregate all pipeline initialization statistics.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

from typing import Any, Dict


class InitializationStatistics:
    """Collect and aggregate V.ROOT.1 initialization statistics."""

    def collect(
        self,
        project_manifest:  Dict[str, Any],
        drawing_manifest:  Dict[str, Any],
        discovery_result:  Dict[str, Any],
        beam_registry:     Dict[str, Any],
        eng_obj_result:    Dict[str, Any],
        pipeline_context:  Dict[str, Any],
        dep_check:         Dict[str, Any],
        validation:        Dict[str, Any],
        total_elapsed_s:   float,
    ) -> Dict[str, Any]:

        dxf_elapsed   = discovery_result.get('elapsed_s', 0.0)
        beam_count     = beam_registry.get('beam_count', 0)
        objects_gen    = eng_obj_result.get('objects_generated', {})

        return {
            'project': {
                'project_id':    project_manifest.get('project_id'),
                'project_name':  project_manifest.get('project_name'),
                'building':      project_manifest.get('building'),
                'floor':         project_manifest.get('floor'),
            },
            'drawings': {
                'total_discovered': drawing_manifest.get('total_drawings', 0),
                'type_counts':      drawing_manifest.get('type_counts', {}),
                'has_reinforcement': drawing_manifest.get('has_reinforcement_drawing', False),
                'has_framing':      drawing_manifest.get('has_framing_drawing', False),
            },
            'beam_discovery': {
                'beam_count':           beam_count,
                'beam_ids':             beam_registry.get('beam_ids', []),
                'label_entities_found': discovery_result.get('label_entities', 0),
                'total_text_entities':  discovery_result.get('total_text_entities', 0),
                'dxf_parse_time_s':     dxf_elapsed,
                'source':               'DYNAMIC_DXF_DISCOVERY',
                'hardcoded_fallback':   False,
            },
            'engineering_objects': {
                'beam_schedule_entries':    objects_gen.get('beam_schedule', 0),
                'reinforcement_bars':       objects_gen.get('reinforcement_objects', 0),
                'engineering_objects':      objects_gen.get('engineering_objects', 0),
                'adapters_written':         len(eng_obj_result.get('adapter_paths', {})),
                'backups_created':          len(eng_obj_result.get('backup_created', {})),
            },
            'dependency_analysis': {
                'passed':        dep_check.get('dependency_check_passed', False),
                'issues_count':  len(dep_check.get('issues', [])),
                'v5_refs':       dep_check.get('summary', {}).get('v5_refs_found', 0),
                'hardcoded_ids': dep_check.get('summary', {}).get('hardcoded_ids_found', 0),
                'set1_refs':     dep_check.get('summary', {}).get('set1_refs_found', 0),
            },
            'validation': {
                'passed':        validation.get('validation_passed', False),
                'rules_passed':  validation.get('passed_count', 0),
                'rules_failed':  validation.get('failed_count', 0),
                'failed_rules':  validation.get('failed_rules', []),
            },
            'timing': {
                'dxf_parse_s':       dxf_elapsed,
                'total_elapsed_s':   round(total_elapsed_s, 2),
            },
        }
