"""
QA.2B.0 — End-to-End Benchmark Pipeline Integration orchestrator.
MODEL_VERSION: 9.6.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .integration_qa import IntegrationQA
from .pipeline_integrator import PipelineIntegrator
from .pipeline_validator import PipelineValidator

MODEL_VERSION = "9.6.0"
PHASE_ID = "QA.2B.0"


class PhaseQA2B0Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        output_root: Optional[Path] = None,
    ):
        self.engine_root = Path(engine_root)
        self.output_root = (
            Path(output_root)
            if output_root
            else self.engine_root / "data" / "output" / "PhaseQA2B0_pipeline_integration"
        )
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        *,
        force_track1: bool = False,
        run_benchmark: bool = True,
    ) -> Dict[str, Any]:
        print(f"[{PHASE_ID}] MODEL_VERSION={MODEL_VERSION}")
        print(f"[{PHASE_ID}] output={self.output_root}")

        integrator = PipelineIntegrator(self.engine_root, self.output_root)
        integration = integrator.integrate_all(
            force_track1=force_track1, run_benchmark=run_benchmark
        )

        validator = PipelineValidator(self.engine_root, self.output_root)
        validation = validator.validate(integration)

        qa_writer = IntegrationQA(self.output_root)
        qa = qa_writer.write(integration, validation)
        summary_path = qa_writer.write_execution_summary(integration, validation, qa)

        # Ensure architecture doc is present alongside outputs
        arch_src = Path(__file__).parent / "PipelineArchitecture.md"
        arch_dst = self.output_root / "PipelineArchitecture.md"
        if arch_src.exists():
            arch_dst.write_text(arch_src.read_text(encoding="utf-8"), encoding="utf-8")

        result = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "success": bool(validation.get("overall_pass")),
            "output_root": str(self.output_root),
            "pipeline_validation": str(self.output_root / "PipelineValidation.json"),
            "pipeline_integration_qa": str(self.output_root / "PipelineIntegrationQA.json"),
            "execution_summary": str(summary_path),
            "integration_success": integration.get("success"),
            "validation": validation,
            "qa": qa,
        }
        print(
            f"[{PHASE_ID}] done success={result['success']} "
            f"beams={qa.get('beam_count_processed')} crops={qa.get('crop_count_generated')}"
        )
        return result
