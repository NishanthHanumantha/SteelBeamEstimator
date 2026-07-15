"""
Engineering Context Builder — Part 3 of Phase GN.1 audit.

Assembles the engineering context from extracted GN parameters and maps each
parameter to its downstream consumers in the V7 production pipeline.
Produces the full traceability graph.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from .gn_models import (
    ExtractedParameter, TraceabilityNode, SourceClass,
    ConsumptionRecord, GapSeverity,
)

# ---------------------------------------------------------------------------
# Known pipeline modules that consume engineering parameters
# ---------------------------------------------------------------------------
_PIPELINE_MAP: Dict[str, Dict[str, Any]] = {
    "steel_grade": {
        "pipeline_value": "Fe415",
        "pipeline_source": "HARDCODED in excel_structure_builder.py:105",
        "consumers": ["SteelWeightCompletion", "EstimatorExcelGenerator"],
        "steel_weight_uses": True,
        "bbs_uses": False,
        "excel_uses": True,
    },
    "concrete_grade_table": {
        "pipeline_value": "M25 (default in development_length_service.py)",
        "pipeline_source": "HARDCODED fallback 'M30' in development_length_service.py:23",
        "consumers": ["DevelopmentLengthService"],
        "steel_weight_uses": True,
        "bbs_uses": False,
        "excel_uses": False,
    },
    "development_length_table_header": {
        "pipeline_value": "40d (constant _DEVELOPMENT_LENGTH_FACTOR=40)",
        "pipeline_source": "HARDCODED in steel_weight_completion.py:33",
        "consumers": ["SteelWeightCompletion", "StirrupWeightEngine"],
        "steel_weight_uses": True,
        "bbs_uses": True,
        "excel_uses": True,
    },
    "development_length_rule": {
        "pipeline_value": "40d",
        "pipeline_source": "HARDCODED in steel_weight_completion.py:33",
        "consumers": ["SteelWeightCompletion"],
        "steel_weight_uses": True,
        "bbs_uses": True,
        "excel_uses": True,
    },
    "development_length_multiplier": {
        "pipeline_value": "40",
        "pipeline_source": "HARDCODED in steel_weight_completion.py:33",
        "consumers": ["SteelWeightCompletion"],
        "steel_weight_uses": True,
        "bbs_uses": True,
        "excel_uses": False,
    },
    "concrete_cover_mm": {
        "pipeline_value": 40.0,
        "pipeline_source": "HARDCODED _COVER_MM=40.0 in steel_weight_completion.py:34 and stirrup_weight_engine.py:19",
        "consumers": ["SteelWeightCompletion", "StirrupWeightEngine"],
        "steel_weight_uses": True,
        "bbs_uses": True,
        "excel_uses": True,
    },
    "spacer_rule": {
        "pipeline_value": "NOT USED",
        "pipeline_source": "No spacer rule consumer found in V7 production pipeline",
        "consumers": [],
        "steel_weight_uses": False,
        "bbs_uses": False,
        "excel_uses": False,
    },
    "hook_bend_rule": {
        "pipeline_value": "10d (_HOOK_MULTIPLE=10)",
        "pipeline_source": "HARDCODED in steel_weight_completion.py:35 and stirrup_weight_engine.py:20",
        "consumers": ["SteelWeightCompletion", "StirrupWeightEngine"],
        "steel_weight_uses": True,
        "bbs_uses": True,
        "excel_uses": False,
    },
    "hook_length_xdb": {
        "pipeline_value": "10d (_HOOK_MULTIPLE=10) — GN says 4xdb standard 90 bend",
        "pipeline_source": "HARDCODED in steel_weight_completion.py:35",
        "consumers": ["SteelWeightCompletion", "StirrupWeightEngine"],
        "steel_weight_uses": True,
        "bbs_uses": True,
        "excel_uses": False,
    },
    "lap_length_table_ref": {
        "pipeline_value": "NOT CONSUMED",
        "pipeline_source": "No lap table consumer in V7 production pipeline",
        "consumers": [],
        "steel_weight_uses": False,
        "bbs_uses": False,
        "excel_uses": False,
    },
    "lap_length_minimum_mm": {
        "pipeline_value": "NOT CONSUMED",
        "pipeline_source": "300mm minimum lap not verified in pipeline",
        "consumers": [],
        "steel_weight_uses": False,
        "bbs_uses": False,
        "excel_uses": False,
    },
    "IS456_reference": {
        "pipeline_value": "IS 456:2000",
        "pipeline_source": "Referenced in comments and Excel notes (excel_structure_builder.py:113)",
        "consumers": ["EstimatorExcelGenerator"],
        "steel_weight_uses": False,
        "bbs_uses": False,
        "excel_uses": True,
    },
    "IS2502_reference": {
        "pipeline_value": "NOT EXPLICITLY CONSUMED",
        "pipeline_source": "IS 2502 not referenced in V7 production pipeline",
        "consumers": [],
        "steel_weight_uses": False,
        "bbs_uses": False,
        "excel_uses": False,
    },
}


class EngineeringContextBuilder:
    """
    Reads extracted GN parameters and produces the traceability graph and
    consumption matrix, comparing GN-extracted values against what the
    pipeline actually uses.
    """

    def build_traceability(
        self, extracted: List[ExtractedParameter]
    ) -> List[TraceabilityNode]:
        nodes: List[TraceabilityNode] = []
        for param in extracted:
            mapping = _PIPELINE_MAP.get(param.parameter_name, {})
            pipeline_val = mapping.get("pipeline_value", "UNKNOWN")
            consumers = mapping.get("consumers", [])

            # Build dependency chain
            chain = ["GN_DXF"]
            if param.parsed_value is not None:
                chain.append("GNExtractor")
                chain.append("EngineeringContext")
                chain.extend(consumers)
            else:
                chain.append("NOT_CONSUMED")

            match = self._values_match(param.parsed_value, pipeline_val)
            severity = None
            if not match and param.parsed_value is not None:
                severity = GapSeverity.HIGH if "HARDCODED" in mapping.get("pipeline_source", "") else GapSeverity.MEDIUM

            node = TraceabilityNode(
                parameter_name=param.parameter_name,
                extracted_value=param.parsed_value,
                pipeline_value=pipeline_val,
                match=match,
                source_drawing=param.source_drawing,
                consumers=consumers,
                dependency_chain=chain,
                gap_severity=severity,
            )
            # Update param consumption flags
            param.consumers = consumers
            param.consumed_by_steel_weight = mapping.get("steel_weight_uses", False)
            param.consumed_by_bbs = mapping.get("bbs_uses", False)
            param.consumed_by_excel = mapping.get("excel_uses", False)
            nodes.append(node)
        return nodes

    def build_consumption_matrix(
        self, extracted: List[ExtractedParameter]
    ) -> List[ConsumptionRecord]:
        records: List[ConsumptionRecord] = []
        for param in extracted:
            mapping = _PIPELINE_MAP.get(param.parameter_name, {})
            pipeline_val = mapping.get("pipeline_value", "NOT_USED")

            sw_val  = pipeline_val if mapping.get("steel_weight_uses") else "NOT_USED"
            bbs_val = pipeline_val if mapping.get("bbs_uses") else "NOT_USED"
            xls_val = pipeline_val if mapping.get("excel_uses") else "NOT_USED"

            sw_match  = mapping.get("steel_weight_uses", False)
            bbs_match = mapping.get("bbs_uses", False)
            xls_match = mapping.get("excel_uses", False)
            all_match = sw_match and bbs_match and xls_match

            records.append(ConsumptionRecord(
                parameter_name=param.parameter_name,
                gn_value=param.parsed_value,
                steel_weight_value=sw_val,
                bbs_value=bbs_val,
                excel_value=xls_val,
                all_match=all_match,
                steel_match=sw_match,
                bbs_match=bbs_match,
                excel_match=xls_match,
                notes=mapping.get("pipeline_source", ""),
            ))
        return records

    @staticmethod
    def _values_match(extracted: Any, pipeline: Any) -> bool:
        if extracted is None:
            return False
        ex_str = str(extracted).lower()
        pi_str = str(pipeline).lower()
        return ex_str in pi_str or pi_str in ex_str
