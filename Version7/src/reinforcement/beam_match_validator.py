"""Validate Phase G.3 beam matching engine."""

from __future__ import annotations

from typing import Any, List

from src.project.drawing_set_state_machine import MATCHING_COMPLETED
from src.reinforcement.engineering_reinforcement_context import ownership_resolver_applied
from src.reinforcement.beam_match import (
    EXECUTION_STATUS_EXECUTED,
    MATCHING_PROGRESS_COMPLETE,
    PREFIX_BEAM_MATCH,
    decision_eligible_for_match,
)
from src.reinforcement.detail_identity import (
    MATCHING_STATE_MATCH_COMPLETED,
    MATCHING_STATUS_MATCHED,
)
from src.reinforcement.match_decision_quality import DecisionQualityStatus


class BeamMatchValidator:
    """Verify committed beam matches and downstream state updates."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        drawing_models = model.get("reinforcement_drawing_models", [])
        beam_matches = model.get("beam_matches", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_engineering_ready_produces_match(model, drawing_models))
        checks.append(self._check_one_match_per_identity(drawing_models, beam_matches))
        checks.append(self._check_match_references_identity(beam_matches))
        checks.append(self._check_match_references_decision(beam_matches))
        checks.append(self._check_match_references_context(beam_matches, model))
        checks.append(self._check_beam_context_updated(model))
        checks.append(self._check_detail_identity_updated(drawing_models))
        checks.append(self._check_drawing_set_updated(model))
        checks.append(self._check_workspace_updated(model))
        checks.append(self._check_registry_complete(model, beam_matches))
        checks.append(self._check_graph_complete(model))
        checks.append(self._check_no_duplicate_matches(beam_matches))
        checks.append(self._check_no_fabricated_matches(model, drawing_models, beam_matches))
        checks.append(self._check_execution_status_updated(drawing_models))
        checks.append(self._check_beam_indices_consistent(model, beam_matches))
        checks.append(self._check_namespace_ids_valid(beam_matches))
        checks.append(self._check_backward_compatibility(drawing_models))
        checks.append(self._check_no_ownership(model))
        checks.append(self._check_no_parsing(model))
        checks.append(self._check_no_engineering_objects(model))
        checks.append(self._check_no_quantities(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.3",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "beam_match_count": len(beam_matches),
            },
        }

    def _eligible_decisions(self, drawing_models: list) -> list[dict[str, Any]]:
        eligible = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                if decision_eligible_for_match(decision):
                    eligible.append(decision)
        return eligible

    def _check_engineering_ready_produces_match(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        eligible = self._eligible_decisions(drawing_models)
        matches = model.get("beam_matches", [])
        if not eligible:
            return {
                "name": "ENGINEERING_READY Decisions Produce BeamMatch",
                "status": "FAIL",
                "eligible": 0,
                "matches": len(matches),
            }
        missing = []
        match_by_decision = {m.get("match_decision_id"): m for m in matches}
        for decision in eligible:
            did = decision.get("decision_id")
            if did not in match_by_decision:
                missing.append(did)
        return {
            "name": "ENGINEERING_READY Decisions Produce BeamMatch",
            "status": "PASS" if not missing and len(matches) == len(eligible) else "FAIL",
            "eligible": len(eligible),
            "matches": len(matches),
            "missing": missing,
        }

    def _check_one_match_per_identity(
        self,
        drawing_models: list,
        beam_matches: list,
    ) -> dict[str, Any]:
        identity_ids = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if ident.get("beam_match_id"):
                    identity_ids.append(ident.get("detail_identity_id"))
        duplicates = sorted({i for i in identity_ids if identity_ids.count(i) > 1})
        return {
            "name": "One BeamMatch Per DetailIdentity",
            "status": "PASS"
            if len(beam_matches) == len(identity_ids) and not duplicates
            else "FAIL",
            "identity_count": len(identity_ids),
            "match_count": len(beam_matches),
            "duplicates": duplicates,
        }

    def _check_match_references_identity(self, beam_matches: list) -> dict[str, Any]:
        invalid = [m.get("beam_match_id") for m in beam_matches if not m.get("detail_identity_id")]
        return {
            "name": "BeamMatch References DetailIdentity",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_match_references_decision(self, beam_matches: list) -> dict[str, Any]:
        invalid = [m.get("beam_match_id") for m in beam_matches if not m.get("match_decision_id")]
        return {
            "name": "BeamMatch References MatchDecision",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_match_references_context(
        self,
        beam_matches: list,
        model: dict[str, Any],
    ) -> dict[str, Any]:
        context_ids = {ctx.get("context_id") for ctx in model.get("beam_engineering_contexts", [])}
        invalid = [
            m.get("beam_match_id")
            for m in beam_matches
            if m.get("beam_context_id") not in context_ids
        ]
        return {
            "name": "BeamMatch References BeamContext",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_beam_context_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        if ownership_resolver_applied(model):
            return {
                "name": "BeamContext Updated",
                "status": "PASS",
                "skipped": "ownership_resolver_applied",
            }
        matches = model.get("beam_matches", [])
        match_by_context = {m.get("beam_context_id"): m for m in matches}
        invalid = []
        for ctx in model.get("beam_engineering_contexts", []):
            cid = ctx.get("context_id")
            match = match_by_context.get(cid)
            if not match:
                continue
            if ctx.get("beam_match_id") != match.get("beam_match_id"):
                invalid.append(cid)
            if ctx.get("reinforcement_context_id") != match.get("detail_context_id"):
                invalid.append(cid)
            if ctx.get("reinforcement_matching_status") != MATCHING_STATUS_MATCHED:
                invalid.append(cid)
        return {
            "name": "BeamContext Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_detail_identity_updated(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if not ident.get("beam_match_id"):
                    continue
                if ident.get("matching_status") != MATCHING_STATUS_MATCHED:
                    invalid.append(ident.get("detail_identity_id"))
                if ident.get("matching_state") != MATCHING_STATE_MATCH_COMPLETED:
                    invalid.append(ident.get("detail_identity_id"))
        return {
            "name": "DetailIdentity Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_drawing_set_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for ds in model.get("drawing_sets", []):
            if ds.get("matching_state") != MATCHING_COMPLETED:
                invalid.append(ds.get("drawing_set_id"))
            if not ds.get("beam_match_registry"):
                invalid.append(ds.get("drawing_set_id"))
            if ds.get("matching_progress") != MATCHING_PROGRESS_COMPLETE:
                invalid.append(ds.get("drawing_set_id"))
        return {
            "name": "DrawingSet Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_workspace_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        project = model.get("project_workspace", {})
        if not project.get("beam_match_registry"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "registry"}
        if not project.get("matching_summary"):
            return {"name": "Workspace Updated", "status": "FAIL", "reason": "summary"}
        return {"name": "Workspace Updated", "status": "PASS"}

    def _check_registry_complete(
        self,
        model: dict[str, Any],
        beam_matches: list,
    ) -> dict[str, Any]:
        registry = model.get("beam_match_registry", {})
        expected = len(beam_matches)
        actual = registry.get("match_count", 0)
        return {
            "name": "Registry Complete",
            "status": "PASS" if expected > 0 and actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
        }

    def _check_graph_complete(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("beam_match_graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        has_matched_to = any(e.get("relationship") == "MATCHED_TO" for e in edges)
        has_references = any(e.get("relationship") == "REFERENCES" for e in edges)
        has_targets = any(e.get("relationship") == "TARGETS" for e in edges)
        has_reinforcement = any(
            e.get("relationship") == "HAS_REINFORCEMENT_MATCH" for e in edges
        )
        ok = (
            len(nodes) > 0
            and has_matched_to
            and has_references
            and has_targets
            and has_reinforcement
        )
        return {
            "name": "Graph Complete",
            "status": "PASS" if ok else "FAIL",
            "node_count": len(nodes),
            "has_matched_to": has_matched_to,
            "has_references": has_references,
            "has_targets": has_targets,
            "has_reinforcement_match": has_reinforcement,
        }

    def _check_no_duplicate_matches(self, beam_matches: list) -> dict[str, Any]:
        ids = [m.get("beam_match_id") for m in beam_matches]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        return {
            "name": "No Duplicate BeamMatches",
            "status": "PASS" if beam_matches and not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _check_no_fabricated_matches(
        self,
        model: dict[str, Any],
        drawing_models: list,
        beam_matches: list,
    ) -> dict[str, Any]:
        eligible_ids = {d.get("decision_id") for d in self._eligible_decisions(drawing_models)}
        fabricated = [
            m.get("beam_match_id")
            for m in beam_matches
            if m.get("match_decision_id") not in eligible_ids
        ]
        return {
            "name": "No Fabricated Matches",
            "status": "PASS" if not fabricated else "FAIL",
            "fabricated": fabricated,
        }

    def _check_execution_status_updated(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                if decision_eligible_for_match(decision):
                    if decision.get("execution_status") != EXECUTION_STATUS_EXECUTED:
                        invalid.append(decision.get("decision_id"))
                elif "execution_status" not in decision:
                    invalid.append(decision.get("decision_id"))
        return {
            "name": "execution_status Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_beam_indices_consistent(
        self,
        model: dict[str, Any],
        beam_matches: list,
    ) -> dict[str, Any]:
        index_marks: set[str] = set()
        for idx in model.get("beam_indices", []):
            index_marks.update(str(m).upper() for m in idx.get("marks", []))
            index_marks.update(str(m).upper() for m in idx.get("index", {}).keys())
        if not index_marks:
            return {"name": "Beam Indices Consistent", "status": "PASS", "skipped": "no_index"}
        invalid = [
            m.get("beam_match_id")
            for m in beam_matches
            if str(m.get("beam_mark", "")).upper() not in index_marks
        ]
        return {
            "name": "Beam Indices Consistent",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_namespace_ids_valid(self, beam_matches: list) -> dict[str, Any]:
        invalid = [
            m.get("beam_match_id")
            for m in beam_matches
            if not str(m.get("beam_match_id", "")).startswith(f"{PREFIX_BEAM_MATCH}::")
        ]
        return {
            "name": "Namespace IDs Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_backward_compatibility(self, drawing_models: list) -> dict[str, Any]:
        required_decision = (
            "decision_id",
            "decision_status",
            "decision_reason",
            "confidence",
            "requires_manual_review",
        )
        missing = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                for field in required_decision:
                    if field not in decision:
                        missing.append(decision.get("decision_id"))
        return {
            "name": "Backward Compatibility Maintained",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    def _check_no_ownership(self, model: dict[str, Any]) -> dict[str, Any]:
        for dm in model.get("reinforcement_drawing_models", []):
            for rel in dm.get("match_relationships", []):
                if "OWN" in str(rel.get("relationship", "")).upper():
                    return {"name": "No Ownership", "status": "FAIL"}
        return {"name": "No Ownership", "status": "PASS"}

    def _check_no_parsing(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("parsed_bars", "bar_schedule") if k in model]
        return {
            "name": "No Reinforcement Parsing",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_engineering_objects(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("engineering_objects",) if k in model]
        return {
            "name": "No Engineering Objects",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_quantities(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("quantities", "steel_weight", "boq") if k in model]
        return {
            "name": "No Quantity Computation",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }
