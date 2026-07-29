"""Validate production pipeline dependency chain."""
from __future__ import annotations
from typing import Any, Dict

from .pipeline_data_loader import PipelineDataLoader
from .validation_models import RuleResult


class PipelineDependencyValidator:

    LEGACY_MARKERS = (
        "REFERENCE_CLASSIFICATION",
        "reference_classification",
        "is_benchmark_beam",
        "is_reference_anchored",
    )

    def validate(
        self,
        loader: PipelineDataLoader,
        coverage: Dict[str, Any],
        reinforcement_source: str,
        production_models_path: str,
    ) -> Dict[str, RuleResult]:
        prod_models = loader.production_models()
        prod_source = loader.production_source()

        eng_beam_ids = loader.engineering_beam_ids()
        prod_beam_ids = {m.get("beam_id") for m in prod_models if m.get("beam_id")}

        steel_origin_ok = prod_beam_ids <= eng_beam_ids or len(prod_beam_ids) == 0
        if prod_models and not steel_origin_ok:
            extra = prod_beam_ids - eng_beam_ids
            steel_detail = f"beams_not_from_engineering_model={len(extra)}"
            steel_pass = False
        else:
            steel_detail = f"production_beams={len(prod_beam_ids)}"
            steel_pass = True

        legacy_in_source = "REFERENCE_CLASSIFICATION" in reinforcement_source
        legacy_in_prod = any(
            marker.lower() in prod_source.lower()
            for marker in ("reference_classification", "l.2 benchmark")
        )
        legacy_in_path = "PhaseL.2" in production_models_path

        benchmark_filter = any(
            m.get("is_benchmark_beam") for m in prod_models
        )

        trace_sources = set()
        for m in prod_models:
            trace = m.get("traceability", {})
            trace_sources.add(trace.get("source_phase", trace.get("source", "")))

        engineering_only = (
            not legacy_in_source
            and not legacy_in_path
            and (
                "EngineeringBarModel" in reinforcement_source
                or "R.1.3" in reinforcement_source
            )
        )

        return {
            "RULE_12": RuleResult(
                "RULE_12",
                "PASS" if steel_pass else "ERROR",
                steel_detail,
                steel_pass,
            ),
            "RULE_13": RuleResult(
                "RULE_13",
                "PASS" if engineering_only and not legacy_in_source else "ERROR",
                f"source={reinforcement_source}, legacy_path={legacy_in_path}",
                engineering_only and not legacy_in_source,
            ),
            "RULE_14": RuleResult(
                "RULE_14",
                "PASS" if not benchmark_filter else "ERROR",
                f"benchmark_filtered={benchmark_filter}",
                not benchmark_filter,
            ),
            "_trace_sources": sorted(trace_sources),
        }
