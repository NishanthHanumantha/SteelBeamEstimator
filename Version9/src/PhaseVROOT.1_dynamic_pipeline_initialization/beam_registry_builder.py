"""
Phase V.ROOT.1 -- beam_registry_builder.py
Build the canonical beam registry from dynamically discovered beams.
No hardcoded IDs. Supports any naming convention.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List


class BeamRegistryBuilder:
    """
    Convert raw beam discovery results into a canonical beam registry.
    Every field is derived from the current drawing -- no inherited data.
    """

    def build(
        self,
        discovery_result: Dict[str, Any],
        project_id: str,
        drawing_path: str,
    ) -> Dict[str, Any]:

        raw_beams: List[Dict[str, Any]] = discovery_result.get('beams', [])
        registry_entries: Dict[str, Any] = {}

        for idx, beam in enumerate(raw_beams):
            beam_id = beam['beam_id']
            entry   = {
                # Identity
                'beam_uuid':      beam.get('uuid') or str(uuid.uuid4()),
                'beam_id':        beam_id,
                'beam_mark':      beam.get('beam_mark', beam_id),
                'beam_index':     idx,

                # Drawing provenance -- from CURRENT project only
                'project_id':     project_id,
                'drawing_path':   drawing_path,
                'drawing_stem':   discovery_result.get('dxf_stem', ''),

                # Geometry (discovered or estimated)
                'section': {
                    'width_mm':   beam.get('section', {}).get('width_mm', 200.0),
                    'depth_mm':   beam.get('section', {}).get('depth_mm', 600.0),
                    'inferred':   beam.get('section', {}).get('inferred', True),
                },
                'clear_span_mm': beam.get('clear_span_mm'),

                # Spatial position in drawing
                'centroid_x':    beam.get('centroid_x'),
                'centroid_y':    beam.get('centroid_y'),
                'bbox':          beam.get('bbox', {}),

                # Discovery metadata
                'occurrence_count':  beam.get('occurrence_count', 1),
                'annotation_count':  beam.get('annotation_count', 0),
                'status':            'REGISTERED',
                'connected_objects': [],
                'traceability': {
                    'source':        'DXF_TEXT_EXTRACTION',
                    'phase':         'V.ROOT.1',
                    'model_version': '7.1.0',
                    'discovered_at': datetime.now().isoformat(),
                },
            }
            registry_entries[beam_id] = entry

        return {
            'project_id':   project_id,
            'drawing_path': drawing_path,
            'beam_count':   len(registry_entries),
            'beam_ids':     sorted(registry_entries.keys()),
            'generated_at': datetime.now().isoformat(),
            'source':       'DYNAMIC_DXF_DISCOVERY',
            'hardcoded':    False,
            'beams':        registry_entries,
        }
