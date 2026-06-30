"""Validate Phase G.2.6 match decision layer."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.beam_match import beam_matching_applied
from src.reinforcement.detail_identity import MATCHING_STATUS_NOT_MATCHED
from src.reinforcement.match_decision import (
    ALLOWED_DECISION_REASONS,
    ALLOWED_DECISION_STATUSES,
    DECISION_STATUS_PENDING_VALIDATION,
    DECISION_STATUS_VALIDATED,
    MANUAL_REVIEW_CONFIDENCE_THRESHOLD,
    requires_manual_review,
)


class MatchDecisionValidator:
    """Verify match decisions without beam matching or ownership."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        drawing_models = model.get("reinforcement_drawing_models", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_decisions_created(drawing_models))
        checks.append(self._check_one_decision_per_identity(drawing_models))
        checks.append(self._check_candidates_referenced(drawing_models))
        checks.append(self._check_candidate_count_correct(drawing_models))
        checks.append(self._check_recommended_exists(drawing_models))
        checks.append(self._check_highest_ranked_selected(model, drawing_models))
        checks.append(self._check_decision_reason_valid(drawing_models))
        checks.append(self._check_decision_status_valid(drawing_models))
        checks.append(self._check_manual_review_threshold(drawing_models))
        checks.append(self._check_no_ownership(model, drawing_models))
        checks.append(self._check_no_beam_context_modification(model))
        checks.append(self._check_no_parsing(model))
        checks.append(self._check_no_engineering_objects(model))
        checks.append(self._check_no_quantities(model))
        checks.append(self._check_registry_complete(model, drawing_models))
        checks.append(self._check_graph_relationships(model))
        checks.append(self._check_drawing_set_updated(model))
        checks.append(self._check_workspace_updated(model))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.2.6",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "decision_count": sum(
                    dm.get("match_decision_count", 0) for dm in drawing_models
                ),
            },
        }

    def _check_decisions_created(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("match_decision_count", 0) for dm in drawing_models)
        return {
            "name": "Match Decisions Created",
            "status": "PASS" if count > 0 else "FAIL",
            "count": count,
        }

    def _check_one_decision_per_identity(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        duplicates = []
        for dm in drawing_models:
            decision_by_identity: dict[str, str] = {}
            for ident in dm.get("detail_identities", []):
                iid = ident.get("detail_identity_id")
                did = ident.get("match_decision_id")
                if not did:
                    missing.append(iid)
                elif iid in decision_by_identity:
                    duplicates.append(iid)
                else:
                    decision_by_identity[iid] = did
            if len(dm.get("match_decisions", [])) != len(dm.get("detail_identities", [])):
                missing.append("count_mismatch")
        return {
            "name": "Every DetailIdentity Has Exactly One MatchDecision",
            "status": "PASS" if not missing and not duplicates else "FAIL",
            "missing": missing,
            "duplicates": duplicates,
        }

    def _check_candidates_referenced(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            candidate_ids = {
                c.get("candidate_id") for c in dm.get("beam_match_candidates", [])
            }
            for decision in dm.get("match_decisions", []):
                for cid in decision.get("candidate_ids", []):
                    if cid not in candidate_ids:
                        invalid.append(decision.get("decision_id"))
        return {
            "name": "MatchDecision References Existing Candidates",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_candidate_count_correct(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                if decision.get("candidate_count") != len(decision.get("candidate_ids", [])):
                    invalid.append(decision.get("decision_id"))
        return {
            "name": "Candidate Count Correct",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_recommended_exists(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            candidate_ids = {
                c.get("candidate_id") for c in dm.get("beam_match_candidates", [])
            }
            for decision in dm.get("match_decisions", []):
                rec = decision.get("recommended_candidate_id")
                if rec and rec not in candidate_ids:
                    invalid.append(decision.get("decision_id"))
        return {
            "name": "Recommended Candidate Exists",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_highest_ranked_selected(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                best = ident.get("best_candidate_id")
                iid = ident.get("detail_identity_id")
                decision = next(
                    (d for d in dm.get("match_decisions", []) if d.get("detail_identity_id") == iid),
                    {},
                )
                if decision.get("recommended_candidate_id") != best:
                    invalid.append(iid)
        return {
            "name": "Highest Ranked Candidate Selected",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_decision_reason_valid(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                if decision.get("decision_reason") not in ALLOWED_DECISION_REASONS:
                    invalid.append(decision.get("decision_id"))
        return {
            "name": "Decision Reason Valid Enum",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_decision_status_valid(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        validated = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                status = decision.get("decision_status")
                if status not in ALLOWED_DECISION_STATUSES:
                    invalid.append(decision.get("decision_id"))
                if status == DECISION_STATUS_VALIDATED:
                    validated.append(decision.get("decision_id"))
        ok = not invalid and not validated
        return {
            "name": "Decision Status Valid",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
            "premature_validated": validated,
        }

    def _check_manual_review_threshold(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for decision in dm.get("match_decisions", []):
                conf = float(decision.get("confidence", 0.0))
                expected = requires_manual_review(conf)
                if decision.get("requires_manual_review") != expected:
                    invalid.append(decision.get("decision_id"))
        return {
            "name": "Manual Review Flag Consistent",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
            "threshold": MANUAL_REVIEW_CONFIDENCE_THRESHOLD,
        }

    def _check_no_ownership(self, model: dict[str, Any], drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for rel in dm.get("decision_relationships", []):
                if "OWN" in str(rel.get("relationship", "")).upper():
                    return {"name": "No Ownership", "status": "FAIL"}
            if beam_matching_applied(model):
                continue
            for ident in dm.get("detail_identities", []):
                if ident.get("matching_status") != MATCHING_STATUS_NOT_MATCHED:
                    return {"name": "No Ownership", "status": "FAIL"}
        return {"name": "No Ownership", "status": "PASS"}

    def _check_no_beam_context_modification(self, model: dict[str, Any]) -> dict[str, Any]:
        if beam_matching_applied(model):
            return {
                "name": "No BeamContext Modification",
                "status": "PASS",
                "skipped": "beam_matching_applied",
            }
        invalid = []
        for ctx in model.get("beam_engineering_contexts", []):
            if ctx.get("reinforcement_context_id") or ctx.get("detail_identity_id"):
                invalid.append(ctx.get("context_id"))
        return {
            "name": "No BeamContext Modification",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_parsing(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("parsed_bars", "bar_schedule") if k in model]
        return {
            "name": "No Parsing",
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
            "name": "No Quantities",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_registry_complete(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        registry = model.get("match_decision_registry", {})
        expected = sum(dm.get("match_decision_count", 0) for dm in drawing_models)
        actual = registry.get("decision_count", 0)
        return {
            "name": "Match Decision Registry Complete",
            "status": "PASS" if expected > 0 and actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
        }

    def _check_graph_relationships(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        decision_nodes = [
            n for n in graph.get("nodes", []) if n.get("type") == "MATCH_DECISION"
        ]
        has_decision_edge = any(
            e.get("relationship") == "HAS_MATCH_DECISION" for e in graph.get("edges", [])
        )
        has_recommends_edge = any(
            e.get("relationship") == "RECOMMENDS" for e in graph.get("edges", [])
        )
        ok = len(decision_nodes) > 0 and has_decision_edge and has_recommends_edge
        return {
            "name": "Graph Decision Relationships Valid",
            "status": "PASS" if ok else "FAIL",
            "decision_nodes": len(decision_nodes),
            "has_decision_edge": has_decision_edge,
            "has_recommends_edge": has_recommends_edge,
        }

    def _check_drawing_set_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for ds in model.get("drawing_sets", []):
            if not ds.get("match_decision_registry"):
                invalid.append(ds.get("drawing_set_id"))
            if ds.get("decision_progress") != "DECISIONS_READY":
                invalid.append(ds.get("drawing_set_id"))
        return {
            "name": "DrawingSet Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_workspace_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for ws in model.get("reinforcement_workspaces", []):
            if "match_decisions" not in ws:
                invalid.append(ws.get("workspace_id", "workspace"))
            if "decision_registry" not in ws:
                invalid.append(ws.get("workspace_id", "workspace"))
        return {
            "name": "Workspace Updated",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }
