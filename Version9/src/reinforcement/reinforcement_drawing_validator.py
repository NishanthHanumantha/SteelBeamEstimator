"""Validate reinforcement drawing geometry intelligence."""

from __future__ import annotations

from typing import Any, List

from src.reinforcement.reinforcement_geometry_entity import ENGINEERING_STATUS_GEOMETRY_ONLY


class ReinforcementDrawingValidator:
    """Verify G.2 geometry extraction without engineering interpretation."""

    def validate(
        self,
        model: dict[str, Any],
        drawing_models: List[dict[str, Any]],
    ) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        checks.append(self._check_models_created(drawing_models))
        checks.append(self._check_regions_detected(drawing_models))
        checks.append(self._check_sketches_detected(drawing_models))
        checks.append(self._check_text_extracted(drawing_models))
        checks.append(self._check_leaders_extracted(drawing_models))
        checks.append(self._check_blocks_extracted(drawing_models))
        checks.append(self._check_relationships_built(drawing_models))
        checks.append(self._check_geometry_ids_unique(drawing_models))
        checks.append(self._check_engineering_object_ids_null(drawing_models))
        checks.append(self._check_engineering_status_geometry_only(drawing_models))
        checks.append(self._check_workspace_populated(model, drawing_models))
        checks.append(self._check_graph_updated(model))
        checks.append(self._check_no_beam_matching(model))
        checks.append(self._check_no_ownership(model))
        checks.append(self._check_no_parsing(drawing_models))
        checks.append(self._check_no_engineering_computation(model))
        checks.append(self._check_regions_have_sketches(drawing_models))
        checks.append(self._check_regions_have_beam_marks(drawing_models))
        checks.append(self._check_grouped_region_continuity(drawing_models))
        checks.append(self._check_sketches_single_region(drawing_models))
        checks.append(self._check_regions_no_overlap(drawing_models))
        checks.append(self._check_region_boundaries_deterministic(drawing_models))
        checks.append(self._check_duplicate_marks_detected(drawing_models))
        checks.append(self._check_duplicate_marks_multiview(drawing_models))
        checks.append(self._check_no_continuous_with_duplicates(drawing_models))
        checks.append(self._check_continuous_unique_marks(drawing_models))
        checks.append(self._check_views_single_region(drawing_models))
        checks.append(self._check_views_have_beam_mark(drawing_models))
        checks.append(self._check_region_beam_count(drawing_models))
        checks.append(self._check_region_view_count(drawing_models))

        failed = [c for c in checks if c["status"] == "FAIL"]
        return {
            "phase": "Phase G.2.2",
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for c in checks if c["status"] == "PASS"),
                "failed": len(failed),
                "drawing_model_count": len(drawing_models),
                "region_count": sum(dm.get("region_count", 0) for dm in drawing_models),
                "sketch_count": sum(dm.get("sketch_count", 0) for dm in drawing_models),
                "text_count": sum(dm.get("text_count", 0) for dm in drawing_models),
                "leader_count": sum(dm.get("leader_count", 0) for dm in drawing_models),
                "block_count": sum(dm.get("block_count", 0) for dm in drawing_models),
                "detail_view_count": sum(dm.get("detail_view_count", 0) for dm in drawing_models),
            },
        }

    def _check_models_created(self, drawing_models: list) -> dict[str, Any]:
        ok = len(drawing_models) > 0
        return {"name": "ReinforcementDrawingModel Created", "status": "PASS" if ok else "FAIL", "count": len(drawing_models)}

    def _check_regions_detected(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("region_count", 0) for dm in drawing_models)
        return {"name": "Regions Detected", "status": "PASS" if count > 0 else "FAIL", "count": count}

    def _check_sketches_detected(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("sketch_count", 0) for dm in drawing_models)
        return {"name": "Sketches Detected", "status": "PASS" if count > 0 else "FAIL", "count": count}

    def _check_text_extracted(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("text_count", 0) for dm in drawing_models)
        return {"name": "Text Extracted", "status": "PASS" if count > 0 else "FAIL", "count": count}

    def _check_leaders_extracted(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("leader_count", 0) for dm in drawing_models)
        return {"name": "Leaders Extracted", "status": "PASS" if count > 0 else "FAIL", "count": count}

    def _check_blocks_extracted(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("block_count", 0) for dm in drawing_models)
        return {"name": "Blocks Extracted", "status": "PASS" if count > 0 else "FAIL", "count": count}

    def _check_relationships_built(self, drawing_models: list) -> dict[str, Any]:
        count = sum(dm.get("relationship_count", 0) for dm in drawing_models)
        return {"name": "Relationships Built", "status": "PASS" if count > 0 else "FAIL", "count": count}

    def _check_geometry_ids_unique(self, drawing_models: list) -> dict[str, Any]:
        ids: list[str] = []
        for dm in drawing_models:
            for key in ("regions", "detail_views", "sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    ids.append(str(item.get("geometry_id", "")))
        duplicates = sorted({gid for gid in ids if ids.count(gid) > 1})
        ok = len(ids) > 0 and not duplicates
        return {
            "name": "Geometry IDs Unique",
            "status": "PASS" if ok else "FAIL",
            "total_ids": len(ids),
            "duplicates": duplicates,
        }

    def _check_engineering_object_ids_null(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for key in ("regions", "detail_views", "sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    if item.get("engineering_object_id") is not None:
                        invalid.append(item.get("geometry_id"))
        ok = not invalid
        return {
            "name": "Engineering Object IDs NULL",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_engineering_status_geometry_only(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for key in ("regions", "detail_views", "sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    if item.get("engineering_status") != ENGINEERING_STATUS_GEOMETRY_ONLY:
                        invalid.append(item.get("geometry_id"))
        ok = not invalid
        return {
            "name": "Engineering Status GEOMETRY_ONLY",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_workspace_populated(
        self,
        model: dict[str, Any],
        drawing_models: list,
    ) -> dict[str, Any]:
        populated = 0
        for ws in model.get("reinforcement_workspaces", []):
            if ws.get("regions") and ws.get("text_objects"):
                populated += 1
        ok = populated == len(drawing_models) and populated > 0
        return {
            "name": "Workspace Populated",
            "status": "PASS" if ok else "FAIL",
            "populated": populated,
        }

    def _check_graph_updated(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("project_engineering_graph", {})
        region_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "REGION"]
        ok = graph.get("phase") in (
            "Phase G.2",
            "Phase G.2.1",
            "Phase G.2.2",
            "Phase G.2.3",
            "Phase G.2.4",
            "Phase G.2.5",
            "Phase G.2.6",
            "Phase G.2.7",
            "Phase G.3",
            "Phase G.4",
        ) and len(region_nodes) > 0
        return {
            "name": "Graph Updated",
            "status": "PASS" if ok else "FAIL",
            "region_nodes": len(region_nodes),
        }

    def _check_no_beam_matching(self, model: dict[str, Any]) -> dict[str, Any]:
        invalid = []
        for dm in model.get("reinforcement_drawing_models", []):
            for key in ("regions", "detail_views", "sketches", "text_objects", "leaders", "blocks"):
                for item in dm.get(key, []):
                    if item.get("beam_context_id") or item.get("matched_beam_id"):
                        invalid.append(item.get("geometry_id"))
        ok = not invalid
        return {
            "name": "No Beam Matching",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_no_ownership(self, model: dict[str, Any]) -> dict[str, Any]:
        for dm in model.get("reinforcement_drawing_models", []):
            for rel in dm.get("relationships", []):
                rel_name = str(rel.get("relationship", "")).upper()
                if "OWN" in rel_name:
                    return {"name": "No Ownership", "status": "FAIL", "relationship": rel_name}
        return {"name": "No Ownership", "status": "PASS"}

    def _check_no_parsing(self, drawing_models: list) -> dict[str, Any]:
        for dm in drawing_models:
            for text in dm.get("text_objects", []):
                if "parsed" in text or "engineering_type" in text:
                    return {"name": "No Parsing", "status": "FAIL"}
        return {"name": "No Parsing", "status": "PASS"}

    def _check_no_engineering_computation(self, model: dict[str, Any]) -> dict[str, Any]:
        keys = ("engineering_objects", "steel_weight", "quantities", "parsed_bars")
        found = [key for key in keys if key in model]
        ok = not found
        return {
            "name": "No Engineering Computation",
            "status": "PASS" if ok else "FAIL",
            "found": found,
        }

    def _check_regions_have_sketches(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        for dm in drawing_models:
            sketches = dm.get("sketches", [])
            sketches_by_region: dict[str, int] = {}
            for sketch in sketches:
                rid = sketch.get("region_id", "")
                sketches_by_region[rid] = sketches_by_region.get(rid, 0) + 1
            for region in dm.get("regions", []):
                rid = region.get("geometry_id", "")
                if sketches_by_region.get(rid, 0) < 1:
                    missing.append(rid)
        ok = not missing
        return {
            "name": "Every Region Has Sketch",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_regions_have_beam_marks(self, drawing_models: list) -> dict[str, Any]:
        missing = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                if not region.get("beam_marks"):
                    missing.append(region.get("geometry_id"))
        ok = not missing
        return {
            "name": "Every Region Has Beam Mark",
            "status": "PASS" if ok else "FAIL",
            "missing": missing,
        }

    def _check_grouped_region_continuity(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        threshold = 0.75
        for dm in drawing_models:
            for region in dm.get("regions", []):
                if region.get("detail_type") != "CONTINUOUS_MULTI_SPAN":
                    continue
                marks = region.get("beam_marks", [])
                score = float(region.get("continuity_score", 0.0))
                if score < threshold:
                    invalid.append(
                        {
                            "geometry_id": region.get("geometry_id"),
                            "beam_marks": marks,
                            "continuity_score": score,
                        }
                    )
        ok = not invalid
        return {
            "name": "Grouped Regions Continuity Score",
            "status": "PASS" if ok else "FAIL",
            "threshold": threshold,
            "invalid": invalid,
        }

    def _check_sketches_single_region(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            seen: dict[str, str] = {}
            for sketch in dm.get("sketches", []):
                sid = sketch.get("geometry_id", "")
                rid = sketch.get("region_id", "")
                if sid in seen and seen[sid] != rid:
                    invalid.append(sid)
                seen[sid] = rid
                if not rid:
                    invalid.append(sid)
        ok = not invalid
        return {
            "name": "Every Sketch One Region",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_regions_no_overlap(self, drawing_models: list) -> dict[str, Any]:
        overlaps = []
        tolerance = 50.0
        row_tolerance = 2500.0
        for dm in drawing_models:
            regions = dm.get("regions", [])
            for i, left in enumerate(regions):
                lb = left.get("bbox", {})
                left_header = left.get("header_bbox", {})
                left_y = (left_header.get("min_y", 0) + left_header.get("max_y", 0)) / 2.0
                for right in regions[i + 1 :]:
                    rb = right.get("bbox", {})
                    right_header = right.get("header_bbox", {})
                    right_y = (right_header.get("min_y", 0) + right_header.get("max_y", 0)) / 2.0
                    if abs(left_y - right_y) > row_tolerance:
                        continue
                    if not lb or not rb:
                        continue
                    ox = max(0.0, min(lb["max_x"], rb["max_x"]) - max(lb["min_x"], rb["min_x"]))
                    oy = max(0.0, min(lb["max_y"], rb["max_y"]) - max(lb["min_y"], rb["min_y"]))
                    if ox > tolerance and oy > tolerance:
                        overlaps.append(
                            {
                                "left": left.get("geometry_id"),
                                "right": right.get("geometry_id"),
                                "overlap_mm2": round(ox * oy, 2),
                            }
                        )
        ok = not overlaps
        return {
            "name": "Regions Do Not Overlap",
            "status": "PASS" if ok else "FAIL",
            "overlaps": overlaps,
        }

    def _check_region_boundaries_deterministic(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                bbox = region.get("bbox", {})
                if not bbox or bbox.get("max_x", 0) <= bbox.get("min_x", 0):
                    invalid.append(region.get("geometry_id"))
        ok = not invalid
        return {
            "name": "Region Boundaries Deterministic",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_duplicate_marks_detected(self, drawing_models: list) -> dict[str, Any]:
        detected = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                if region.get("duplicate_mark_detected"):
                    detected.append(region.get("geometry_id"))
        ok = len(detected) > 0
        return {
            "name": "Duplicate Beam Marks Detected",
            "status": "PASS" if ok else "FAIL",
            "regions": detected,
        }

    def _check_duplicate_marks_multiview(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                if not region.get("duplicate_mark_detected"):
                    continue
                if region.get("detail_type") != "MULTI_VIEW_SINGLE_BEAM":
                    invalid.append(region.get("geometry_id"))
        ok = not invalid
        return {
            "name": "Duplicate Marks Become MULTI_VIEW_SINGLE_BEAM",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_no_continuous_with_duplicates(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                if region.get("detail_type") != "CONTINUOUS_MULTI_SPAN":
                    continue
                marks = region.get("beam_marks", [])
                if len(marks) != len(set(marks)):
                    invalid.append(region.get("geometry_id"))
        ok = not invalid
        return {
            "name": "Duplicate Marks Never CONTINUOUS_MULTI_SPAN",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_continuous_unique_marks(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                if region.get("detail_type") != "CONTINUOUS_MULTI_SPAN":
                    continue
                marks = region.get("beam_marks", [])
                if len(marks) <= 1 or len(marks) != len(set(marks)):
                    invalid.append(
                        {
                            "geometry_id": region.get("geometry_id"),
                            "beam_marks": marks,
                        }
                    )
        ok = not invalid
        return {
            "name": "Continuous Multi-Span Unique Beam Marks",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_views_single_region(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        seen: dict[str, str] = {}
        for dm in drawing_models:
            for view in dm.get("detail_views", []):
                vid = view.get("view_id", view.get("geometry_id", ""))
                rid = view.get("region_id", "")
                if vid in seen and seen[vid] != rid:
                    invalid.append(vid)
                seen[vid] = rid
                if not rid:
                    invalid.append(vid)
        ok = not invalid
        return {
            "name": "Every View One Region",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_views_have_beam_mark(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for view in dm.get("detail_views", []):
                if not view.get("beam_mark"):
                    invalid.append(view.get("view_id", view.get("geometry_id")))
        ok = not invalid
        return {
            "name": "Every View References Beam Mark",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_region_beam_count(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            for region in dm.get("regions", []):
                marks = region.get("beam_marks", [])
                beam_count = region.get("beam_count")
                if beam_count is None:
                    continue
                if beam_count != len(set(marks)):
                    invalid.append(region.get("geometry_id"))
        ok = not invalid
        return {
            "name": "Region Beam Count Matches Unique Marks",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }

    def _check_region_view_count(self, drawing_models: list) -> dict[str, Any]:
        invalid = []
        for dm in drawing_models:
            views_by_region: dict[str, int] = {}
            for view in dm.get("detail_views", []):
                rid = view.get("region_id", "")
                views_by_region[rid] = views_by_region.get(rid, 0) + 1
            for region in dm.get("regions", []):
                rid = region.get("geometry_id", "")
                expected = region.get("view_count", 0)
                actual = views_by_region.get(rid, 0)
                if expected != actual:
                    invalid.append(
                        {
                            "geometry_id": rid,
                            "expected": expected,
                            "actual": actual,
                        }
                    )
        ok = not invalid
        return {
            "name": "View Count Matches Detail Views",
            "status": "PASS" if ok else "FAIL",
            "invalid": invalid,
        }
