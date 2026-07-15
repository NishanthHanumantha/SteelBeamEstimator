"""
Block Expansion Writer — exports Phase R.2A.2 JSON artefacts.
"""
from __future__ import annotations
import json
import pathlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .general_notes_text_extractor import GeneralNotesTextExtractor
from .development_length_parser import DevelopmentLengthParser
from .engineering_context_model import EngineeringContext
from .engineering_context_loader import EngineeringContextLoader
from .block_expansion_validator import BlockExpansionValidator, ValidationResult

_STEEL_GRADE_PAT = re.compile(r"LD\s+FOR\s+(?:FY|FE)[-\s]?(\d{3,4})", re.I)


def _save(out: pathlib.Path, name: str, data: Any) -> str:
    p = out / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(p)


class BlockExpansionWriter:
    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def write_all(
        self,
        extractor: GeneralNotesTextExtractor,
        ctx: EngineeringContext,
        loader: EngineeringContextLoader,
        validation_results: List[ValidationResult],
    ) -> Dict[str, str]:
        ts = datetime.utcnow().isoformat()
        paths: Dict[str, str] = {}

        inventory = extractor.extract_inventory()
        report = extractor.get_expansion_report()
        hierarchy = extractor.get_block_hierarchy()

        dl_parser = DevelopmentLengthParser(extractor)
        dl_entries, dl_warnings, dl_audit = dl_parser.parse()

        # 1. expanded_text_inventory.json
        paths["expanded_text_inventory"] = _save(self._out, "expanded_text_inventory.json", {
            "generated": ts,
            "model_version": "7.5.3",
            "total_entities": len(inventory),
            "by_source": {
                "TOP_LEVEL": sum(1 for r in inventory if r.source == "TOP_LEVEL"),
                "BLOCK": sum(1 for r in inventory if r.source == "BLOCK"),
                "NESTED_BLOCK": sum(1 for r in inventory if r.source == "NESTED_BLOCK"),
            },
            "entities": [
                {
                    "entity_id": r.entity_id,
                    "text": r.text[:200],
                    "layer": r.layer,
                    "x": r.x, "y": r.y,
                    "entity_type": r.entity_type,
                    "parent_block": r.parent_block,
                    "nesting_depth": r.nesting_depth,
                    "rotation": r.rotation,
                    "source": r.source,
                    "block_path": r.block_path,
                }
                for r in inventory
            ],
        })

        # 2. block_hierarchy.json
        paths["block_hierarchy"] = _save(self._out, "block_hierarchy.json", {
            "generated": ts,
            **hierarchy,
            "expansion_summary": {
                "insert_blocks_expanded": report.get("insert_blocks_expanded"),
                "nested_inserts_expanded": report.get("nested_inserts_expanded"),
                "virtual_entities_extracted": report.get("virtual_entities_extracted"),
            },
        })

        # 3. block_expansion_report.json
        paths["block_expansion_report"] = _save(self._out, "block_expansion_report.json", {
            "generated": ts,
            "phase": "R.2A.2",
            "model_version": "7.5.3",
            **report,
            "item_count_before_expansion_estimate": 704,
            "item_count_after_expansion": len(inventory),
            "block_entities_added": sum(
                1 for r in inventory if r.source in ("BLOCK", "NESTED_BLOCK")
            ),
        })

        # 4. entity_coordinate_validation.json
        fy550_rec = next(
            (r for r in inventory if "LD FOR FY-550" in r.text.upper()), None
        )
        paths["entity_coordinate_validation"] = _save(
            self._out, "entity_coordinate_validation.json", {
                "generated": ts,
                "fy550_header": {
                    "found": fy550_rec is not None,
                    "world_x": fy550_rec.x if fy550_rec else None,
                    "world_y": fy550_rec.y if fy550_rec else None,
                    "expected_x_approx": 1587.35,
                    "expected_y_approx": 774.20,
                    "coordinate_match": (
                        fy550_rec is not None
                        and abs(fy550_rec.x - 1587.35) < 5
                        and abs(fy550_rec.y - 774.20) < 5
                    ),
                    "source": fy550_rec.source if fy550_rec else None,
                    "parent_block": fy550_rec.parent_block if fy550_rec else None,
                },
                "coordinate_transform": "ezdxf virtual_entities() world coordinates",
            },
        )

        # 5. development_length_inventory.json
        dl_table: Dict[str, Any] = {}
        for e in dl_entries:
            dl_table.setdefault(e.steel_grade, {}).setdefault(
                f"dia_{e.diameter_mm}", {}
            )[e.concrete_grade] = {
                "length_mm": e.length_mm,
                "source": e.source,
            }

        paths["development_length_inventory"] = _save(
            self._out, "development_length_inventory.json", {
                "generated": ts,
                "total_entries": len(dl_entries),
                "steel_grades": sorted({e.steel_grade for e in dl_entries}),
                "dxf_parsed_grades": dl_audit.get("tables_parsed_from_dxf", []),
                "is456_computed_grades": dl_audit.get("tables_computed_is456", []),
                "fe550_in_dxf": dl_audit.get("fe550_in_dxf", False),
                "development_length_table": dl_table,
                "warnings": dl_warnings,
            },
        )

        # 6-8. Engineering context outputs (regenerated)
        paths["engineering_context"] = _save(self._out, "engineering_context.json", {
            "generated": ts,
            "model_version": "7.5.3",
            "phase": "R.2A.2",
            **ctx.to_dict(),
        })

        paths["engineering_context_statistics"] = _save(
            self._out, "engineering_context_statistics.json", {
                "generated": ts,
                "parse_confidence": ctx.parse_confidence,
                "development_length_table_entries": len(ctx.development_length_table),
                "steel_grades": list(ctx.steel_grades),
                "cover_rules": len(ctx.cover_rules),
                "hook_rules": len(ctx.hook_rules),
                "lap_rules": len(ctx.lap_rules),
                "dl_by_grade": {
                    sg: sum(1 for k in ctx.development_length_table if k[0] == sg)
                    for sg in sorted({k[0] for k in ctx.development_length_table})
                },
            },
        )

        v_passed = sum(1 for r in validation_results if r.passed)
        paths["engineering_context_validation"] = _save(
            self._out, "engineering_context_validation.json", {
                "generated": ts,
                "phase": "R.2A.2",
                "model_version": "7.5.3",
                "validation_score": f"{v_passed}/{len(validation_results)}",
                "all_pass": v_passed == len(validation_results),
                "rules": [r.to_dict() for r in validation_results],
                "loader_summary": loader.summary(),
            },
        )

        return paths
