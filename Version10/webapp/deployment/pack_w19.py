"""Build a W.19 runtime tarball: W.16 metadata + W.18B spacer + release label.

No .env, no caches, no web_runs, no API keys.
"""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w19_runtime.tar.gz")

FILES = [
    # W.16
    "src/PhaseP2610D1_vision_semantic_contract_hybrid_foundation/normalize.py",
    "src/PhaseR.2A_engineering_context/concrete_grade_parser.py",
    "src/PhaseR.2A_engineering_context/cover_parser.py",
    "src/PhaseR.2A_engineering_context/development_length_parser.py",
    "src/PhaseR.2A_engineering_context/engineering_context_factory.py",
    "src/PhaseR.2A_engineering_context/engineering_context_loader.py",
    "src/PhaseR.2A_engineering_context/general_notes_text_extractor.py",
    "src/PhaseR.2A_engineering_context/steel_grade_parser.py",
    "src/PhaseR1.3_pipeline_integration/engineering_bar_builder.py",
    "src/PhaseVB.1_production_output_completion/bbs_completion_engine.py",
    "src/PhaseVB.1_production_output_completion/estimator_excel_generator.py",
    "src/PhaseVB.1_production_output_completion/phase_vb1_orchestrator.py",
    "src/PhaseVB.1_production_output_completion/steel_weight_completion.py",
    "src/PhaseVB.1_production_output_completion/workbook_validator.py",
    "src/PhaseVROOT.1_dynamic_pipeline_initialization/project_discovery.py",
    "webapp/tests/test_w16_metadata_aggregation.py",
    "webapp/deployment/PHASE_W16_METADATA_AND_AGGREGATION_REPORT.md",
    "webapp/deployment/W16_INVESTIGATION.md",
    # W.18B spacer
    "src/PhaseV9_spacer_rule/__init__.py",
    "src/PhaseV9_spacer_rule/r13_injector.py",
    "src/PhaseV9_spacer_rule/spacer_engine.py",
    "src/PhaseV9_spacer_rule/spacer_models.py",
    "src/PhaseV9_spacer_rule/tests/test_spacer_engine.py",
    "src/PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py",
    "src/PhaseR1_2B_engineeringbar_consolidation/engineeringbar_consolidator.py",
    "webapp/deployment/PHASE_W18B_SPACER_RULE_CORRECTION.md",
    "webapp/deployment/W18B_SPACER_VALIDATION_TRACE.json",
    "webapp/deployment/_w18b_spacer_replay.py",
    # W.19 release label
    "webapp/config.py",
    "webapp/routes.py",
    "webapp/tests/test_w5_hybrid_shadow.py",
    "webapp/tests/test_w6_hybrid_authority.py",
    "webapp/tests/test_w12_result_delivery.py",
    "webapp/tests/test_w13_hybrid_download.py",
    "webapp/tests/test_w14_hybrid_recovery.py",
]


def main() -> None:
    missing = [rel for rel in FILES if not (ENGINE / rel).is_file()]
    if missing:
        raise SystemExit("missing: " + ", ".join(missing))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(OUT, "w:gz") as tar:
        for rel in FILES:
            tar.add(ENGINE / rel, arcname="Version10/" + rel.replace("\\", "/"))
    print("FILES", len(FILES))
    print("OUT", OUT)
    print("BYTES", OUT.stat().st_size)


if __name__ == "__main__":
    main()
