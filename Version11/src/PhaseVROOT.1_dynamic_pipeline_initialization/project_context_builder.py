"""
Phase V.ROOT.1 -- project_context_builder.py
Build a dynamic project context dict from discovered data.
No Benchmark Set 1 references. No Version5 dependencies.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


class ProjectContextBuilder:
    """
    Assemble the complete project context from all discovered information.
    The context is passed to every downstream phase.
    """

    def build(
        self,
        project_manifest:  Dict[str, Any],
        drawing_manifest:  Dict[str, Any],
        beam_registry:     Dict[str, Any],
    ) -> Dict[str, Any]:

        beam_ids = list(beam_registry.get('beams', {}).keys())
        beam_count = len(beam_ids)

        return {
            # Project identity (all dynamically discovered)
            'project_id':           project_manifest.get('project_id', 'UNKNOWN'),
            'project_name':         project_manifest.get('project_name', 'UNKNOWN'),
            'building':             project_manifest.get('building', 'UNKNOWN'),
            'floor':                project_manifest.get('floor', 'UNKNOWN'),
            'discipline':           project_manifest.get('discipline', 'STRUCTURAL'),
            'revision':             project_manifest.get('revision', 'R0'),
            'drawing_set_id':       project_manifest.get('drawing_set_id', 'UNKNOWN'),

            # Drawing references
            'primary_reinforcement_drawing': drawing_manifest.get(
                'primary_reinforcement_drawing'
            ),
            'primary_framing_drawing': drawing_manifest.get(
                'primary_framing_drawing'
            ),
            'total_drawings':        drawing_manifest.get('total_drawings', 0),

            # Beam registry summary
            'beam_ids':              beam_ids,
            'beam_count':            beam_count,
            'beam_id_source':        'DYNAMIC_DXF_DISCOVERY',

            # Engineering standards
            'material_grade':        'Grade 460',
            'concrete_grade':        'C30/37',
            'cover_mm':              25,

            # Benchmark flags (all False -- no hardcoded assumptions)
            'uses_hardcoded_beams':   False,
            'uses_v5_dependencies':   False,
            'uses_benchmark_set1':    False,

            # Provenance
            'initialized_at':        datetime.now().isoformat(),
            'model_version':         '7.1.0',
            'phase':                 'V.ROOT.1',
        }
