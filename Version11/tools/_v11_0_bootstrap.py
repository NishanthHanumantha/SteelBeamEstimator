"""Phase V11.0 — copy Version10 production boundary into Version11.

Does not modify Version10 source. Byte-copies required runtime files, then
applies documented V11 identity edits only.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
V10 = REPO / "Version10"
V11 = REPO / "Version11"

SKIP_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "uploads",
    "outputs",
    "logs",
}

SKIP_FILE_SUFFIXES = {".pyc", ".pyo", ".log"}
SKIP_FILE_PREFIXES = ("~$",)

PRODUCTION_RUNNERS = [
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

SRC_PACKAGES = [
    "PhaseVROOT.1_dynamic_pipeline_initialization",
    "PhaseR.1_generalized_reinforcement_discovery",
    "PhaseT1_geometric_stirrup_evidence",
    "PhaseT16_entity_ownership",
    "PhaseR.2A_engineering_context",
    "PhaseR2.1B_engineering_semantic_interpreter",
    "PhaseR2.1C_engineering_fact_normalization",
    "PhaseR2.1D_evidence_hypothesis_engine",
    "PhaseL.2.2_geometry_recovery",
    "PhaseR3_geometry_context_engine",
    "PhaseR3.1_engineering_relationship_engine",
    "PhaseR1_2A_geometry_accuracy",
    "PhaseR1.3_pipeline_integration",
    "PhaseR1_2B_engineeringbar_consolidation",
    "PhaseR1_2C_engineering_intent_resolution",
    "PhaseR1_2D_reinforcement_detailing",
    "PhaseR1_3_reinforcement_piece_generation",
    "PhaseV9_spacer_rule",
    "PhaseSI.1_stirrup_improvement",
    "PhaseVB.1_production_output_completion",
    "PhaseW5_production_hybrid_shadow",
    "PhaseW6_hybrid_production_authority",
    "PhaseW8_production_vision_evidence",
    "PhaseW11_hybrid_reliability",
    "PhaseP253_claude_vision_interpretation_pilot",
    "PhaseP2610C5_stratified_vision_semantic_benchmark",
    "PhaseP2610C3_visual_completeness_claude_shadow",
    "PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark",
    "PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark",
    "PhaseP2610D1_vision_semantic_contract_hybrid_foundation",
    "PhaseP2610D2_shadow_hybrid_semantic_resolver",
    "PhaseP2610D3_hybrid_engineering_binding_compatibility",
    "PhaseP2610D4_shadow_hybrid_engineering_calculation_accuracy_benchmark",
    "PhaseP269_reinforcement_group_interpretation",
    "PhaseP2610A_beam_region_crop_audit",
    "PhaseP2610B_adaptive_beam_detail_crop",
    "PhaseP2610B2_render_quality_directional_recovery",
    "PhaseP2610C1C2_evidence_inventory_candidate_selection",
    "PhaseM.1_engineering_vision_dataset",
    "config",
    "llm",
]

WEBAPP_FILES = [
    "app.py",
    "wsgi.py",
    "routes.py",
    "config.py",
    "requirements.txt",
    ".gitignore",
    "README.md",
]
WEBAPP_DIRS = ["services", "templates", "static", "tests"]
WEBAPP_TEST_KEEP = {
    "test_w2_smoke.py",
    "test_w6_hybrid_authority.py",
    "test_w16_metadata_aggregation.py",
    "test_w191_excel_metadata_binding.py",
    "test_w5_hybrid_shadow.py",
    "test_w12_result_delivery.py",
    "test_w13_hybrid_download.py",
    "test_w14_hybrid_recovery.py",
    "__init__.py",
}
WEBAPP_DEPLOY_KEEP = {
    "PHASE_W19_1_EXCEL_PROJECT_METADATA_BINDING_HOTFIX.md",
    "steel-beam-estimator-v10.env.example",
}


def _skip_file(path: Path) -> bool:
    name = path.name
    if name.startswith(SKIP_FILE_PREFIXES):
        return True
    if path.suffix.lower() in SKIP_FILE_SUFFIXES:
        return True
    return False


def copy_tree(src: Path, dst: Path) -> int:
    if not src.exists():
        raise FileNotFoundError(src)
    n = 0
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return 1
    for p in src.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in p.parts):
            continue
        if p.is_dir():
            continue
        if _skip_file(p):
            continue
        rel = p.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        n += 1
    return n


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    if not V10.is_dir():
        print("MISSING Version10", file=sys.stderr)
        return 2
    if V11.exists():
        print("Version11 already exists — refusing to overwrite", file=sys.stderr)
        return 3

    copied = []
    V11.mkdir(parents=True)

    for pkg in SRC_PACKAGES:
        src = V10 / "src" / pkg
        if not src.exists():
            print("MISSING package", pkg, file=sys.stderr)
            return 4
        n = copy_tree(src, V11 / "src" / pkg)
        copied.append({"kind": "src_package", "name": pkg, "files": n})

    for runner in PRODUCTION_RUNNERS:
        src = V10 / "Run_PY" / runner
        if not src.exists():
            print("MISSING runner", runner, file=sys.stderr)
            return 5
        copy_tree(src, V11 / "Run_PY" / runner)
        copied.append({"kind": "runner", "name": runner, "files": 1})

    n = copy_tree(V10 / "config", V11 / "config")
    copied.append({"kind": "config_yaml", "name": "config", "files": n})

    for name in WEBAPP_FILES:
        src = V10 / "webapp" / name
        if src.exists():
            copy_tree(src, V11 / "webapp" / name)

    for dname in WEBAPP_DIRS:
        src = V10 / "webapp" / dname
        if dname == "tests":
            dst = V11 / "webapp" / "tests"
            dst.mkdir(parents=True)
            for tf in WEBAPP_TEST_KEEP:
                s = src / tf
                if s.exists():
                    copy_tree(s, dst / tf)
            continue
        copy_tree(src, V11 / "webapp" / dname)

    deploy_src = V10 / "webapp" / "deployment"
    for name in WEBAPP_DEPLOY_KEEP:
        s = deploy_src / name
        if s.exists():
            copy_tree(s, V11 / "docs" / "v10_deployment_reference" / name)

    copy_tree(V10 / "requirements.txt", V11 / "requirements.txt")
    if (V10 / "webapp" / "requirements.txt").exists():
        copy_tree(V10 / "webapp" / "requirements.txt", V11 / "webapp" / "requirements.txt")

    n = copy_tree(V10 / "data" / "Benchmark_Set_2", V11 / "data" / "benchmarks" / "Benchmark_Set_2")
    copied.append({"kind": "benchmark", "name": "Benchmark_Set_2", "files": n})

    # Keep GN fallback path that R.2A factory expects: data/Benchmark_Set_2/general_notes
    (V11 / "data" / "Benchmark_Set_2").mkdir(parents=True, exist_ok=True)
    gn_src = V10 / "data" / "Benchmark_Set_2"
    # also mirror at V10-compatible location used by factory
    n2 = copy_tree(gn_src, V11 / "data" / "Benchmark_Set_2")
    copied.append({"kind": "benchmark_factory_path", "name": "data/Benchmark_Set_2", "files": n2})

    for keep in (V11 / "data" / "output", V11 / "data" / "web_runs", V11 / "webapp" / "uploads", V11 / "webapp" / "outputs", V11 / "webapp" / "logs"):
        keep.mkdir(parents=True, exist_ok=True)
        (keep / ".gitkeep").write_text("", encoding="utf-8")

    baseline = V11 / "data" / "baseline"
    baseline.mkdir(parents=True, exist_ok=True)
    fixture_pairs = [
        (
            V10 / "data/output/PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark/_pdf_fixture/accuracy_report_data.json",
            baseline / "P2610E1_accuracy_report_data.json",
        ),
        (
            V10 / "data/output/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/_pdf_fixture/accuracy_report_data.json",
            baseline / "P2610E2_accuracy_report_data.json",
        ),
        (
            V10 / "data/output/PhaseP2610E1_fifth_set_hybrid_accuracy_benchmark/_pdf_fixture/P2.6.10-E.1_RESULTS.json",
            baseline / "P2610E1_RESULTS.json",
        ),
        (
            V10 / "data/output/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/_pdf_fixture/P2.6.10-E.2_RESULTS.json",
            baseline / "P2610E2_RESULTS.json",
        ),
    ]
    for src, dst in fixture_pairs:
        if src.exists():
            copy_tree(src, dst)

    gitignore = """# Version11 local artifacts
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
.env
.env.*
*.pem
*.log
data/output/**
!data/output/.gitkeep
data/web_runs/**
!data/web_runs/.gitkeep
webapp/uploads/**
!webapp/uploads/.gitkeep
webapp/outputs/**
!webapp/outputs/.gitkeep
webapp/logs/**
!webapp/logs/.gitkeep
"""
    (V11 / ".gitignore").write_text(gitignore, encoding="utf-8")

    # Identity edits (documented V11-only differences)
    cfg = V11 / "webapp" / "config.py"
    text = cfg.read_text(encoding="utf-8")
    text = text.replace('ENGINE_LABEL = "Version10"', 'ENGINE_LABEL = "Version11"')
    text = text.replace(
        'ENGINE_DISPLAY = "Version10 production pipeline"',
        'ENGINE_DISPLAY = "Version11 development pipeline"',
    )
    text = text.replace(
        "# Historical alias used by older web copies; always Version10 in this tree.",
        "# Historical alias; ENGINE_ROOT is Version11 in this tree.",
    )
    cfg.write_text(text, encoding="utf-8")

    adapter = V11 / "webapp" / "services" / "version10_adapter.py"
    at = adapter.read_text(encoding="utf-8")
    at = at.replace(
        'if "version10" not in engine_root.lower().replace("\\\\", "/"):',
        'if not any(tag in engine_root.lower().replace("\\\\", "/") for tag in ("version10", "version11")):',
    )
    adapter.write_text(at, encoding="utf-8")

    smoke = V11 / "webapp" / "tests" / "test_w2_smoke.py"
    st = smoke.read_text(encoding="utf-8")
    st = st.replace('self.assertEqual(data["engine_label"], "Version10")', 'self.assertEqual(data["engine_label"], "Version11")')
    st = st.replace('self.assertIn("Version10 production pipeline", html)', 'self.assertIn("Version11 development pipeline", html)')
    st = st.replace('self.assertEqual(config.ENGINE_ROOT.name, "Version10")', 'self.assertEqual(config.ENGINE_ROOT.name, "Version11")')
    smoke.write_text(st, encoding="utf-8")

    inventory = {
        "source": str(V10),
        "dest": str(V11),
        "copied": copied,
        "src_packages": SRC_PACKAGES,
        "runners": PRODUCTION_RUNNERS,
    }
    (V11 / "docs").mkdir(parents=True, exist_ok=True)
    (V11 / "docs" / "V11_0_COPY_INVENTORY.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8"
    )
    print("CREATED", V11)
    print("PACKAGES", len(SRC_PACKAGES), "RUNNERS", len(PRODUCTION_RUNNERS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
