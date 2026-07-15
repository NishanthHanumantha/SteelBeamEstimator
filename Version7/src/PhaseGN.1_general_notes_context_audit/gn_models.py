"""
Data models for Phase GN.1 audit artefacts.
All fields are read-only audit records; no production logic.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Classification enumerations (as string constants for JSON portability)
# ---------------------------------------------------------------------------
class SourceClass:
    DYNAMIC      = "Dynamic"        # value read live from DXF at runtime
    GENERAL_NOTES = "General_Notes" # present in GN DXF but not yet consumed
    HARDCODED    = "Hardcoded"      # literal constant in source code
    CONFIG       = "Config"         # from a config file / YAML
    FALLBACK     = "Fallback"       # default used when primary extraction fails
    DEFAULT      = "Default"        # IS-standard default applied by design


class GapSeverity:
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class GapType:
    EXTRACTED_UNUSED    = "Extracted_But_Unused"
    MISSING_EXTRACTION  = "Missing_Extraction"
    WRONG_SOURCE        = "Wrong_Source"
    FALLBACK_USED       = "Fallback_Used"
    HARDCODED_ASSUMPTION = "Hardcoded_Assumption"
    POTENTIAL_IMPACT    = "Potential_Accuracy_Impact"


# ---------------------------------------------------------------------------
# Core audit records
# ---------------------------------------------------------------------------
@dataclass
class GNDiscoveryRecord:
    project_id: str
    gn_dxf_path: str
    sheet_name: str
    discovered_dynamically: bool
    entity_counts: Dict[str, int] = field(default_factory=dict)
    total_text_entities: int = 0
    layers_present: List[str] = field(default_factory=list)
    benchmark_set_1_dependency: bool = False
    version6_dependency: bool = False
    hardcoded_path_used: bool = False
    discovery_method: str = ""
    notes: List[str] = field(default_factory=list)


@dataclass
class ExtractedParameter:
    parameter_name: str
    source_drawing: str
    source_layer: str
    source_text: str
    parsed_value: Any
    classification: str          # SourceClass value
    consumers: List[str] = field(default_factory=list)
    consumed_by_steel_weight: bool = False
    consumed_by_bbs: bool = False
    consumed_by_excel: bool = False
    gap_type: Optional[str] = None
    notes: str = ""


@dataclass
class TraceabilityNode:
    parameter_name: str
    extracted_value: Any
    pipeline_value: Any
    match: bool
    source_drawing: str
    consumers: List[str] = field(default_factory=list)
    dependency_chain: List[str] = field(default_factory=list)
    gap_severity: Optional[str] = None


@dataclass
class FramingFieldAudit:
    field_name: str
    source_drawing: str
    source_entity: str
    consumer_modules: List[str] = field(default_factory=list)
    used: bool = False
    pipeline_value_example: Any = None
    classification: str = SourceClass.DYNAMIC
    notes: str = ""


@dataclass
class RebarFieldAudit:
    field_name: str
    source_drawing: str
    source_entity: str
    consumer_modules: List[str] = field(default_factory=list)
    used: bool = False
    example_annotation: str = ""
    classification: str = SourceClass.DYNAMIC
    notes: str = ""


@dataclass
class HardcodedDefault:
    file_path: str
    line_number: int
    symbol: str
    literal_value: str
    engineering_meaning: str
    classification: str
    gn_equivalent: Optional[str] = None
    severity: str = GapSeverity.MEDIUM
    notes: str = ""


@dataclass
class ConsumptionRecord:
    parameter_name: str
    gn_value: Any
    steel_weight_value: Any
    bbs_value: Any
    excel_value: Any
    all_match: bool = False
    steel_match: bool = False
    bbs_match: bool = False
    excel_match: bool = False
    notes: str = ""


@dataclass
class EngineeringGap:
    gap_id: str
    parameter_name: str
    gap_type: str
    severity: str
    description: str
    impact: str
    recommendation: str
    affected_modules: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    rule_id: str
    rule_name: str
    passed: bool
    evidence: str
    detail: str = ""


@dataclass
class GN1AuditReport:
    phase: str = "GN.1"
    model_version: str = "7.4.0"
    timestamp: str = ""
    project_id: str = ""
    gn_discovery: Optional[Dict] = None
    extracted_parameters: List[Dict] = field(default_factory=list)
    traceability_graph: List[Dict] = field(default_factory=list)
    framing_audit: List[Dict] = field(default_factory=list)
    reinforcement_audit: List[Dict] = field(default_factory=list)
    hardcoded_defaults: List[Dict] = field(default_factory=list)
    consumption_matrix: List[Dict] = field(default_factory=list)
    engineering_gaps: List[Dict] = field(default_factory=list)
    generalization_check: Dict = field(default_factory=dict)
    validation_results: List[Dict] = field(default_factory=list)
    validation_score: str = ""
    overall_verdict: str = ""
    summary: Dict = field(default_factory=dict)
