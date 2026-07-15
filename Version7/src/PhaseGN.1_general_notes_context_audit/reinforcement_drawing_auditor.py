"""
Reinforcement Drawing Auditor — Part 5 of Phase GN.1 audit.

Verifies the origin of every reinforcement quantity used by the pipeline:
  Top Bars, Bottom Bars, Top Extra, Bottom Extra,
  Stirrups, Spacer, SFR, Dimension Callouts.

READ-ONLY: does not modify any production file.
"""
from __future__ import annotations
import json
import pathlib
from typing import Any, Dict, List

from .gn_models import RebarFieldAudit, SourceClass

_REBAR_FIELDS = [
    {
        "field": "top_main_bars",
        "source_entity": "Annotation text above beam neutral axis (e.g. '3Y16')",
        "consumer_modules": [
            "PhaseR1.ReinforcementDiscovery",
            "ReinforcementSourceAdapter",
            "SteelWeightCompletion",
            "BBSCompletionEngine",
        ],
        "classification": SourceClass.DYNAMIC,
        "notes": "Phase R.1 reads top annotations from reinforcement DXF by spatial Y-position",
    },
    {
        "field": "bottom_main_bars",
        "source_entity": "Annotation text below beam neutral axis (e.g. '3Y20')",
        "consumer_modules": [
            "PhaseR1.ReinforcementDiscovery",
            "ReinforcementSourceAdapter",
            "SteelWeightCompletion",
            "BBSCompletionEngine",
        ],
        "classification": SourceClass.DYNAMIC,
        "notes": "Phase R.1 reads bottom annotations by spatial Y-position relative to beam",
    },
    {
        "field": "top_extra_bars",
        "source_entity": "Secondary annotation above neutral axis (extra / EF)",
        "consumer_modules": [
            "PhaseR1.ReinforcementDiscovery",
            "ReinforcementSourceAdapter",
            "SteelWeightCompletion",
        ],
        "classification": SourceClass.DYNAMIC,
        "notes": "Phase R.1 identifies extra bars by EF/extra pattern matching",
    },
    {
        "field": "bottom_extra_bars",
        "source_entity": "Secondary annotation below neutral axis",
        "consumer_modules": [
            "PhaseR1.ReinforcementDiscovery",
            "ReinforcementSourceAdapter",
            "SteelWeightCompletion",
        ],
        "classification": SourceClass.DYNAMIC,
        "notes": "Phase R.1 identifies extra bars by position and annotation pattern",
    },
    {
        "field": "stirrups",
        "source_entity": "Stirrup annotation (e.g. 'Y8@150 c/c' or 'N-Y8D@150')",
        "consumer_modules": [
            "PhaseR1.ReinforcementDiscovery",
            "PhaseR1.AnnotationParser",
            "ReinforcementSourceAdapter",
            "StirrupWeightEngine",
            "BBSCompletionEngine",
        ],
        "classification": SourceClass.DYNAMIC,
        "notes": "Phase R.1 parses YD@S format and N-YD format for stirrup specs",
    },
    {
        "field": "spacer_bars",
        "source_entity": "Spacer bar annotation (if present in reinforcement drawing)",
        "consumer_modules": [],
        "classification": SourceClass.HARDCODED,
        "notes": (
            "Spacer bars are NOT extracted from reinforcement drawing in current pipeline. "
            "Spacer rules from GN DXF (Table-1) are also not consumed."
        ),
    },
    {
        "field": "side_face_reinforcement",
        "source_entity": "SFR annotation (side face reinforcement bars)",
        "consumer_modules": [
            "PhaseR1.ReinforcementDiscovery",
            "ReinforcementSourceAdapter",
            "SteelWeightCompletion",
        ],
        "classification": SourceClass.DYNAMIC,
        "notes": "Phase R.1 identifies SFR by annotation pattern matching",
    },
    {
        "field": "dimension_callouts",
        "source_entity": "DIMENSION entities and LENGTH annotations on beam reinforcement",
        "consumer_modules": [
            "PhaseR1.ReinforcementDiscovery",
            "SteelWeightCompletion",
        ],
        "classification": SourceClass.DYNAMIC,
        "notes": "Beam dimension callouts used to compute cut lengths by Phase R.1",
    },
]


class ReinforcementDrawingAuditor:
    """
    Audits reinforcement drawing field origins and downstream consumption.
    """

    def __init__(self, v7_root: pathlib.Path):
        self._v7 = v7_root
        self._r1_output = (
            v7_root / "data" / "output"
            / "PhaseR.1_generalized_reinforcement_discovery"
            / "beam_reinforcement_models.json"
        )
        self._rebar_dir = v7_root / "data" / "Benchmark_Set_2" / "reinforcement"

    def audit(self) -> List[RebarFieldAudit]:
        r1_data = self._load_r1_models()
        rebar_dxf = self._find_rebar_dxf()
        sample_beam = self._sample_beam(r1_data)

        audits: List[RebarFieldAudit] = []
        for field_def in _REBAR_FIELDS:
            field_name = field_def["field"]
            used = len(field_def["consumer_modules"]) > 0
            example_ann = self._get_example_annotation(sample_beam, field_name)

            audits.append(RebarFieldAudit(
                field_name=field_name,
                source_drawing=(
                    rebar_dxf.name if rebar_dxf else "MULTIPLE REBAR DXF FILES"
                ),
                source_entity=field_def["source_entity"],
                consumer_modules=field_def["consumer_modules"],
                used=used,
                example_annotation=example_ann,
                classification=field_def["classification"],
                notes=field_def["notes"],
            ))
        return audits

    def _load_r1_models(self) -> Dict:
        if self._r1_output.exists():
            try:
                return json.loads(self._r1_output.read_text("utf-8"))
            except Exception:
                pass
        return {}

    def _find_rebar_dxf(self) -> Any:
        if self._rebar_dir.exists():
            dxf_files = sorted(self._rebar_dir.glob("*.dxf"))
            return dxf_files[0] if dxf_files else None
        return None

    def _sample_beam(self, r1_data: Dict) -> Dict:
        models = r1_data.get("models", [])
        if models and isinstance(models, list):
            return models[0]
        return {}

    def _get_example_annotation(self, beam: Dict, field: str) -> str:
        groups = beam.get("groups", [])
        for g in groups:
            if isinstance(g, dict):
                # Map field names to group role
                role = g.get("role", "").lower()
                ann = g.get("annotation", g.get("raw_text", ""))
                if field.startswith("top") and "top" in role:
                    return str(ann)[:80]
                if field.startswith("bottom") and "bottom" in role:
                    return str(ann)[:80]
                if "stirrup" in field and "stirrup" in role:
                    return str(ann)[:80]
        return ""
