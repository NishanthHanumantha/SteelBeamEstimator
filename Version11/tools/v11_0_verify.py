"""V11.0 verification: syntax, import, and byte-identity vs Version10."""
from __future__ import annotations

import ast
import compileall
import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
V10 = REPO / "Version10"
V11 = REPO / "Version11"

IDENTITY_DIFFS = {
    "webapp/config.py",
    "webapp/services/version10_adapter.py",
    "webapp/tests/test_w2_smoke.py",
    # Mixed-package inits: skip research orchestrator side-effects on import.
    "src/PhaseP2610C5_stratified_vision_semantic_benchmark/__init__.py",
    "src/PhaseP2610C3_visual_completeness_claude_shadow/__init__.py",
    "src/PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark/__init__.py",
    "src/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/__init__.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/__init__.py",
    "src/PhaseP2610C1C2_evidence_inventory_candidate_selection/__init__.py",
    "src/PhaseP2610D1_vision_semantic_contract_hybrid_foundation/__init__.py",
    "src/PhaseP2610D2_shadow_hybrid_semantic_resolver/__init__.py",
    "src/PhaseP2610D3_hybrid_engineering_binding_compatibility/__init__.py",
    "src/PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark/__init__.py",
}

RUNNERS = [
    "run_phase_vroot1_dynamic_pipeline_initialization.py",
    "run_phase_r1_generalized_reinforcement_discovery.py",
    "run_phase_t1_geometric_stirrup_evidence.py",
    "run_phase_r2a_engineering_context.py",
    "run_phase_r21b_semantic_interpreter.py",
    "run_phase_r21c_engineering_fact_normalization.py",
    "run_phase_r21d_evidence_hypothesis_engine.py",
    "run_phase_l2_2_geometry_recovery.py",
    "run_phase_r3_geometry_context_engine.py",
    "run_phase_r31_engineering_relationship_engine.py",
    "run_phase_r12a_geometry_accuracy.py",
    "run_phase_r13_pipeline_integration.py",
    "run_phase_w6_hybrid_production_authority.py",
    "run_phase_vb1_production_output_completion.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    report = {
        "compileall": {},
        "ast_parse_errors": [],
        "hash": {"matched": 0, "identity_diffs": [], "true_diffs": [], "v11_only": [], "v10_missing": []},
        "import_runners": [],
    }

    ok_compile = True
    for rel in ("src", "Run_PY", "webapp", "config"):
        target = V11 / rel
        if not target.exists():
            continue
        ok = compileall.compile_dir(str(target), quiet=1, force=False)
        report["compileall"][rel] = bool(ok)
        ok_compile = ok_compile and bool(ok)

    for p in V11.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            report["ast_parse_errors"].append({"file": str(p.relative_to(V11)), "error": str(exc)})

    compare_roots = ["src", "Run_PY", "config", "webapp"]
    for root in compare_roots:
        for p in (V11 / root).rglob("*"):
            if p.is_dir() or "__pycache__" in p.parts:
                continue
            if p.suffix in {".log", ".pyc"} or p.name.startswith("~$"):
                continue
            rel = p.relative_to(V11).as_posix()
            src = V10 / rel
            if not src.exists():
                report["hash"]["v11_only"].append(rel)
                continue
            if sha256(p) == sha256(src):
                report["hash"]["matched"] += 1
            elif rel in IDENTITY_DIFFS:
                report["hash"]["identity_diffs"].append(rel)
            else:
                report["hash"]["true_diffs"].append(rel)

    sys.path.insert(0, str(V11))
    sys.path.insert(0, str(V11 / "src"))
    sys.path.insert(0, str(V11 / "webapp"))
    for runner in RUNNERS:
        path = V11 / "Run_PY" / runner
        item = {"runner": runner, "ok": False, "error": None}
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"))
            spec = importlib.util.spec_from_file_location(f"v11_{path.stem}", path)
            # Do not exec runners (they may start CLIs). Syntax+spec only.
            item["ok"] = spec is not None
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        report["import_runners"].append(item)

    modules = [
        "PhaseW6_hybrid_production_authority.orchestrator",
        "PhaseW5_production_hybrid_shadow.adapter",
        "PhaseW8_production_vision_evidence.generator",
        "PhaseVB.1_production_output_completion.phase_vb1_orchestrator",
    ]
    # dotted names with dots in package folders won't import; skip VB dotted.
    report["module_imports"] = []
    for name, fpath in [
        ("w6_orchestrator", V11 / "src/PhaseW6_hybrid_production_authority/orchestrator.py"),
        ("w5_adapter", V11 / "src/PhaseW5_production_hybrid_shadow/adapter.py"),
        ("w8_generator", V11 / "src/PhaseW8_production_vision_evidence/generator.py"),
        ("handoff", V11 / "src/PhaseW6_hybrid_production_authority/handoff.py"),
        ("claude_call", V11 / "src/PhaseP2610C5_stratified_vision_semantic_benchmark/claude_call.py"),
        ("vision_prompt", V11 / "src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_prompt.py"),
        ("live_invoke", V11 / "src/PhaseW5_production_hybrid_shadow/live_invoke.py"),
        ("run_context", V11 / "src/config/run_context.py"),
    ]:
        row = {"name": name, "ok": False, "error": None}
        try:
            spec = importlib.util.spec_from_file_location(name, fpath)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            row["ok"] = True
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["trace"] = traceback.format_exc()[-800:]
        report["module_imports"].append(row)

    report["ok_compile"] = ok_compile and not report["ast_parse_errors"]
    report["ok_identity"] = not report["hash"]["true_diffs"]
    report["ok_runners"] = all(x["ok"] for x in report["import_runners"])
    report["ok_modules"] = all(x["ok"] for x in report["module_imports"])

    out = V11 / "docs" / "V11_0_VERIFICATION.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("ok_compile", "ok_identity", "ok_runners", "ok_modules", "compileall")}, indent=2))
    print("true_diffs", report["hash"]["true_diffs"])
    print("identity_diffs", report["hash"]["identity_diffs"])
    print("ast_errors", len(report["ast_parse_errors"]))
    failed_mods = [x for x in report["module_imports"] if not x["ok"]]
    if failed_mods:
        print("FAILED_MODULES")
        for x in failed_mods:
            print(x["name"], x["error"])
    return 0 if report["ok_compile"] and report["ok_identity"] and report["ok_runners"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
