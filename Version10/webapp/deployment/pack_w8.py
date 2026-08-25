"""Build a W.8 runtime tarball. No .env, no caches, no web_runs."""
from __future__ import annotations

import tarfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w8_runtime.tar.gz")

FILES = [
    "src/PhaseW8_production_vision_evidence/__init__.py",
    "src/PhaseW8_production_vision_evidence/config.py",
    "src/PhaseW8_production_vision_evidence/generator.py",
    "src/PhaseW8_production_vision_evidence/package.py",
    "src/PhaseW6_hybrid_production_authority/__init__.py",
    "src/PhaseW6_hybrid_production_authority/__main__.py",
    "src/PhaseW6_hybrid_production_authority/config.py",
    "src/PhaseW6_hybrid_production_authority/coverage.py",
    "src/PhaseW6_hybrid_production_authority/handoff.py",
    "src/PhaseW6_hybrid_production_authority/observability.py",
    "src/PhaseW6_hybrid_production_authority/orchestrator.py",
    "src/PhaseW6_hybrid_production_authority/visuals.py",
    "src/PhaseW5_production_hybrid_shadow/adapter.py",
    "src/PhaseW5_production_hybrid_shadow/catalog.py",
    "src/PhaseW5_production_hybrid_shadow/comparison.py",
    "src/PhaseW5_production_hybrid_shadow/config.py",
    "src/PhaseW5_production_hybrid_shadow/cost.py",
    "src/PhaseW5_production_hybrid_shadow/live_invoke.py",
    "src/PhaseW5_production_hybrid_shadow/paths.py",
    "src/PhaseW5_production_hybrid_shadow/semantic.py",
    "src/PhaseW5_production_hybrid_shadow/settings.py",
    "src/PhaseW5_production_hybrid_shadow/visual_sources.py",
    "src/PhaseW5_production_hybrid_shadow/__init__.py",
    "src/PhaseW5_production_hybrid_shadow/__main__.py",
    "src/PhaseP2610E2_fifth_set_full_population_live_vision_hybrid_accuracy_benchmark/live_caller.py",
    "src/PhaseP2610A_beam_region_crop_audit/__init__.py",
    "src/PhaseP2610A_beam_region_crop_audit/config.py",
    "src/PhaseP2610A_beam_region_crop_audit/title_localizer.py",
    "src/PhaseP2610A_beam_region_crop_audit/region_builder.py",
    "src/PhaseP2610A_beam_region_crop_audit/cropper.py",
    "src/PhaseP2610B_adaptive_beam_detail_crop/__init__.py",
    "src/PhaseP2610B_adaptive_beam_detail_crop/config.py",
    "src/PhaseP2610B_adaptive_beam_detail_crop/envelope.py",
    "src/PhaseP2610B_adaptive_beam_detail_crop/evidence.py",
    "src/PhaseP2610B_adaptive_beam_detail_crop/completeness.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/__init__.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/config.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/geometry.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/quality.py",
    "src/PhaseP2610C1C2_evidence_inventory_candidate_selection/__init__.py",
    "src/PhaseP2610C1C2_evidence_inventory_candidate_selection/config.py",
    "src/PhaseP2610C1C2_evidence_inventory_candidate_selection/inventory.py",
    "src/PhaseP2610C1C2_evidence_inventory_candidate_selection/selector.py",
    "src/PhaseP2610C3_visual_completeness_claude_shadow/config.py",
    "src/PhaseP2610C3_visual_completeness_claude_shadow/evidence_model.py",
    "src/PhaseP2610C3_visual_completeness_claude_shadow/target_anchor_validator.py",
    "src/PhaseP2610C3_visual_completeness_claude_shadow/visual_completeness_gate.py",
    "webapp/config.py",
    "webapp/routes.py",
    "webapp/deployment/steel-beam-estimator-v10.service",
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
