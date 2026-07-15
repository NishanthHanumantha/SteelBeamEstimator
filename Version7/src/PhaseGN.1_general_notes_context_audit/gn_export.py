"""
GN Export — writes all 10 Phase GN.1 output artefacts to JSON files.
"""
from __future__ import annotations
import dataclasses
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List


def _to_json(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, (list, tuple)):
        return [_to_json(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_json(v) for k, v in obj.items()}
    return obj


def _save(output_dir: pathlib.Path, filename: str, data: Any) -> pathlib.Path:
    path = output_dir / filename
    serializable = _to_json(data)
    path.write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


class GNExport:
    """Writes all Phase GN.1 output JSON artefacts."""

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        discovery: Any,
        extracted: List[Any],
        traceability: List[Any],
        framing: List[Any],
        rebar: List[Any],
        hardcoded: List[Any],
        consumption: List[Any],
        gaps: List[Any],
        generalization: Dict,
        validation: List[Any],
        full_report: Dict,
    ) -> Dict[str, str]:
        timestamp = datetime.utcnow().isoformat()
        paths: Dict[str, str] = {}

        # 1. general_notes_discovery.json
        p = _save(self._out, "general_notes_discovery.json", {
            "generated": timestamp,
            "discovery": _to_json(discovery),
        })
        paths["general_notes_discovery"] = str(p)

        # 2. engineering_context.json
        p = _save(self._out, "engineering_context.json", {
            "generated": timestamp,
            "extracted_parameters": [_to_json(e) for e in extracted],
            "parameter_count": len(extracted),
        })
        paths["engineering_context"] = str(p)

        # 3. engineering_parameter_traceability.json
        p = _save(self._out, "engineering_parameter_traceability.json", {
            "generated": timestamp,
            "traceability_nodes": [_to_json(n) for n in traceability],
            "total_nodes": len(traceability),
        })
        paths["engineering_parameter_traceability"] = str(p)

        # 4. framing_context_traceability.json
        p = _save(self._out, "framing_context_traceability.json", {
            "generated": timestamp,
            "framing_fields": [_to_json(f) for f in framing],
            "all_fields_used": all(f.used for f in framing),
        })
        paths["framing_context_traceability"] = str(p)

        # 5. reinforcement_context_traceability.json
        p = _save(self._out, "reinforcement_context_traceability.json", {
            "generated": timestamp,
            "rebar_fields": [_to_json(r) for r in rebar],
            "fields_with_consumers": sum(1 for r in rebar if r.consumer_modules),
        })
        paths["reinforcement_context_traceability"] = str(p)

        # 6. parameter_consumption_matrix.json
        p = _save(self._out, "parameter_consumption_matrix.json", {
            "generated": timestamp,
            "consumption_records": [_to_json(c) for c in consumption],
            "total": len(consumption),
            "all_consuming": sum(1 for c in consumption if c.all_match),
        })
        paths["parameter_consumption_matrix"] = str(p)

        # 7. hardcoded_defaults_report.json
        from .gn_models import GapSeverity, SourceClass
        p = _save(self._out, "hardcoded_defaults_report.json", {
            "generated": timestamp,
            "findings": [_to_json(h) for h in hardcoded],
            "total": len(hardcoded),
            "by_severity": {
                "CRITICAL": sum(1 for h in hardcoded if h.severity == GapSeverity.CRITICAL),
                "HIGH": sum(1 for h in hardcoded if h.severity == GapSeverity.HIGH),
                "MEDIUM": sum(1 for h in hardcoded if h.severity == GapSeverity.MEDIUM),
                "LOW": sum(1 for h in hardcoded if h.severity == GapSeverity.LOW),
            },
            "by_classification": {
                "Hardcoded": sum(1 for h in hardcoded if h.classification == SourceClass.HARDCODED),
                "Fallback": sum(1 for h in hardcoded if h.classification == SourceClass.FALLBACK),
                "Default": sum(1 for h in hardcoded if h.classification == SourceClass.DEFAULT),
            },
        })
        paths["hardcoded_defaults_report"] = str(p)

        # 8. engineering_gap_analysis.json
        from .gn_models import GapSeverity
        p = _save(self._out, "engineering_gap_analysis.json", {
            "generated": timestamp,
            "gaps": [_to_json(g) for g in gaps],
            "total_gaps": len(gaps),
            "by_severity": {
                "CRITICAL": sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL),
                "HIGH": sum(1 for g in gaps if g.severity == GapSeverity.HIGH),
                "MEDIUM": sum(1 for g in gaps if g.severity == GapSeverity.MEDIUM),
                "LOW": sum(1 for g in gaps if g.severity == GapSeverity.LOW),
            },
        })
        paths["engineering_gap_analysis"] = str(p)

        # 9. validation_report.json
        passed = sum(1 for v in validation if v.passed)
        p = _save(self._out, "validation_report.json", {
            "generated": timestamp,
            "rules": [_to_json(v) for v in validation],
            "passed": passed,
            "total": len(validation),
            "score": f"{passed}/{len(validation)}",
            "all_passed": passed == len(validation),
        })
        paths["validation_report"] = str(p)

        # 10. general_notes_context_audit_report.json (master report)
        p = _save(self._out, "general_notes_context_audit_report.json", full_report)
        paths["general_notes_context_audit_report"] = str(p)

        return paths
