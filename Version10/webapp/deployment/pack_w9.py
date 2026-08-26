"""Build a W.9 runtime tarball (W.8 evidence path). No .env, no caches, no web_runs.

C1C2 / B2 / C3 package __init__ files are replaced with production stubs so
importing selector / quality / visual_completeness_gate does not load research
orchestrators.
"""
from __future__ import annotations

import io
import tarfile
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w9_runtime.tar.gz")

STUB_INIT = '''"""Production runtime package. Research orchestrator is not imported."""
'''

STUB_INIT_PATHS = {
    "src/PhaseP2610C1C2_evidence_inventory_candidate_selection/__init__.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/__init__.py",
    "src/PhaseP2610C3_visual_completeness_claude_shadow/__init__.py",
}

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
    "src/PhaseP2610B2_render_quality_directional_recovery/config.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/geometry.py",
    "src/PhaseP2610B2_render_quality_directional_recovery/quality.py",
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


def _add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    info.mtime = int(time.time())
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def main() -> None:
    missing = [rel for rel in FILES if not (ENGINE / rel).is_file()]
    if missing:
        raise SystemExit("missing: " + ", ".join(missing))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(OUT, "w:gz") as tar:
        for rel in FILES:
            tar.add(ENGINE / rel, arcname="Version10/" + rel.replace("\\", "/"))
        for rel in sorted(STUB_INIT_PATHS):
            _add_bytes(
                tar,
                "Version10/" + rel.replace("\\", "/"),
                STUB_INIT.encode("utf-8"),
            )
    print("FILES", len(FILES) + len(STUB_INIT_PATHS))
    print("STUBS", len(STUB_INIT_PATHS))
    print("OUT", OUT)
    print("BYTES", OUT.stat().st_size)


if __name__ == "__main__":
    main()
