"""
Append RULE-012 to the Engineering Rule Library artefacts.
MODEL_VERSION: 8.8.2
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from beam_coverage_model import MODEL_VERSION, RULE_ID

RULE012_DEFINITION: Dict[str, Any] = {
    "rule_id": RULE_ID,
    "rule_name": "Mandatory Stirrup Coverage Validation",
    "rule_family": "Stirrup Interpretation",
    "rule_category": "Engineering Validation",
    "originating_issue": "RULE-012-INVARIANT",
    "originating_phase": "Annotation",
    "engineering_domain": "Reinforcement Discovery",
    "engineering_intent": "Every beam shall contain at least one stirrup representation.",
    "rule_description": (
        "Mandatory validation that every beam in the Beam Registry possesses a stirrup "
        "representation through Engineering Intent, Reinforcement Detail, Piece Generation, "
        "and EngineeringBars. Detection only — no automatic correction."
    ),
    "engineering_rationale": (
        "Stirrups hold top and bottom reinforcement, provide shear resistance, and maintain "
        "cage integrity. Missing stirrup annotations must not propagate undetected."
    ),
    "trigger_conditions": [
        "beam present in Beam Registry",
        "pipeline artefacts available for Intent / Detail / Piece / EngineeringBars",
    ],
    "required_inputs": [
        "beam_registry",
        "engineering_intents",
        "reinforcement_details",
        "reinforcement_pieces",
        "engineering_bar_models",
        "reinforcement_annotations",
    ],
    "decision_logic": [
        "FOR each beam in Beam Registry",
        "IF STIRRUP Intent AND STIRRUP Detail AND STIRRUP Piece AND STIRRUP EngineeringBar THEN PASS",
        "ELSE FAIL and record first missing pipeline stage",
        "DO NOT invent or auto-correct stirrups",
    ],
    "expected_outputs": [
        "stirrup_coverage_report",
        "beam_stirrup_validation",
        "missing_stirrup_diagnostics",
        "coverage_dashboard",
    ],
    "validation_criteria": [
        "every registry beam checked",
        "coverage_pct = detected_stirrup_families / beam_count",
        "missing beams reported with pipeline stage evidence",
        "no production modification",
        "no automatic correction",
    ],
    "priority": 1,
    "priority_label": "HIGH",
    "confidence": 1.0,
    "expected_accuracy_gain": 0.0,
    "estimated_steel_gain_kg": 0.0,
    "affected_roles": ["STIRRUP"],
    "affected_diameters": [],
    "affected_beams": [],
    "dependencies": ["RULE-010"],
    "conflicting_rules": [],
    "implementation_phase": "Validation",
    "status": "Missing",
    "source_phase": "R.1.6.2",
    "supporting_evidence": [
        "engineering_invariant: every RC beam requires stirrups",
        "R.1.6.1 computes only received stirrup intents",
    ],
    "validation_flags": [
        "MANDATORY_VALIDATION_RULE",
        "BEFORE_STEEL_CALCULATION",
        "BEFORE_BENCHMARKING",
        "BEFORE_CORRECTION_ENGINE",
        "DETECTION_ONLY",
    ],
    "originating_issues": ["RULE-012-INVARIANT"],
    "finding_ids": [],
    "gap_type": "Weak Validation",
    "pattern_id": "MANDATORY_STIRRUP_COVERAGE",
    "estimated_effort": "M",
    "engineering_risk": "High",
    "mandatory_validation_rule": True,
    "model_version": MODEL_VERSION,
}


class Rule012LibraryUpdater:
    """Append RULE-012 to R.1.6 library JSON artefacts (in-place update)."""

    def __init__(self, library_dir: Path):
        self.library_dir = Path(library_dir)

    def update(self, missing_beam_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        rule = dict(RULE012_DEFINITION)
        if missing_beam_ids is not None:
            rule["affected_beams"] = list(missing_beam_ids)

        library = self._read("engineering_rule_library.json") or {}
        rules_full = self._read("engineering_rules.json") or {}
        roadmap = self._read("implementation_roadmap.json") or {}
        traceability = self._read("engineering_rule_traceability.json") or {}

        self._upsert_library_index(library, rule)
        self._upsert_full_rules(rules_full, rule)
        self._upsert_roadmap(roadmap, rule)
        self._upsert_traceability(traceability, rule)
        self._upsert_priority_list(rule)

        self._write("engineering_rule_library.json", library)
        self._write("engineering_rules.json", rules_full)
        self._write("implementation_roadmap.json", roadmap)
        self._write("engineering_rule_traceability.json", traceability)

        return {
            "rule": rule,
            "library_path": str(self.library_dir / "engineering_rule_library.json"),
            "rule_count": library.get("rule_count"),
            "updated_files": [
                "engineering_rule_library.json",
                "engineering_rules.json",
                "implementation_roadmap.json",
                "engineering_rule_traceability.json",
                "rule_priority_list.json",
            ],
        }

    def _upsert_library_index(self, library: Dict[str, Any], rule: Dict[str, Any]) -> None:
        rows: List[Dict[str, Any]] = list(library.get("rules") or [])
        rows = [r for r in rows if r.get("rule_id") != RULE_ID]
        # Bump existing priorities so RULE-012 is highest (priority 1).
        for r in rows:
            try:
                p = int(r.get("priority") or 0)
            except (TypeError, ValueError):
                p = 0
            if p >= 1:
                r["priority"] = p + 1
        rows.insert(0, {
            "rule_id": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "rule_family": rule["rule_family"],
            "priority": 1,
            "status": rule["status"],
            "implementation_phase": rule["implementation_phase"],
            "expected_accuracy_gain": rule["expected_accuracy_gain"],
            "originating_issues": rule["originating_issues"],
            "mandatory_validation_rule": True,
            "priority_label": "HIGH",
        })
        rows.sort(key=lambda r: (int(r.get("priority") or 999), str(r.get("rule_id") or "")))
        families = sorted({str(r.get("rule_family")) for r in rows if r.get("rule_family")})
        library["model_version"] = MODEL_VERSION
        library["title"] = library.get("title") or "Engineering Rule Library"
        library["single_source_of_truth"] = True
        library["rule_count"] = len(rows)
        library["families"] = families
        library["rules"] = rows
        library["mandatory_validation_rules"] = [RULE_ID]

    def _upsert_full_rules(self, rules_full: Dict[str, Any], rule: Dict[str, Any]) -> None:
        rows: List[Dict[str, Any]] = list(rules_full.get("rules") or [])
        rows = [r for r in rows if r.get("rule_id") != RULE_ID]
        for r in rows:
            try:
                p = int(r.get("priority") or 0)
            except (TypeError, ValueError):
                p = 0
            if p >= 1:
                r["priority"] = p + 1
        rows.insert(0, rule)
        rows.sort(key=lambda r: (int(r.get("priority") or 999), str(r.get("rule_id") or "")))
        rules_full["model_version"] = MODEL_VERSION
        rules_full["rule_count"] = len(rows)
        rules_full["rules"] = rows

    def _upsert_roadmap(self, roadmap: Dict[str, Any], rule: Dict[str, Any]) -> None:
        items: List[Dict[str, Any]] = list(roadmap.get("items") or [])
        items = [i for i in items if i.get("rule_id") != RULE_ID]
        for i in items:
            try:
                p = int(i.get("priority") or 0)
            except (TypeError, ValueError):
                p = 0
            if p >= 1:
                i["priority"] = p + 1
        items.insert(0, {
            "priority": 1,
            "rule_id": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "rule_family": rule["rule_family"],
            "expected_accuracy_gain_pct": rule["expected_accuracy_gain"],
            "estimated_steel_gain_kg": rule["estimated_steel_gain_kg"],
            "dependencies": rule["dependencies"],
            "implementation_phase": rule["implementation_phase"],
            "engineering_risk": rule["engineering_risk"],
            "estimated_complexity": rule["estimated_effort"],
            "status": rule["status"],
            "gap_type": rule["gap_type"],
            "mandatory_validation_rule": True,
            "gate": [
                "before_steel_calculation",
                "before_benchmarking",
                "before_correction_engine",
            ],
        })
        items.sort(key=lambda r: (int(r.get("priority") or 999), str(r.get("rule_id") or "")))
        roadmap["model_version"] = MODEL_VERSION
        roadmap["rule_count"] = len(items)
        roadmap["items"] = items
        if "cumulative_expected_gain_pct" not in roadmap:
            roadmap["cumulative_expected_gain_pct"] = sum(
                float(i.get("expected_accuracy_gain_pct") or 0) for i in items
            )

    def _upsert_traceability(self, traceability: Dict[str, Any], rule: Dict[str, Any]) -> None:
        rows: List[Dict[str, Any]] = list(traceability.get("rows") or [])
        rows = [r for r in rows if r.get("rule_id") != RULE_ID]
        rows.append({
            "issue_id": "RULE-012-INVARIANT",
            "finding_ids": [],
            "rule_id": RULE_ID,
            "rule_family": rule["rule_family"],
            "recommended_phase": "Validation",
            "implementation_phase": "Validation",
            "evidence_count": len(rule.get("supporting_evidence") or []),
            "future_correction": "DETECT::RULE-012 (no auto-fix in R.1.6.2)",
            "future_benchmark": "R.1.4 re-benchmark after coverage restored",
            "mandatory_validation_rule": True,
        })
        traceability["model_version"] = MODEL_VERSION
        traceability["rows"] = rows
        traceability["mapped_issues"] = len({r.get("issue_id") for r in rows if r.get("issue_id")})
        traceability["complete"] = True

    def _upsert_priority_list(self, rule: Dict[str, Any]) -> None:
        path = self.library_dir / "rule_priority_list.json"
        data = self._read("rule_priority_list.json") or {
            "model_version": MODEL_VERSION,
            "title": "Engineering Rule Priority List",
            "items": [],
        }
        items: List[Dict[str, Any]] = list(data.get("items") or [])
        # Seed from library index if empty
        if not items:
            lib = self._read("engineering_rule_library.json") or {}
            for r in lib.get("rules") or []:
                if r.get("rule_id") == RULE_ID:
                    continue
                items.append({
                    "priority": r.get("priority"),
                    "rule_id": r.get("rule_id"),
                    "rule_name": r.get("rule_name"),
                    "status": r.get("status"),
                })
        items = [i for i in items if i.get("rule_id") != RULE_ID]
        for i in items:
            try:
                p = int(i.get("priority") or 0)
            except (TypeError, ValueError):
                p = 0
            if p >= 1:
                i["priority"] = p + 1
        items.insert(0, {
            "priority": 1,
            "priority_label": "HIGH",
            "rule_id": RULE_ID,
            "rule_name": rule["rule_name"],
            "rule_family": rule["rule_family"],
            "status": rule["status"],
            "implementation_phase": rule["implementation_phase"],
            "mandatory_validation_rule": True,
            "gate": [
                "before_steel_calculation",
                "before_benchmarking",
                "before_correction_engine",
            ],
        })
        items.sort(key=lambda r: (int(r.get("priority") or 999), str(r.get("rule_id") or "")))
        data["model_version"] = MODEL_VERSION
        data["items"] = items
        data["mandatory_validation_rules"] = [RULE_ID]
        self._write("rule_priority_list.json", data)

    def _read(self, name: str) -> Any:
        path = self.library_dir / name
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, name: str, data: Dict[str, Any]) -> None:
        path = self.library_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
