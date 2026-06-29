"""Phase F debug DXF exporter for beam geometry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

import ezdxf
from loguru import logger

_LAYER_CENTERLINE = "DEBUG_BEAM_CENTERLINE"
_LAYER_CONNECTIVITY = "DEBUG_BEAM_CONNECTIVITY"
_LAYER_SUPPORTS = "DEBUG_BEAM_SUPPORTS"
_LAYER_GEOMETRY = "DEBUG_BEAM_GEOMETRY"
_LAYER_DIMENSIONS = "DEBUG_DIMENSIONS"
_LAYER_SECTION = "DEBUG_SECTION"
_LAYER_STRUCTURAL_NODES = "DEBUG_STRUCTURAL_NODES"
_LAYER_ENGINEERING_LENGTHS = "DEBUG_ENGINEERING_LENGTHS"
_LAYER_GRAPH = "DEBUG_GRAPH"
_LAYER_STATIONING = "DEBUG_STATIONING"
_LAYER_RELATIONSHIPS = "DEBUG_RELATIONSHIPS"
_LAYER_ENGINEERING_CONTEXT = "DEBUG_ENGINEERING_CONTEXT"
_LAYER_DEPENDENCIES = "DEBUG_DEPENDENCIES"
_LAYER_PROJECT_GRAPH = "DEBUG_PROJECT_GRAPH"
_LAYER_DEBUG_PROJECT = "DEBUG_PROJECT"
_LAYER_DEBUG_FLOORS = "DEBUG_FLOORS"
_LAYER_DEBUG_WORKSPACE = "DEBUG_WORKSPACE"
_LAYER_DEBUG_REINFORCEMENT_WORKSPACE = "DEBUG_REINFORCEMENT_WORKSPACE"
_LAYER_DEBUG_REINFORCEMENT_DOCUMENT = "DEBUG_REINFORCEMENT_DOCUMENT"
_LAYER_DEBUG_REINFORCEMENT_REGISTRY = "DEBUG_REINFORCEMENT_REGISTRY"


class BeamGeometryDebugExporter:
    """Draw centreline, support, connectivity, section, and length debug layers."""

    def export(
        self,
        model: dict[str, Any],
        output_path: Path,
        show_dimensions: bool = True,
        show_supports: bool = True,
        show_section: bool = True,
        show_structural_nodes: bool = True,
        show_engineering_lengths: bool = True,
        show_graph: bool = True,
        show_engineering_context: bool = True,
        show_dependencies: bool = True,
        show_project_graph: bool = True,
        show_workspace: bool = True,
    ) -> None:
        doc = ezdxf.new("R2010")
        layers = [
            _LAYER_CENTERLINE,
            _LAYER_CONNECTIVITY,
            _LAYER_SUPPORTS,
            _LAYER_GEOMETRY,
        ]
        if show_dimensions:
            layers.append(_LAYER_DIMENSIONS)
        if show_section:
            layers.append(_LAYER_SECTION)
        if show_structural_nodes:
            layers.append(_LAYER_STRUCTURAL_NODES)
        if show_engineering_lengths:
            layers.append(_LAYER_ENGINEERING_LENGTHS)
        if show_graph:
            layers.extend([_LAYER_GRAPH, _LAYER_STATIONING, _LAYER_RELATIONSHIPS])
        if show_engineering_context:
            layers.append(_LAYER_ENGINEERING_CONTEXT)
        if show_dependencies:
            layers.append(_LAYER_DEPENDENCIES)
        if show_project_graph:
            layers.append(_LAYER_PROJECT_GRAPH)
        if show_workspace:
            layers.extend([_LAYER_DEBUG_PROJECT, _LAYER_DEBUG_FLOORS, _LAYER_DEBUG_WORKSPACE])
        for layer in layers:
            if layer not in doc.layers:
                doc.layers.add(layer)

        msp = doc.modelspace()
        beams = model.get("beams", [])

        for beam in beams:
            geometry = beam.get("geometry", {})
            centerline = geometry.get("centerline")
            if not centerline:
                continue
            start = centerline["start_point"]
            end = centerline["end_point"]
            msp.add_line(
                (start["x"], start["y"]),
                (end["x"], end["y"]),
                dxfattribs={"layer": _LAYER_CENTERLINE, "color": 3},
            )
            mid_x = (start["x"] + end["x"]) / 2.0
            mid_y = (start["y"] + end["y"]) / 2.0
            msp.add_text(
                beam["beam_mark"],
                dxfattribs={
                    "layer": _LAYER_GEOMETRY,
                    "height": 180.0,
                    "insert": (mid_x, mid_y),
                    "color": 2,
                },
            )
            bbox = geometry.get("bbox")
            if bbox:
                msp.add_lwpolyline(
                    [
                        (bbox["min_x"], bbox["min_y"]),
                        (bbox["max_x"], bbox["min_y"]),
                        (bbox["max_x"], bbox["max_y"]),
                        (bbox["min_x"], bbox["max_y"]),
                        (bbox["min_x"], bbox["min_y"]),
                    ],
                    dxfattribs={"layer": _LAYER_GEOMETRY, "color": 8},
                )

            if show_dimensions:
                section = beam.get("dimensions", {}).get("section", {})
                designation = section.get("designation", "UNKNOWN")
                section_label = f"{beam['beam_mark']}\n{designation.replace('x', '×')}"
                msp.add_text(
                    section_label,
                    dxfattribs={
                        "layer": _LAYER_DIMENSIONS,
                        "height": 200.0,
                        "insert": (mid_x + 250, mid_y + 250),
                        "color": 5,
                    },
                )

            if show_section:
                eng_section = beam.get("beam_section", {})
                label = (
                    f"{beam['beam_mark']}\n"
                    f"{eng_section.get('designation', 'UNKNOWN')}\n"
                    f"{eng_section.get('classification', 'UNKNOWN')}"
                )
                msp.add_text(
                    label,
                    dxfattribs={
                        "layer": _LAYER_SECTION,
                        "height": 180.0,
                        "insert": (mid_x - 300, mid_y - 300),
                        "color": 4,
                    },
                )

            if show_engineering_lengths:
                lm = beam.get("length_model", {})
                cl = lm.get("centerline_length", {}).get("value")
                cs = lm.get("clear_span", {}).get("value")
                length_label = (
                    f"{beam['beam_mark']}\n"
                    f"CL={int(cl) if cl else '?'}\n"
                    f"CS={int(cs) if cs else '?'}"
                )
                msp.add_text(
                    length_label,
                    dxfattribs={
                        "layer": _LAYER_ENGINEERING_LENGTHS,
                        "height": 160.0,
                        "insert": (mid_x + 400, mid_y - 400),
                        "color": 140,
                    },
                )
                left_b = lm.get("bearing_length_left", {}).get("value")
                right_b = lm.get("bearing_length_right", {}).get("value")
                if left_b and left_b > 0:
                    msp.add_circle(
                        (start["x"], start["y"]),
                        radius=min(float(left_b), 500.0),
                        dxfattribs={"layer": _LAYER_ENGINEERING_LENGTHS, "color": 140},
                    )
                if right_b and right_b > 0:
                    msp.add_circle(
                        (end["x"], end["y"]),
                        radius=min(float(right_b), 500.0),
                        dxfattribs={"layer": _LAYER_ENGINEERING_LENGTHS, "color": 140},
                    )

            if show_graph:
                stationing = beam.get("stationing", {})
                for st in stationing.get("stations", []):
                    g = st.get("global", {})
                    gx, gy = g.get("x"), g.get("y")
                    if gx is None or gy is None:
                        continue
                    msp.add_circle(
                        (gx, gy),
                        radius=80.0,
                        dxfattribs={"layer": _LAYER_STATIONING, "color": 11},
                    )
                    msp.add_text(
                        st.get("label", ""),
                        dxfattribs={
                            "layer": _LAYER_STATIONING,
                            "height": 100.0,
                            "insert": (gx + 100, gy + 100),
                            "color": 11,
                        },
                    )
                msp.add_text(
                    f"{beam['beam_mark']}\nS0→SL",
                    dxfattribs={
                        "layer": _LAYER_GRAPH,
                        "height": 140.0,
                        "insert": (start["x"] - 200, start["y"] - 200),
                        "color": 7,
                    },
                )

            if show_supports:
                support_model = beam.get("supports", {})
                for end_name, point in (
                    ("left", start),
                    ("right", end),
                ):
                    support = support_model.get(end_name, {})
                    x, y = point["x"], point["y"]
                    msp.add_circle(
                        (x, y),
                        radius=120.0,
                        dxfattribs={"layer": _LAYER_SUPPORTS, "color": 1},
                    )
                    msp.add_text(
                        f"{support.get('type', '?')}:{support.get('id', '-')}",
                        dxfattribs={
                            "layer": _LAYER_SUPPORTS,
                            "height": 120.0,
                            "insert": (x + 150, y + 150),
                            "color": 1,
                        },
                    )

        if show_structural_nodes:
            for node in model.get("structural_nodes", []):
                location = node.get("location") or {}
                x = location.get("x")
                y = location.get("y")
                if x is None or y is None:
                    continue
                msp.add_circle(
                    (x, y),
                    radius=200.0,
                    dxfattribs={"layer": _LAYER_STRUCTURAL_NODES, "color": 30},
                )
                msp.add_text(
                    f"{node.get('id')}\n{node.get('type')}",
                    dxfattribs={
                        "layer": _LAYER_STRUCTURAL_NODES,
                        "height": 150.0,
                        "insert": (x + 220, y + 220),
                        "color": 30,
                    },
                )

        for edge in model.get("connectivity_graph", {}).get("edges", []):
            from_id = edge.get("from")
            to_id = edge.get("to")
            beam = next(
                (item for item in beams if item["beam_id"] in (from_id, to_id)),
                None,
            )
            if not beam:
                continue
            geometry = beam.get("geometry", {})
            centerline = geometry.get("centerline")
            if not centerline:
                continue
            end_name = edge.get("end")
            if end_name == "start":
                point = centerline["start_point"]
            elif end_name == "end":
                point = centerline["end_point"]
            else:
                point = centerline["start_point"]
            label = edge.get("relationship", edge.get("support_type", "connect"))
            msp.add_text(
                label,
                dxfattribs={
                    "layer": _LAYER_CONNECTIVITY,
                    "height": 100.0,
                    "insert": (point["x"], point["y"] - 200),
                    "color": 6,
                },
            )

        if show_graph:
            beam_lookup = {b["beam_id"]: b for b in beams}
            for edge in model.get("beam_relationships", {}).get("edges", []):
                rel = edge.get("relationship", "")
                from_id = edge.get("from")
                to_id = edge.get("to")
                beam = beam_lookup.get(from_id) or beam_lookup.get(to_id)
                if not beam:
                    continue
                cl = beam.get("geometry", {}).get("centerline") or {}
                pt = cl.get("start_point") or {}
                msp.add_text(
                    f"{rel}:{from_id}→{to_id}",
                    dxfattribs={
                        "layer": _LAYER_RELATIONSHIPS,
                        "height": 90.0,
                        "insert": (pt.get("x", 0), pt.get("y", 0) - 350),
                        "color": 13,
                    },
                )

        if show_engineering_context:
            for beam in beams:
                geometry = beam.get("geometry", {})
                centerline = geometry.get("centerline") or {}
                start = centerline.get("start_point") or {}
                ctx = beam.get("engineering_context", {})
                ctx_id = ctx.get("context_id", "?")
                msp.add_text(
                    f"CTX:{ctx_id}",
                    dxfattribs={
                        "layer": _LAYER_ENGINEERING_CONTEXT,
                        "height": 120.0,
                        "insert": (start.get("x", 0) + 500, start.get("y", 0) + 500),
                        "color": 22,
                    },
                )

        if show_dependencies:
            dep_graph = model.get("engineering_dependency_graph", {})
            computations = dep_graph.get("computations", [])
            label_y = 0.0
            for comp in computations[:8]:
                msp.add_text(
                    f"DEP:{comp.get('id', '?')}",
                    dxfattribs={
                        "layer": _LAYER_DEPENDENCIES,
                        "height": 200.0,
                        "insert": (-5000.0, label_y),
                        "color": 23,
                    },
                )
                label_y += 400.0

        if show_project_graph:
            project_graph = model.get("project_engineering_graph", {})
            root = project_graph.get("root", {})
            root_id = root.get("id", "PROJECT")
            msp.add_text(
                f"ROOT:{root_id}",
                dxfattribs={
                    "layer": _LAYER_PROJECT_GRAPH,
                    "height": 300.0,
                    "insert": (-5000.0, -2000.0),
                    "color": 24,
                },
            )
            for beam in beams:
                geometry = beam.get("geometry", {})
                centerline = geometry.get("centerline") or {}
                start = centerline.get("start_point") or {}
                lcs = beam.get("local_coordinate_system", {})
                gcs = beam.get("global_coordinates", {})
                origin = gcs.get("origin") if isinstance(gcs.get("origin"), dict) else None
                if not origin:
                    origin = lcs.get("origin")
                if isinstance(origin, dict):
                    ox, oy = origin.get("x", start.get("x", 0)), origin.get("y", start.get("y", 0))
                else:
                    ox, oy = start.get("x", 0), start.get("y", 0)
                msp.add_circle(
                    (ox, oy),
                    radius=60.0,
                    dxfattribs={"layer": _LAYER_PROJECT_GRAPH, "color": 24},
                )
                msp.add_text(
                    "S0",
                    dxfattribs={
                        "layer": _LAYER_PROJECT_GRAPH,
                        "height": 80.0,
                        "insert": (ox + 80, oy + 80),
                        "color": 24,
                    },
                )

        if show_workspace:
            ws = model.get("project_workspace", {})
            msp.add_text(
                f"PROJECT:{ws.get('project_id', '?')}",
                dxfattribs={
                    "layer": _LAYER_DEBUG_PROJECT,
                    "height": 350.0,
                    "insert": (-8000.0, -3000.0),
                    "color": 25,
                },
            )
            msp.add_text(
                f"GN:{ws.get('general_notes', {}).get('document_id', '?')}",
                dxfattribs={
                    "layer": _LAYER_DEBUG_PROJECT,
                    "height": 250.0,
                    "insert": (-8000.0, -3400.0),
                    "color": 25,
                },
            )
            for idx, floor in enumerate(ws.get("floors", [])):
                msp.add_text(
                    f"FLOOR:{floor.get('floor_id', '?')}",
                    dxfattribs={
                        "layer": _LAYER_DEBUG_FLOORS,
                        "height": 220.0,
                        "insert": (-8000.0, -4000.0 - idx * 350),
                        "color": 26,
                    },
                )
                fp = floor.get("framing_plan", {})
                msp.add_text(
                    f"Framing:{fp.get('status', '?')} Beams:{fp.get('beam_count', 0)}",
                    dxfattribs={
                        "layer": _LAYER_DEBUG_FLOORS,
                        "height": 180.0,
                        "insert": (-8000.0, -4200.0 - idx * 350),
                        "color": 26,
                    },
                )
            mgr = model.get("workspace_manager", {})
            msp.add_text(
                f"WS:{mgr.get('status', '?')} SVC:{mgr.get('services', '?')}",
                dxfattribs={
                    "layer": _LAYER_DEBUG_WORKSPACE,
                    "height": 280.0,
                    "insert": (-8000.0, -5500.0),
                    "color": 27,
                },
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(str(output_path))
        logger.info("Phase F debug DXF written to {}", output_path)

    def export_reinforcement(
        self,
        model: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Export Phase G.1 reinforcement loading debug layers."""
        doc = ezdxf.new("R2010")
        for layer in (
            _LAYER_DEBUG_REINFORCEMENT_WORKSPACE,
            _LAYER_DEBUG_REINFORCEMENT_DOCUMENT,
            _LAYER_DEBUG_REINFORCEMENT_REGISTRY,
        ):
            if layer not in doc.layers:
                doc.layers.add(layer)

        msp = doc.modelspace()
        workspaces = model.get("reinforcement_workspaces", [])
        registry = model.get("reinforcement_registry", {})

        msp.add_text(
            f"G.1 Reinforcement Loading — workspaces={len(workspaces)}",
            dxfattribs={
                "layer": _LAYER_DEBUG_REINFORCEMENT_WORKSPACE,
                "height": 400.0,
                "insert": (-12000.0, 8000.0),
                "color": 3,
            },
        )

        for idx, ws in enumerate(workspaces):
            y = 7000.0 - idx * 1200.0
            msp.add_text(
                f"WS:{ws.get('workspace_id', '?')} status={ws.get('status', '?')}",
                dxfattribs={
                    "layer": _LAYER_DEBUG_REINFORCEMENT_WORKSPACE,
                    "height": 280.0,
                    "insert": (-12000.0, y),
                    "color": 3,
                },
            )
            doc_info = ws.get("document", {})
            msp.add_text(
                (
                    f"DOC:{doc_info.get('document_id', '?')} "
                    f"entities={doc_info.get('entity_count', 0)} "
                    f"layers={doc_info.get('layer_count', 0)}"
                ),
                dxfattribs={
                    "layer": _LAYER_DEBUG_REINFORCEMENT_DOCUMENT,
                    "height": 220.0,
                    "insert": (-12000.0, y - 350),
                    "color": 5,
                },
            )
            msp.add_text(
                f"FILE:{doc_info.get('drawing_name', '?')} type={doc_info.get('drawing_type', '?')}",
                dxfattribs={
                    "layer": _LAYER_DEBUG_REINFORCEMENT_DOCUMENT,
                    "height": 180.0,
                    "insert": (-12000.0, y - 600),
                    "color": 5,
                },
            )

        for idx, entry in enumerate(registry.get("documents", [])):
            msp.add_text(
                (
                    f"REG:{entry.get('document_id', '?')} "
                    f"floor={entry.get('floor', '?')} "
                    f"status={entry.get('status', '?')}"
                ),
                dxfattribs={
                    "layer": _LAYER_DEBUG_REINFORCEMENT_REGISTRY,
                    "height": 200.0,
                    "insert": (-12000.0, 2000.0 - idx * 300),
                    "color": 6,
                },
            )

        validation = model.get("reinforcement_validation", {})
        msp.add_text(
            f"VALIDATION:{validation.get('status', '?')}",
            dxfattribs={
                "layer": _LAYER_DEBUG_REINFORCEMENT_REGISTRY,
                "height": 280.0,
                "insert": (-12000.0, 2500.0),
                "color": 1 if validation.get("status") == "FAIL" else 3,
            },
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.saveas(str(output_path))
        logger.info("Phase G debug DXF written to {}", output_path)

    def export_drawing_identity(
        self,
        model: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Append Phase G.1.1 drawing identity debug layers."""
        try:
            doc = ezdxf.readfile(str(output_path))
        except Exception:
            doc = ezdxf.new("R2010")

        for layer in (
            "DEBUG_DRAWING_IDENTITY",
            "DEBUG_DRAWING_TITLE",
            "DEBUG_FLOOR_DETECTION",
        ):
            if layer not in doc.layers:
                doc.layers.add(layer)

        msp = doc.modelspace()
        identities = model.get("drawing_identities", [])

        msp.add_text(
            f"G.1.1 Drawing Identity — count={len(identities)}",
            dxfattribs={
                "layer": "DEBUG_DRAWING_IDENTITY",
                "height": 400.0,
                "insert": (-16000.0, 10000.0),
                "color": 4,
            },
        )

        for idx, identity in enumerate(identities):
            y = 9000.0 - idx * 1400.0
            msp.add_text(
                (
                    f"ID:{identity.get('drawing_id', '?')} "
                    f"type={identity.get('drawing_type', '?')} "
                    f"conf={identity.get('confidence', 0):.2f}"
                ),
                dxfattribs={
                    "layer": "DEBUG_DRAWING_IDENTITY",
                    "height": 260.0,
                    "insert": (-16000.0, y),
                    "color": 4,
                },
            )
            msp.add_text(
                f"TITLE:{identity.get('drawing_title', '?')}",
                dxfattribs={
                    "layer": "DEBUG_DRAWING_TITLE",
                    "height": 220.0,
                    "insert": (-16000.0, y - 350),
                    "color": 30,
                },
            )
            msp.add_text(
                (
                    f"FLOOR:{identity.get('floor_name', 'N/A')} "
                    f"slug={identity.get('floor_slug', 'N/A')} "
                    f"source={identity.get('detection_source', '?')}"
                ),
                dxfattribs={
                    "layer": "DEBUG_FLOOR_DETECTION",
                    "height": 200.0,
                    "insert": (-16000.0, y - 650),
                    "color": 2,
                },
            )

        validation = model.get("drawing_identity_validation", {})
        msp.add_text(
            f"IDENTITY_VALIDATION:{validation.get('status', '?')}",
            dxfattribs={
                "layer": "DEBUG_FLOOR_DETECTION",
                "height": 280.0,
                "insert": (-16000.0, 10500.0),
                "color": 1 if validation.get("status") == "FAIL" else 3,
            },
        )

        doc.saveas(str(output_path))
        logger.info("Phase G.1.1 drawing identity debug appended to {}", output_path)

    def export_drawing_set(
        self,
        model: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Append Phase G.1.2 drawing set debug layers."""
        try:
            doc = ezdxf.readfile(str(output_path))
        except Exception:
            doc = ezdxf.new("R2010")

        for layer in ("DEBUG_DRAWING_SET", "DEBUG_DRAWING_RELATIONSHIPS"):
            if layer not in doc.layers:
                doc.layers.add(layer)

        msp = doc.modelspace()
        sets = model.get("drawing_sets", [])

        msp.add_text(
            f"G.1.2 Drawing Sets — count={len(sets)}",
            dxfattribs={
                "layer": "DEBUG_DRAWING_SET",
                "height": 400.0,
                "insert": (-20000.0, 12000.0),
                "color": 1,
            },
        )

        for idx, ds in enumerate(sets):
            y = 11000.0 - idx * 1600.0
            msp.add_text(
                (
                    f"SET:{ds.get('drawing_set_id', '?')} "
                    f"floor={ds.get('floor_name', '?')} "
                    f"status={ds.get('status', '?')}"
                ),
                dxfattribs={
                    "layer": "DEBUG_DRAWING_SET",
                    "height": 280.0,
                    "insert": (-20000.0, y),
                    "color": 1,
                },
            )
            drawings = ds.get("drawings", {})
            msp.add_text(
                f"FRAMING:{drawings.get('framing', 'N/A')}",
                dxfattribs={
                    "layer": "DEBUG_DRAWING_RELATIONSHIPS",
                    "height": 220.0,
                    "insert": (-20000.0, y - 350),
                    "color": 5,
                },
            )
            msp.add_text(
                f"REINFORCEMENT:{drawings.get('reinforcement', 'N/A')}",
                dxfattribs={
                    "layer": "DEBUG_DRAWING_RELATIONSHIPS",
                    "height": 220.0,
                    "insert": (-20000.0, y - 600),
                    "color": 5,
                },
            )
            msp.add_text(
                f"GN_REF:{drawings.get('general_notes', 'N/A')}",
                dxfattribs={
                    "layer": "DEBUG_DRAWING_RELATIONSHIPS",
                    "height": 200.0,
                    "insert": (-20000.0, y - 850),
                    "color": 6,
                },
            )

        validation = model.get("drawing_set_validation", {})
        msp.add_text(
            f"SET_VALIDATION:{validation.get('status', '?')}",
            dxfattribs={
                "layer": "DEBUG_DRAWING_SET",
                "height": 280.0,
                "insert": (-20000.0, 12500.0),
                "color": 1 if validation.get("status") == "FAIL" else 3,
            },
        )

        doc.saveas(str(output_path))
        logger.info("Phase G.1.2 drawing set debug appended to {}", output_path)

    def export_drawing_set_state(
        self,
        model: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Append Phase G.1.3 lifecycle, version, and beam index debug layers."""
        try:
            doc = ezdxf.readfile(str(output_path))
        except Exception:
            doc = ezdxf.new("R2010")

        for layer in (
            "DEBUG_DRAWING_SET_STATE",
            "DEBUG_DRAWING_SET_VERSION",
            "DEBUG_BEAM_INDEX",
        ):
            if layer not in doc.layers:
                doc.layers.add(layer)

        msp = doc.modelspace()
        sets = model.get("drawing_sets", [])

        for idx, ds in enumerate(sets):
            y = 14000.0 - idx * 1800.0
            msp.add_text(
                f"SET:{ds.get('drawing_set_id', '?')} loading={ds.get('loading_state', '?')}",
                dxfattribs={
                    "layer": "DEBUG_DRAWING_SET_STATE",
                    "height": 260.0,
                    "insert": (-24000.0, y),
                    "color": 2,
                },
            )
            msp.add_text(
                (
                    f"match={ds.get('matching_state', '?')} "
                    f"parse={ds.get('parsing_state', '?')} "
                    f"eng={ds.get('engineering_state', '?')}"
                ),
                dxfattribs={
                    "layer": "DEBUG_DRAWING_SET_STATE",
                    "height": 200.0,
                    "insert": (-24000.0, y - 300),
                    "color": 2,
                },
            )
            version = ds.get("drawing_set_version", {})
            msp.add_text(
                f"VER:{version.get('drawing_set_version', '?')} hash={version.get('version_hash', '?')[:12]}",
                dxfattribs={
                    "layer": "DEBUG_DRAWING_SET_VERSION",
                    "height": 220.0,
                    "insert": (-24000.0, y - 550),
                    "color": 4,
                },
            )
            meta = ds.get("beam_index_meta", {})
            msp.add_text(
                f"BEAMS_INDEXED:{meta.get('beam_count', 0)}",
                dxfattribs={
                    "layer": "DEBUG_BEAM_INDEX",
                    "height": 220.0,
                    "insert": (-24000.0, y - 800),
                    "color": 3,
                },
            )

        validation = model.get("drawing_set_state_validation", {})
        msp.add_text(
            f"STATE_VALIDATION:{validation.get('status', '?')}",
            dxfattribs={
                "layer": "DEBUG_DRAWING_SET_STATE",
                "height": 280.0,
                "insert": (-24000.0, 14500.0),
                "color": 1 if validation.get("status") == "FAIL" else 3,
            },
        )

        doc.saveas(str(output_path))
        logger.info("Phase G.1.3 drawing set state debug appended to {}", output_path)
