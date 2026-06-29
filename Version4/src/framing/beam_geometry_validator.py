"""Validate Phase F.1 beam geometry outputs."""

from __future__ import annotations

from typing import Any, List


class BeamGeometryValidator:
    """Verify beam geometry model completeness."""

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        checks: List[dict[str, Any]] = []
        beams = model.get("beams", [])

        checks.append(self._check_beams_detected(beams))
        checks.append(self._check_centerlines(beams))
        checks.append(self._check_orientation(beams))
        checks.append(self._check_geometry_objects(beams))
        checks.append(self._check_connectivity(model))
        checks.append(self._check_supports(model))
        checks.append(self._check_depth_from_labels(beams))

        failed = [check for check in checks if check["status"] == "FAIL"]
        return {
            "status": "PASS" if not failed else "FAIL",
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["status"] == "PASS"),
                "failed": len(failed),
            },
        }

    def _check_beams_detected(self, beams: list) -> dict[str, Any]:
        ok = len(beams) >= 1
        return {
            "name": "Beam Detection",
            "status": "PASS" if ok else "FAIL",
            "beam_count": len(beams),
        }

    def _check_centerlines(self, beams: list) -> dict[str, Any]:
        with_centerline = sum(
            1
            for beam in beams
            if beam.get("geometry", {}).get("centerline") is not None
        )
        ok = with_centerline == len(beams) and with_centerline > 0
        return {
            "name": "Centreline Extraction",
            "status": "PASS" if ok else "FAIL",
            "with_centerline": with_centerline,
            "total": len(beams),
        }

    def _check_orientation(self, beams: list) -> dict[str, Any]:
        oriented = sum(
            1
            for beam in beams
            if beam.get("geometry", {}).get("orientation") is not None
        )
        ok = oriented == len(beams) and oriented > 0
        return {
            "name": "Orientation",
            "status": "PASS" if ok else "FAIL",
            "oriented_count": oriented,
        }

    def _check_geometry_objects(self, beams: list) -> dict[str, Any]:
        if not beams:
            return {"name": "Geometry Object", "status": "FAIL"}
        ok = all(
            beam.get("geometry", {}).get("bbox") is not None
            and beam.get("geometry", {}).get("length_mm") is not None
            for beam in beams
        )
        return {
            "name": "Geometry Object",
            "status": "PASS" if ok else "FAIL",
        }

    def _check_connectivity(self, model: dict[str, Any]) -> dict[str, Any]:
        graph = model.get("connectivity_graph", {})
        beam_count = len(model.get("beams", []))
        ok = beam_count == 0 or graph.get("edge_count", 0) >= beam_count
        return {
            "name": "Connectivity Graph",
            "status": "PASS" if ok else "FAIL",
            "edge_count": graph.get("edge_count", 0),
        }

    def _check_supports(self, model: dict[str, Any]) -> dict[str, Any]:
        supports = model.get("supports", [])
        beam_count = len(model.get("beams", []))
        ok = beam_count == 0 or len(supports) >= beam_count * 2
        return {
            "name": "Support Detection",
            "status": "PASS" if ok else "FAIL",
            "support_count": len(supports),
        }

    def _check_depth_from_labels(self, beams: list) -> dict[str, Any]:
        known_depth = sum(
            1
            for beam in beams
            if beam.get("dimensions", {}).get("depth", {}).get("status") == "KNOWN"
        )
        ok = known_depth == len(beams) and known_depth > 0
        return {
            "name": "Depth Extraction",
            "status": "PASS" if ok else "FAIL",
            "known_depth_count": known_depth,
        }
