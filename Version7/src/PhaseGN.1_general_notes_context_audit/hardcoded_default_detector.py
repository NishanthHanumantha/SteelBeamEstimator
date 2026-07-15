"""
Hardcoded Default Detector — Part 6 of Phase GN.1 audit.

Scans the entire Version7 Python source for engineering constants that should
ideally originate from the General Notes DXF:
  7850, Fe500, Fe415, M25, M30, 40mm cover, 10d hook, development length factor.

Classifies each occurrence as:
  Dynamic | General_Notes | Hardcoded | Config | Fallback | Default

READ-ONLY: does not modify any file.
"""
from __future__ import annotations
import pathlib
import re
from typing import List

from .gn_models import HardcodedDefault, SourceClass, GapSeverity

# ---------------------------------------------------------------------------
# Engineering constant patterns to search for
# ---------------------------------------------------------------------------
_SEARCH_RULES = [
    {
        "pattern": re.compile(r"_DEVELOPMENT_LENGTH_FACTOR\s*=\s*(\d+)", re.I),
        "symbol": "_DEVELOPMENT_LENGTH_FACTOR",
        "meaning": "Development length multiplier (Ld = N*d)",
        "classification": SourceClass.HARDCODED,
        "gn_equivalent": "Development Length Table (LD FOR FY-415) in GN DXF",
        "severity": GapSeverity.HIGH,
    },
    {
        "pattern": re.compile(r"_COVER_MM\s*=\s*([\d.]+)", re.I),
        "symbol": "_COVER_MM",
        "meaning": "Nominal concrete clear cover in mm",
        "classification": SourceClass.HARDCODED,
        "gn_equivalent": "Not explicitly specified in GN DXF; IS 456:2000 Table 16 = 40mm for beams",
        "severity": GapSeverity.HIGH,
    },
    {
        "pattern": re.compile(r"_HOOK_MULTIPLE\s*=\s*(\d+)", re.I),
        "symbol": "_HOOK_MULTIPLE",
        "meaning": "Hook allowance multiplier per end (hook = N*d)",
        "classification": SourceClass.HARDCODED,
        "gn_equivalent": "GN DXF: Standard 90 Bend = 4xdb; pipeline uses 10d",
        "severity": GapSeverity.MEDIUM,
    },
    {
        "pattern": re.compile(r"_DENSITY_KG_M3\s*=\s*([\d.]+)", re.I),
        "symbol": "_DENSITY_KG_M3",
        "meaning": "Steel density in kg/m3",
        "classification": SourceClass.DEFAULT,
        "gn_equivalent": "IS standard constant (7850 kg/m3) — acceptable hardcode",
        "severity": GapSeverity.LOW,
    },
    {
        "pattern": re.compile(r"[\"']Steel Grade[\"']\s*:\s*[\"']Fe415[^\"']*[\"']", re.I),
        "symbol": "Steel Grade = Fe415",
        "meaning": "Steel grade label in Excel output",
        "classification": SourceClass.HARDCODED,
        "gn_equivalent": "GN DXF development length table implies Fe415",
        "severity": GapSeverity.MEDIUM,
    },
    {
        "pattern": re.compile(r"(?:concrete_grade|concrete\s+grade)\s+or\s+[\"']M30[\"']", re.I),
        "symbol": "default concrete grade M30",
        "meaning": "Fallback concrete grade when GN not parsed",
        "classification": SourceClass.FALLBACK,
        "gn_equivalent": "GN DXF: M25 concrete grade for beams in superstructure",
        "severity": GapSeverity.HIGH,
    },
    {
        "pattern": re.compile(r"7850(?:\.0)?(?!\s*#.*IS)", re.I),
        "symbol": "7850",
        "meaning": "Steel density 7850 kg/m3",
        "classification": SourceClass.DEFAULT,
        "gn_equivalent": "IS standard physical constant — acceptable",
        "severity": GapSeverity.LOW,
    },
    {
        "pattern": re.compile(r"Development\s+length\s+=\s+40d", re.I),
        "symbol": "Development length = 40d",
        "meaning": "Development length comment/label",
        "classification": SourceClass.HARDCODED,
        "gn_equivalent": "GN DXF development length table for Fe415",
        "severity": GapSeverity.MEDIUM,
    },
    {
        "pattern": re.compile(r"Clear\s+cover\s+=\s+40\s*mm", re.I),
        "symbol": "Clear cover = 40 mm",
        "meaning": "Cover value in Excel/report notes",
        "classification": SourceClass.HARDCODED,
        "gn_equivalent": "IS 456:2000 Table 16 — should be confirmed from GN",
        "severity": GapSeverity.MEDIUM,
    },
    {
        "pattern": re.compile(r"Fe415.*High Yield|High Yield.*Fe415", re.I),
        "symbol": "Fe415 (High Yield)",
        "meaning": "Steel grade string in Excel sheet",
        "classification": SourceClass.HARDCODED,
        "gn_equivalent": "Should be populated from GN DXF steel grade extraction",
        "severity": GapSeverity.MEDIUM,
    },
    {
        "pattern": re.compile(r"\"M30\"\s*#\s*default", re.I),
        "symbol": '"M30" default',
        "meaning": "Default concrete grade M30",
        "classification": SourceClass.FALLBACK,
        "gn_equivalent": "GN DXF concrete grade table",
        "severity": GapSeverity.HIGH,
    },
]


class HardcodedDefaultDetector:
    """
    Scans Version7/src python files and identifies engineering hardcoded
    constants that should be sourced dynamically from General Notes DXF.
    """

    def __init__(self, v7_root: pathlib.Path):
        self._src = v7_root / "src"

    def detect(self) -> List[HardcodedDefault]:
        findings: List[HardcodedDefault] = []
        for py_file in sorted(self._src.rglob("*.py")):
            try:
                lines = py_file.read_text("utf-8", errors="replace").splitlines()
            except Exception:
                continue
            for line_no, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for rule in _SEARCH_RULES:
                    m = rule["pattern"].search(line)
                    if m:
                        literal = m.group(0)[:60]
                        rel_path = py_file.relative_to(self._src.parent)
                        findings.append(HardcodedDefault(
                            file_path=str(rel_path),
                            line_number=line_no,
                            symbol=rule["symbol"],
                            literal_value=literal,
                            engineering_meaning=rule["meaning"],
                            classification=rule["classification"],
                            gn_equivalent=rule.get("gn_equivalent"),
                            severity=rule["severity"],
                            notes=f"Match: {literal}",
                        ))
        return findings
