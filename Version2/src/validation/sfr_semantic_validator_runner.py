"""Phase D.1.7F — orchestration for SFR semantic validation."""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from src.config.output_paths import OutputPaths
from src.validation.sfr_semantic_debug_exporter import SfrSemanticDebugExporter
from src.validation.sfr_semantic_validator import SfrSemanticResult, SfrSemanticValidator


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


def run_semantic_validation(
    validated_master_path: Path,
    output_paths: OutputPaths,
) -> SfrSemanticResult:
    output_paths.phase_d17f_dir.mkdir(parents=True, exist_ok=True)

    master_records = load_json(validated_master_path)
    if not isinstance(master_records, list):
        raise ValueError("validated_annotations_master must be a list")

    result = SfrSemanticValidator().validate(master_records)

    write_json(
        output_paths.engineering_annotations_semantic,
        result["engineering_annotations_semantic"],
    )
    write_json(output_paths.sfr_semantic_validation, result["validation"])
    write_json(output_paths.sfr_semantic_summary, result["summary"])
    write_text(output_paths.sfr_semantic_report_txt, result["report_text"])
    write_json(output_paths.engineering_dataset_phase_d17f, result["refined_master"])

    SfrSemanticDebugExporter().export(
        result["semantic_records"],
        output_paths.sfr_semantic_debug_dxf,
    )

    return result
