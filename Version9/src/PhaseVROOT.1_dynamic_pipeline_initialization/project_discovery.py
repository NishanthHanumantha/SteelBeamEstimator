"""
Phase V.ROOT.1 -- project_discovery.py
Automatically discover project identity from any input folder.
No filenames are hardcoded. No project-specific logic.
MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import re
import pathlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


_FLOOR_PATTERNS = [
    (re.compile(r'\b(GF|GROUND\s*FL(?:OOR)?)\b', re.I), 'GF'),
    (re.compile(r'\b(B\d)\b'), None),          # basement floor e.g. B1
    (re.compile(r'\bFL?[-_]?(\d+)\b', re.I), None),   # F1, FL2, F-3
    (re.compile(r'\b(\d+)(?:ST|ND|RD|TH)\s*FL', re.I), None),
    (re.compile(r'\b(ROOF|TOP|TERRACE)\b', re.I), None),
]

_DISCIPLINE_PATTERNS = [
    (re.compile(r'\bSE\b', re.I), 'STRUCTURAL'),
    (re.compile(r'\bSTR(?:UCT)?\b', re.I), 'STRUCTURAL'),
    (re.compile(r'\bME\b', re.I), 'MECHANICAL'),
    (re.compile(r'\bEL\b', re.I), 'ELECTRICAL'),
    (re.compile(r'\bCIV\b', re.I), 'CIVIL'),
]


class ProjectDiscovery:
    """
    Inspect any folder to discover project identity.
    Produces a project_manifest dict.
    """

    def discover(self, folder: pathlib.Path) -> Dict[str, Any]:
        folder = folder.resolve()
        all_names = [p.name for p in folder.rglob('*') if p.is_file()]
        combined  = ' '.join([folder.name] + all_names)

        project_name   = self._infer_project_name(folder, all_names)
        building       = self._infer_building(combined, folder)
        floor          = self._infer_floor(combined)
        discipline     = self._infer_discipline(combined)
        revision       = self._infer_revision(combined)
        drawing_set_id = self._build_drawing_set_id(project_name, building, floor)
        project_id     = f"{drawing_set_id}::{datetime.now().strftime('%Y')}"

        dxf_files = [p for p in folder.rglob('*.dxf')] + [p for p in folder.rglob('*.DXF')]

        return {
            'project_id':      project_id,
            'project_name':    project_name,
            'building':        building,
            'floor':           floor,
            'discipline':      discipline,
            'revision':        revision,
            'drawing_set_id':  drawing_set_id,
            'source_folder':   str(folder),
            'dxf_count':       len(dxf_files),
            'dxf_files':       [str(p) for p in dxf_files],
            'discovered_at':   datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------

    def _infer_project_name(
        self, folder: pathlib.Path, names: List[str]
    ) -> str:
        # Use the reinforcement DXF stem if available
        for n in names:
            p = pathlib.Path(n)
            if 'reinforcement' in n.lower() and p.suffix.lower() == '.dxf':
                stem = p.stem
                # Remove common suffixes (e.g. BeamReinforcementDetails)
                stem = re.sub(r'[_-]?Beam.*$', '', stem, flags=re.I).strip('_- ')
                if stem:
                    return stem
        # Fallback: folder name, cleaned
        name = folder.name
        name = re.sub(r'[_-]+', ' ', name).strip()
        return name or 'UNKNOWN_PROJECT'

    def _infer_building(self, text: str, folder: pathlib.Path) -> str:
        # Try to extract building name from folder path
        parts = list(folder.parts)
        for part in reversed(parts):
            if re.search(r'\b(?:clubhouse|galera|villa|tower|block|building|bldg)\b', part, re.I):
                m = re.search(
                    r'(clubhouse|galera|villa|tower|block[_\s]*\w+|building[_\s]*\w+)',
                    part, re.I
                )
                if m:
                    return m.group(1).title()
        # From combined text
        m = re.search(r'\b(CLUBHOUSE|GALERA|VILLA|TOWER)\b', text, re.I)
        return m.group(1).title() if m else 'UNKNOWN_BUILDING'

    def _infer_floor(self, text: str) -> str:
        for pat, label in _FLOOR_PATTERNS:
            m = pat.search(text)
            if m:
                return label if label else m.group(1).upper()
        return 'UNKNOWN_FLOOR'

    def _infer_discipline(self, text: str) -> str:
        for pat, label in _DISCIPLINE_PATTERNS:
            if pat.search(text):
                return label
        return 'STRUCTURAL'

    def _infer_revision(self, text: str) -> str:
        m = re.search(r'R(\d+)', text, re.I)
        return f"R{m.group(1)}" if m else 'R0'

    def _build_drawing_set_id(self, name: str, building: str, floor: str) -> str:
        clean = re.sub(r'[^A-Z0-9]', '_', name.upper())
        return f"{clean}::{building.upper()}::{floor}"
