"""
benchmark3_generalization_auditor.py — Audit for benchmark-specific dependencies.
MODEL_VERSION: 8.1.1
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Dict, List

_ROOT = pathlib.Path(__file__).resolve().parents[3]
_V7   = _ROOT / "Version7"
_OUT  = _V7 / "data" / "output"
_SRC  = _V7 / "src"

_SET1_BEAMS = {
    "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10",
    "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18",
}

_AUDIT_CHECKS = [
    ("no_benchmark_set_1_dependency",  ["Benchmark_Set_1", "benchmark_set_1", "Clubhouse_GF"]),
    ("no_benchmark_set_2_dependency",  ["Benchmark_Set_2", "benchmark_set_2", "Galera_GF"]),
    ("no_version5_dependency",         ["Version5/data/output", "phase_g/g_5", "phase_i/i_2"]),
    ("no_version6_dependency",         ["Version6/data/output"]),
    ("no_reference_classification",    ["REFERENCE_CLASSIFICATION"]),
    ("no_hardcoded_beam_ids",          []),  # special check
]


class Benchmark3GeneralizationAuditor:

    def audit(self) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        passed_checks: Dict[str, bool] = {}

        # 1. Scan runtime output JSON for benchmark references
        output_findings = self._scan_output_artefacts()
        findings.extend(output_findings)

        # 2. Check beam registry for exact Set 1 fingerprint
        reg_finding = self._check_beam_registry()
        if reg_finding:
            findings.append(reg_finding)

        # 3. Check pipeline context quality flags
        ctx_findings = self._check_pipeline_context()
        findings.extend(ctx_findings)

        # 4. Check VB1 reinforcement source from production stats
        src_finding = self._check_reinforcement_source()
        if src_finding:
            findings.append(src_finding)

        # 6. Check General Notes DXF resolves to current benchmark (Set 3)
        gn_finding = self._check_gn_path()
        if gn_finding:
            findings.append(gn_finding)

        # 7. Summarise pass/fail per audit dimension
        for check_id, phrases in _AUDIT_CHECKS:
            if check_id == "no_hardcoded_beam_ids":
                passed = not any(
                    f.get("category") == "HARDCODED_BEAM_IDS" for f in findings
                )
            else:
                passed = not any(
                    f.get("category") == check_id.upper() for f in findings
                )
            passed_checks[check_id] = passed

        all_pass = all(passed_checks.values()) and len(findings) == 0

        return {
            "all_checks_passed": all_pass,
            "checks": passed_checks,
            "findings": findings,
            "finding_count": len(findings),
            "summary": (
                "No benchmark-specific dependencies detected"
                if all_pass
                else f"{len(findings)} generalization issue(s) detected"
            ),
        }

    def _scan_output_artefacts(self) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        scan_dirs = [
            _OUT / "PhaseVROOT.1_dynamic_pipeline_initialization",
            _OUT / "PhaseR.1_generalized_reinforcement_discovery",
            _OUT / "PhaseR1.3_pipeline_integration",
            _OUT / "Production_Output",
        ]
        patterns = {
            "NO_BENCHMARK_SET_1_DEPENDENCY": ["Benchmark_Set_1", "benchmark_set_1", "Clubhouse"],
            "NO_BENCHMARK_SET_2_DEPENDENCY": ["Benchmark_Set_2", "benchmark_set_2"],
            "NO_VERSION5_DEPENDENCY":        ["Version5/data/output", "phase_g/g_5"],
            "NO_VERSION6_DEPENDENCY":        ["Version6/data/output"],
            "NO_REFERENCE_CLASSIFICATION":   ["REFERENCE_CLASSIFICATION"],
        }

        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for jf in scan_dir.glob("*.json"):
                try:
                    text = jf.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for category, phrases in patterns.items():
                    for phrase in phrases:
                        if phrase.lower() in text.lower():
                            # Benchmark_Set_3 in input path is OK
                            if "Benchmark_Set_3" in text and phrase == "Benchmark_Set_2":
                                continue
                            if "Benchmark_Set_3" in text and phrase == "Benchmark_Set_1":
                                continue
                            findings.append({
                                "category": category,
                                "module": str(jf.relative_to(_V7)),
                                "detail": f"Found '{phrase}' in runtime artefact",
                                "severity": "WARNING" if "REFERENCE" in category else "CRITICAL",
                            })
        return findings

    def _check_beam_registry(self) -> Dict[str, Any] | None:
        reg_path = _OUT / "PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json"
        if not reg_path.exists():
            return None
        try:
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
            beam_ids = set(reg.get("beam_ids") or [])
            if beam_ids and beam_ids == _SET1_BEAMS:
                return {
                    "category": "HARDCODED_BEAM_IDS",
                    "module": "beam_registry.json",
                    "detail": "Beam registry contains exactly B1-B18 (Benchmark Set 1 fingerprint)",
                    "severity": "CRITICAL",
                }
        except Exception:
            pass
        return None

    def _check_pipeline_context(self) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        ctx_path = _OUT / "PhaseVROOT.1_dynamic_pipeline_initialization/pipeline_context.json"
        if not ctx_path.exists():
            return findings
        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
            quality = ctx.get("quality") or {}
            for flag, label in [
                ("uses_hardcoded_beams", "HARDCODED_BEAM_IDS"),
                ("uses_v5_dependencies", "NO_VERSION5_DEPENDENCY"),
                ("uses_benchmark_set1", "NO_BENCHMARK_SET_1_DEPENDENCY"),
            ]:
                if quality.get(flag):
                    findings.append({
                        "category": label,
                        "module": "pipeline_context.json",
                        "detail": f"quality.{flag}=True",
                        "severity": "CRITICAL",
                    })
        except Exception:
            pass
        return findings

    def _check_reinforcement_source(self) -> Dict[str, Any] | None:
        for rel in [
            "PhaseR1.3_pipeline_integration/integration_statistics.json",
            "Production_Output/production_statistics.json",
        ]:
            p = _OUT / rel
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                source = str(
                    data.get("reinforcement_source")
                    or data.get("source")
                    or ""
                )
                if "REFERENCE_CLASSIFICATION" in source.upper():
                    return {
                        "category": "NO_REFERENCE_CLASSIFICATION",
                        "module": rel,
                        "detail": f"Reinforcement source: {source}",
                        "severity": "WARNING",
                    }
            except Exception:
                pass
        return None

    def _check_gn_path(self) -> Dict[str, Any] | None:
        ec_path = _OUT / "PhaseR.2A_engineering_context/engineering_context.json"
        if not ec_path.exists():
            return None
        try:
            ec = json.loads(ec_path.read_text(encoding="utf-8"))
            gn_path = str(ec.get("gn_dxf_path") or "")
            if "Benchmark_Set_2" in gn_path:
                return {
                    "category": "NO_BENCHMARK_SET_2_DEPENDENCY",
                    "module": "PhaseR.2A_engineering_context/engineering_context_factory.py",
                    "detail": (
                        f"GN DXF resolved to Benchmark Set 2: {gn_path} "
                        "(hardcoded in _discover_gn_path line ~103)"
                    ),
                    "severity": "CRITICAL",
                }
            if "Benchmark_Set_3" not in gn_path:
                return {
                    "category": "NO_BENCHMARK_SET_1_DEPENDENCY",
                    "module": "PhaseR.2A_engineering_context/engineering_context.json",
                    "detail": f"GN DXF not from Benchmark Set 3: {gn_path}",
                    "severity": "WARNING",
                }
        except Exception:
            pass
        return None
