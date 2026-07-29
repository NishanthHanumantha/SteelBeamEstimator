"""
Build OfficialWorkbookModel from estimator workbook interpretation.
MODEL_VERSION: 8.6.0
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

from beam_group_parser import BeamGroupParser
from beam_table_parser import BeamTableParser
from estimator_workbook_loader import EstimatorWorkbookLoader
from models import OfficialProject, OfficialWorkbookModel
from summary_table_parser import SummaryTableParser
from table_detector import TableDetector

MODEL_VERSION = "8.6.0"


class OfficialModelBuilder:
    def build(self, workbook_path: Union[str, Path]) -> OfficialWorkbookModel:
        loader = EstimatorWorkbookLoader(workbook_path)
        try:
            detector = TableDetector(loader.grids)
            detected = detector.detect_all()

            summary = SummaryTableParser(loader.grids, detected).parse()
            table_info = BeamTableParser(loader.grids, detected).locate()

            beams = []
            interpretation: Dict[str, Any] = {
                "detected_tables": [t.to_dict() for t in detected],
                "loader": loader.info(),
                "summary_detected": summary.source_header_row > 0,
                "breakup_detected": table_info is not None,
            }

            if table_info:
                grid = loader.grids[table_info["sheet_name"]]
                beams = BeamGroupParser().parse(
                    grid=grid,
                    sheet_name=table_info["sheet_name"],
                    header_row=table_info["header_row"],
                    column_map=table_info["column_map"],
                    diameters=table_info["diameters"],
                    data_start_row=table_info["data_start_row"],
                )
                interpretation["beam_table"] = {
                    "sheet_name": table_info["sheet_name"],
                    "header_row": table_info["header_row"] + 1,
                    "column_map": table_info["column_map"],
                    "diameters": {str(k): v for k, v in table_info["diameters"].items()},
                    "beam_count": len(beams),
                    "reinforcement_row_count": sum(len(b.reinforcement_rows) for b in beams),
                }

            project = OfficialProject(
                project_name=summary.project_name,
                block=summary.block,
                floor=summary.floor,
                workbook_path=str(Path(workbook_path).resolve()),
                sheet_names=loader.sheet_names,
            )

            return OfficialWorkbookModel(
                project=project,
                steel_summary=summary,
                beams=beams,
                interpretation=interpretation,
                model_version=MODEL_VERSION,
            )
        finally:
            loader.close()
