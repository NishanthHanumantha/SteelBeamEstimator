"""Phase D.1.7G — run SFR discovery audit and write outputs."""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths
from src.validation.sfr_discovery_audit import SfrDiscoveryAudit, SfrDiscoveryAuditResult
from src.validation.sfr_discovery_debug_exporter import SfrDiscoveryDebugExporter

DEFAULT_DXF = Path("data/reinforcement/Beam_ReinforcementDetails.dxf")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    logger.info("Wrote {}", path.resolve())


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote {}", path.resolve())


def run_discovery_audit(
    paths: OutputPaths,
    dxf_path: Path = DEFAULT_DXF,
) -> SfrDiscoveryAuditResult:
    paths.phase_d17g_dir.mkdir(parents=True, exist_ok=True)

    for label, path in (
        ("engineering D.1.7F", paths.engineering_dataset_phase_d17f),
        ("sketches", paths.beam_sketches_debug),
        ("sketch ownership", paths.sketch_ownership),
        ("header occurrences", paths.header_occurrences),
        ("dxf", dxf_path),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    engineering_d17f = load_json(paths.engineering_dataset_phase_d17f)
    sketches = load_json(paths.beam_sketches_debug)
    ownership = load_json(paths.sketch_ownership)
    occurrences = load_json(paths.header_occurrences)

    result = SfrDiscoveryAudit(paths.root).run(
        str(dxf_path.resolve()),
        sketches,
        ownership,
        occurrences,
        engineering_d17f,
    )

    write_json(paths.sfr_discovery_inventory, result["inventory"])
    write_json(paths.sfr_discovery_expected_vs_found, result["expected_vs_found"])
    write_json(paths.sfr_discovery_pipeline_loss, result["pipeline_loss"])
    write_json(paths.sfr_discovery_root_cause, result["root_causes"])
    write_json(paths.sfr_discovery_summary, result["summary"])
    write_json(paths.sfr_discovery_validation, result["validation"])
    write_text(paths.sfr_discovery_report_txt, result["report_text"])

    SfrDiscoveryDebugExporter().export(
        result["inventory"],
        result["expected_vs_found"],
        paths.engineering_dataset_phase_d17f,
        paths.sfr_discovery_debug_dxf,
    )

    return result
