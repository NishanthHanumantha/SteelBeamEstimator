"""Map Engineering Decisions to production calculation inputs."""

from __future__ import annotations

from typing import Any, Dict, List, Set


class DecisionMapper:
    """Map decisions to existing production calculation input sets."""

    def map_all(
        self,
        decisions: List[dict[str, Any]],
        execution_contexts: List[dict[str, Any]],
        selection: List[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        context_by_id = {
            str(item.get("decision_id")): item for item in execution_contexts if item.get("decision_id")
        }
        selection_by_id = {
            str(item.get("decision_id")): item for item in selection if item.get("decision_id")
        }

        mappings: List[dict[str, Any]] = []
        executable_intent_ids: Set[str] = set()
        suppressed_intent_ids: Set[str] = set()
        executable_bar_ids: Set[str] = set()
        executable_beam_ids: Set[str] = set()

        for decision in decisions:
            decision_id = str(decision.get("decision_id") or "")
            context = context_by_id.get(decision_id) or {}
            selected = selection_by_id.get(decision_id) or {}
            primary = decision.get("primary_intent") or {}
            supporting = list(decision.get("supporting_intents") or [])
            suppressed = list(decision.get("suppressed_intents") or [])

            active_intent_ids = []
            if primary.get("intent_id"):
                active_intent_ids.append(str(primary.get("intent_id")))
            active_intent_ids.extend(
                str(item.get("intent_id")) for item in supporting if item.get("intent_id")
            )
            suppressed_ids = [
                str(item.get("intent_id")) for item in suppressed if item.get("intent_id")
            ]

            if selected.get("executable"):
                executable_intent_ids.update(active_intent_ids)
                suppressed_intent_ids.update(suppressed_ids)
                if decision.get("source_bar_id"):
                    executable_bar_ids.add(str(decision.get("source_bar_id")))
                if decision.get("beam_id"):
                    executable_beam_ids.add(str(decision.get("beam_id")))

            mappings.append(
                {
                    "decision_id": decision_id,
                    "decision_key": decision.get("decision_key"),
                    "executable": bool(selected.get("executable")),
                    "calculation_input": {
                        "beam_id": decision.get("beam_id"),
                        "source_bar_id": decision.get("source_bar_id"),
                        "engineering_object_id": decision.get("engineering_object_id"),
                        "calculation_context_id": (context.get("calculation_context") or {}).get(
                            "context_id"
                        ),
                        "specification_id": (context.get("specification") or {}).get("specification_id"),
                        "active_intent_ids": active_intent_ids,
                        "suppressed_intent_ids": suppressed_ids,
                        "decision_category": decision.get("decision_category"),
                        "resolution_rule": decision.get("resolution_rule"),
                    },
                    "production_targets": {
                        "calculation": "phase_i/i_2_2_calculation_result_framework",
                        "cut_length": "phase_i/i_6_cut_length",
                        "steel": "phase_i/i_11_steel_weight",
                        "bbs": "phase_i/i_10_bbs",
                        "beam_schedule": "phase_i/i_15_beam_schedule",
                        "excel": "phase_i/i_17_excel_export",
                    },
                }
            )

        # Execution intents exclude suppressed.
        execution_intent_ids = sorted(executable_intent_ids - suppressed_intent_ids)

        return {
            "mapping_count": len(mappings),
            "mappings": sorted(mappings, key=lambda item: str(item.get("decision_id") or "")),
            "execution_intent_ids": execution_intent_ids,
            "suppressed_intent_ids": sorted(suppressed_intent_ids),
            "executable_bar_ids": sorted(executable_bar_ids),
            "executable_beam_ids": sorted(executable_beam_ids),
            "executable_decision_count": sum(1 for item in mappings if item.get("executable")),
            "existing_calculation_engine": "src.engineering_calculation_integration.IntegrationEngine",
            "duplicated_calculations": False,
        }
