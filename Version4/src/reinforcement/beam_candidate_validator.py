"""Validate Phase G.2.5 beam match candidate engine."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.beam_match_candidate import (
    CANDIDATE_STATUS_RANKED,
    MATCHING_STATE_CANDIDATES_READY,
)
from src.reinforcement.detail_identity import MATCHING_STATUS_NOT_MATCHED


class BeamCandidateValidator:
    """Verify candidate generation without final beam matching or ownership."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        drawing_models = model.get("reinforcement_drawing_models", [])
        checks: List[dict[str, Any]] = []
        checks.append(self._check_candidates_exist(drawing_models))
        checks.append(self._check_every_identity_has_candidates_field(drawing_models))
        checks.append(self._check_same_drawing_set(drawing_models))
        checks.append(self._check_same_floor(drawing_models, model))
        checks.append(self._check_beam_context_exists(model, drawing_models))
        checks.append(self._check_candidate_ids_unique(drawing_models))
        checks.append(self._check_scores_valid(drawing_models))
        checks.append(self._check_confidence_valid(drawing_models))
        checks.append(self._check_ranking_deterministic(model, drawing_models))
        checks.append(self._check_no_duplicate_best_candidate(drawing_models))
        checks.append(self._check_no_ownership(drawing_models))
        checks.append(self._check_no_matching(drawing_models))
        checks.append(self._check_no_parsing(drawing_models))
        checks.append(self._check_no_quantities(model))
        checks.append(self._check_no_beam_context_modification(model))
        checks.append(self._check_graph_relationships(model))
        checks.append(self._check_registry_complete(model, drawing_models))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.2.5",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "candidate_count": sum(
                    dm.get("beam_match_candidate_count", 0) for dm in drawing_models
                ),
            },
        }

    def _check_candidates_exist(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("beam_match_candidate_count", 0) for dm in drawing_models)
        return {
            "name": "Beam Match Candidates Created",
            "status": "PASS" if count > 0 else "FAIL",
            "count": count,
        }

    def _check_every_identity_has_candidates_field(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if "candidate_count" not in ident or "matching_state" not in ident:
                    missing.append(ident.get("detail_identity_id"))
        return {
            "name": "Every DetailIdentity Has Candidate Fields",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    def _check_same_drawing_set(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            ds_id = dm.get("drawing_set_id", "")
            for cand in dm.get("beam_match_candidates", []):
                if cand.get("drawing_set_id") != ds_id:
                    invalid.append(cand.get("candidate_id"))
        return {
            "name": "All Candidates Same Drawing Set",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_same_floor(self, drawing_models: list, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            floor_id = dm.get("floor_id", "")
            for cand in dm.get("beam_match_candidates", []):
                if cand.get("floor_id") != floor_id:
                    invalid.append(cand.get("candidate_id"))
        return {
            "name": "All Candidates Same Floor",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_beam_context_exists(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        context_ids = {
            str(c.get("context_id", ""))
            for c in model.get("beam_engineering_contexts", [])
        }
        missing = []
        for dm in drawing_models:
            for cand in dm.get("beam_match_candidates", []):
                cid = str(cand.get("beam_context_id", ""))
                if cid and cid not in context_ids:
                    missing.append(cand.get("candidate_id"))
        return {
            "name": "BeamContext Exists For Candidates",
            "status": "PASS" if not missing else "FAIL",
            "missing": missing,
        }

    def _check_candidate_ids_unique(self, drawing_models: list) -> dict[str, Any]:
        ids: list[str] = []
        for dm in drawing_models:
            for cand in dm.get("beam_match_candidates", []):
                ids.append(str(cand.get("candidate_id", "")))
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        return {
            "name": "Candidate IDs Unique",
            "status": "PASS" if ids and not duplicates else "FAIL",
            "duplicates": duplicates,
        }

    def _check_scores_valid(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for cand in dm.get("beam_match_candidates", []):
                score = cand.get("score")
                if not isinstance(score, (int, float)) or not (0 < float(score) <= 1.0):
                    invalid.append(cand.get("candidate_id"))
        return {
            "name": "Scores Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_confidence_valid(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for cand in dm.get("beam_match_candidates", []):
                conf = cand.get("confidence")
                if not isinstance(conf, (int, float)) or not (0 < float(conf) <= 1.0):
                    invalid.append(cand.get("candidate_id"))
        return {
            "name": "Confidence Valid",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_ranking_deterministic(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        from src.reinforcement.beam_candidate_builder import BeamCandidateBuilder
        from src.reinforcement.beam_candidate_ranker import BeamCandidateRanker

        invalid = []
        for dm in drawing_models:
            rebuilt, _ = BeamCandidateBuilder().build(
                model,
                dm.get("drawing_id", ""),
                dm.get("drawing_set_id", ""),
                dm.get("floor_id", ""),
                dm.get("detail_identities", []),
            )
            reranked, _, _ = BeamCandidateRanker().rank(
                rebuilt,
                dm.get("detail_identities", []),
            )
            expected = {c["candidate_id"]: c for c in reranked}
            for cand in dm.get("beam_match_candidates", []):
                cid = cand.get("candidate_id")
                exp = expected.get(cid)
                if not exp or exp.get("metadata", {}).get("rank") != cand.get("metadata", {}).get("rank"):
                    invalid.append(cid)
        return {
            "name": "Ranking Deterministic",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_duplicate_best_candidate(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                best = ident.get("best_candidate_id")
                if not best:
                    continue
                matches = [
                    c
                    for c in dm.get("beam_match_candidates", [])
                    if c.get("detail_identity_id") == ident.get("detail_identity_id")
                    and c.get("candidate_id") == best
                ]
                if len(matches) != 1:
                    invalid.append(ident.get("detail_identity_id"))
        return {
            "name": "No Duplicate Best Candidate",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_ownership(self, drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for rel in dm.get("candidate_relationships", []):
                if "OWN" in str(rel.get("relationship", "")).upper():
                    return {"name": "No Ownership", "status": "FAIL"}
        return {"name": "No Ownership", "status": "PASS"}

    def _check_no_matching(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for ident in dm.get("detail_identities", []):
                if ident.get("matching_status") != MATCHING_STATUS_NOT_MATCHED:
                    invalid.append(ident.get("detail_identity_id"))
            for cand in dm.get("beam_match_candidates", []):
                if cand.get("status") not in (CANDIDATE_STATUS_RANKED, "GENERATED"):
                    if cand.get("status") in ("MATCHED", "SELECTED"):
                        invalid.append(cand.get("candidate_id"))
        return {
            "name": "No Final Matching",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_no_parsing(self, drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for cand in dm.get("beam_match_candidates", []):
                if "parsed" in cand or "bar_schedule" in cand:
                    return {"name": "No Parsing", "status": "FAIL"}
        return {"name": "No Parsing", "status": "PASS"}

    def _check_no_quantities(self, model: dict[str, Any]) -> dict[str, Any]:
        found = [k for k in ("quantities", "steel_weight", "boq") if k in model]
        return {
            "name": "No Quantities",
            "status": "PASS" if not found else "FAIL",
            "found": found,
        }

    def _check_no_beam_context_modification(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for ctx in model.get("beam_engineering_contexts", []):
            if ctx.get("reinforcement_context_id"):
                invalid.append(ctx.get("context_id"))
            if ctx.get("detail_identity_id"):
                invalid.append(ctx.get("context_id"))
        return {
            "name": "No BeamContext Modification",
            "status": "PASS" if not invalid else "FAIL",
            "invalid": invalid,
        }

    def _check_graph_relationships(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        candidate_nodes = [
            n for n in graph.get("nodes", []) if n.get("type") == "MATCH_CANDIDATE"
        ]
        has_candidate_edge = any(
            e.get("relationship") == "HAS_CANDIDATE" for e in graph.get("edges", [])
        )
        has_targets_edge = any(
            e.get("relationship") == "TARGETS" for e in graph.get("edges", [])
        )
        ok = len(candidate_nodes) > 0 and has_candidate_edge and has_targets_edge
        return {
            "name": "Graph Candidate Relationships Valid",
            "status": "PASS" if ok else "FAIL",
            "candidate_nodes": len(candidate_nodes),
            "has_candidate_edge": has_candidate_edge,
            "has_targets_edge": has_targets_edge,
        }

    def _check_registry_complete(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        registry = model.get("beam_candidate_registry", {})
        expected = sum(dm.get("beam_match_candidate_count", 0) for dm in drawing_models)
        actual = registry.get("candidate_count", 0)
        return {
            "name": "Candidate Registry Complete",
            "status": "PASS" if expected > 0 and actual == expected else "FAIL",
            "expected": expected,
            "actual": actual,
        }
