"""Fix remaining DEFAULT_* references in run_phase scripts."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPLACEMENTS = {
    "DEFAULT_ANNOTATIONS": "paths.beam_annotations_raw",
    "DEFAULT_SKETCHES": "paths.beam_sketches_debug",
    "DEFAULT_OWNERSHIP": "paths.sketch_ownership",
    "DEFAULT_OCCURRENCES": "paths.header_occurrences",
    "DEFAULT_BEAM_CELLS": "paths.beam_cells",
    "DEFAULT_REASSIGNED": "paths.beam_annotations_reassigned",
    "DEFAULT_REGION_VALIDATION": "paths.annotation_region_validation",
    "DEFAULT_LEAKAGE": "paths.boundary_leakage_report",
    "DEFAULT_D13_SUMMARY": "paths.annotation_region_validation_summary",
    "DEFAULT_D131_SUMMARY": "paths.boundary_leakage_summary",
}

for path in ROOT.glob("run_phase_*.py"):
    text = path.read_text(encoding="utf-8")
    original = text
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"Fixed {path.name}")

# Fix d16b missing DEFAULT_DXF_DIR
d16b = ROOT / "run_phase_d16b_entity_survey.py"
text = d16b.read_text(encoding="utf-8")
if "DEFAULT_DXF_DIR" in text and "DEFAULT_DXF_DIR = " not in text:
    text = text.replace(
        "from src.dxf.dxf_entity_type_survey import DxfEntityTypeSurvey\n",
        "from src.dxf.dxf_entity_type_survey import DxfEntityTypeSurvey\n\nDEFAULT_DXF_DIR = Path(\"data/reinforcement\")\n",
    )
    d16b.write_text(text, encoding="utf-8")
    print("Fixed d16b DEFAULT_DXF_DIR")

d17a = ROOT / "run_phase_d17a_dimension_source_audit.py"
text = d17a.read_text(encoding="utf-8")
if "DEFAULT_DXF_DIR" in text and "DEFAULT_DXF_DIR = " not in text:
    text = text.replace(
        "from src.annotations.dimension_source_validator import DimensionSourceValidator\n",
        "from src.annotations.dimension_source_validator import DimensionSourceValidator\n\nDEFAULT_DXF_DIR = Path(\"data/reinforcement\")\n",
    )
    d17a.write_text(text, encoding="utf-8")
    print("Fixed d17a DEFAULT_DXF_DIR")

d17 = ROOT / "run_phase_d17_dimension_extraction.py"
text = d17.read_text(encoding="utf-8")
if "DEFAULT_DXF_DIR" in text and "DEFAULT_DXF_DIR = " not in text:
    text = text.replace(
        "from src.annotations.dimension_annotation_validator import DimensionAnnotationValidator\n",
        "from src.annotations.dimension_annotation_validator import DimensionAnnotationValidator\n\nDEFAULT_DXF_DIR = Path(\"data/reinforcement\")\n",
    )
    d17.write_text(text, encoding="utf-8")
    print("Fixed d17 DEFAULT_DXF_DIR")

d16a = ROOT / "run_phase_d16a_annotation_coverage.py"
text = d16a.read_text(encoding="utf-8")
if "DEFAULT_DXF = " not in text:
    text = text.replace(
        "from src.annotations.annotation_coverage_debug_exporter import (\n",
        "DEFAULT_DXF = Path(\"data/reinforcement/Beam_ReinforcementDetails.dxf\")\n\nfrom src.annotations.annotation_coverage_debug_exporter import (\n",
    )
    d16a.write_text(text, encoding="utf-8")
    print("Fixed d16a DEFAULT_DXF")

print("Done")
