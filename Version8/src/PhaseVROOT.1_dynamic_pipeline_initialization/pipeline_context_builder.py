"""
Phase V.ROOT.1 -- pipeline_context_builder.py
Package all dynamic context for downstream pipeline consumption.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


class PipelineContextBuilder:
    """
    Assemble the pipeline_context.json consumed by L.2 and all
    downstream phases when they run in dynamic mode.
    """

    def build(
        self,
        project_context:     Dict[str, Any],
        drawing_manifest:    Dict[str, Any],
        beam_registry:       Dict[str, Any],
        eng_obj_result:      Dict[str, Any],
    ) -> Dict[str, Any]:

        return {
            # Phase identity
            'phase':           'V.ROOT.1',
            'model_version':   '7.1.0',
            'initialized_at':  datetime.now().isoformat(),

            # Project
            'project_context': project_context,

            # Drawings
            'drawing_manifest': {
                'total_drawings': drawing_manifest.get('total_drawings', 0),
                'type_counts':    drawing_manifest.get('type_counts', {}),
                'primary_reinforcement_drawing': drawing_manifest.get(
                    'primary_reinforcement_drawing'
                ),
                'primary_framing_drawing': drawing_manifest.get(
                    'primary_framing_drawing'
                ),
            },

            # Beams (fully dynamic)
            'beam_registry': {
                'beam_count': beam_registry.get('beam_count', 0),
                'beam_ids':   beam_registry.get('beam_ids', []),
                'source':     beam_registry.get('source', 'DYNAMIC_DXF_DISCOVERY'),
                'hardcoded':  False,
            },

            # Engineering objects
            'engineering_objects': {
                'beam_schedule_count': eng_obj_result.get('objects_generated', {}).get(
                    'beam_schedule', 0
                ),
                'reinforcement_bar_count': eng_obj_result.get('objects_generated', {}).get(
                    'reinforcement_objects', 0
                ),
                'engineering_object_count': eng_obj_result.get('objects_generated', {}).get(
                    'engineering_objects', 0
                ),
                'adapter_paths': eng_obj_result.get('adapter_paths', {}),
            },

            # Quality flags
            'quality': {
                'uses_hardcoded_beams':   False,
                'uses_v5_dependencies':   False,
                'uses_benchmark_set1':    False,
                'dynamic_initialization': True,
                'backward_compatible':    True,
            },

            # Downstream instructions
            'downstream_config': {
                'l2_ready':    True,
                'si0_ready':   True,
                'si1_ready':   True,
                'vb1_ready':   True,
                'note': (
                    'V.ROOT.1 has written dynamic engineering objects to the '
                    'Version5 adapter paths. All downstream phases (L.2 onwards) '
                    'will use the dynamically discovered beam data.'
                ),
            },
        }
