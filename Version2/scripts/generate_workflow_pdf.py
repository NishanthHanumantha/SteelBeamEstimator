"""Generate Steel Beam Estimator Version 2 workflow flowchart PDF."""

from pathlib import Path

from fpdf import FPDF

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "SteelBeamEstimator_Workflow_Flowchart.pdf"

# Colors (RGB)
C_INPUT = (41, 98, 155)
C_FOUNDATION = (46, 125, 50)
C_ANNOTATION = (230, 126, 34)
C_AUDIT = (142, 68, 173)
C_FINAL = (192, 57, 43)
C_FUTURE = (127, 140, 141)
C_ARROW = (80, 80, 80)
C_WHITE = (255, 255, 255)
C_LIGHT = (245, 245, 245)
C_TEXT = (33, 33, 33)


def _latin1(text: str) -> str:
    """Ensure text is compatible with Helvetica core font."""
    return (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u2022", "*")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


class WorkflowPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)

    def cell(self, w, h=0, text="", *args, **kwargs):
        return super().cell(w, h, _latin1(text), *args, **kwargs)

    def multi_cell(self, w, h=0, text="", *args, **kwargs):
        return super().multi_cell(w, h, _latin1(text), *args, **kwargs)

    def header(self) -> None:
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*C_ARROW)
            self.cell(0, 8, "Steel Beam Estimator - Version 2 Pipeline Workflow", align="C")
            self.ln(4)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_ARROW)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def title_page(self) -> None:
        self.add_page()
        self.set_fill_color(*C_INPUT)
        self.rect(0, 0, 210, 45, style="F")
        self.set_y(18)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*C_WHITE)
        self.cell(0, 10, "Steel Beam Estimator", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 14)
        self.cell(0, 8, "Version 2 - Pipeline Workflow Flowchart", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_y(55)
        self.set_text_color(*C_TEXT)
        self.set_font("Helvetica", "", 11)
        self.multi_cell(
            0,
            6,
            (
                "This document summarizes all pipeline phases completed to date, from DXF ingestion "
                "through engineering dataset finalization. Phase D.2 (annotation parsing) is the "
                "planned next step.\n\n"
                "Outputs live under data/output/ grouped by phase subdirectory. "
                "Canonical paths: src/config/output_paths.py"
            ),
        )

        self.ln(4)
        self._legend_box()

    def _legend_box(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "Legend", new_x="LMARGIN", new_y="NEXT")
        items = [
            (C_INPUT, "Input / source data"),
            (C_FOUNDATION, "Foundation phases (A-C.5)"),
            (C_ANNOTATION, "Annotation pipeline (D.1)"),
            (C_AUDIT, "Audit / validation sub-phases"),
            (C_FINAL, "Finalization & readiness"),
            (C_FUTURE, "Planned (not implemented)"),
        ]
        y = self.get_y() + 2
        for color, label in items:
            self.set_fill_color(*color)
            self.rect(15, y, 8, 5, style="F")
            self.set_xy(24, y)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*C_TEXT)
            self.cell(0, 5, label)
            y += 7

    def section_title(self, title: str, color: tuple[int, int, int]) -> None:
        self.ln(4)
        self.set_fill_color(*color)
        self.set_text_color(*C_WHITE)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 9, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*C_TEXT)
        self.ln(2)

    def flow_box(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        sublabel: str,
        color: tuple[int, int, int],
        fontsize: int = 8,
    ) -> None:
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        self.rect(x, y, w, h, style="FD")
        self.set_xy(x + 2, y + 2)
        self.set_font("Helvetica", "B", fontsize)
        self.set_text_color(*C_WHITE)
        self.multi_cell(w - 4, 4, label, align="C")
        if sublabel:
            self.set_xy(x + 2, y + h - 10)
            self.set_font("Helvetica", "", 6)
            self.multi_cell(w - 4, 3, sublabel, align="C")

    def arrow_down(self, x: float, y1: float, y2: float) -> None:
        self.set_draw_color(*C_ARROW)
        self.set_line_width(0.4)
        mid_y = (y1 + y2) / 2
        self.line(x, y1, x, y2 - 3)
        # arrowhead
        self.line(x, y2 - 3, x - 2, y2 - 6)
        self.line(x, y2 - 3, x + 2, y2 - 6)
        self.line(x - 2, y2 - 6, x + 2, y2 - 6)

    def arrow_right(self, x1: float, x2: float, y: float) -> None:
        self.set_draw_color(*C_ARROW)
        self.set_line_width(0.4)
        self.line(x1, y, x2 - 3, y)
        self.line(x2 - 3, y, x2 - 6, y - 2)
        self.line(x2 - 3, y, x2 - 6, y + 2)

    def overview_flowchart(self) -> None:
        self.add_page()
        self.section_title("High-Level Pipeline Overview", C_INPUT)

        cx = 105
        box_w = 120
        box_h = 14
        x = cx - box_w / 2

        boxes = [
            (C_INPUT, "DXF INPUT", "Framing plans + Reinforcement drawings"),
            (C_FOUNDATION, "PHASES A -> C.5", "Beams, headers, cells, sketch ownership"),
            (C_ANNOTATION, "PHASE D.1", "Extract, validate, classify annotations"),
            (C_ANNOTATION, "PHASE D.1.6B -> D.1.7", "DIMENSION entities + extended classification"),
            (C_AUDIT, "PHASE D.1.7A -> D.1.7C", "Source audit, filter, integrity checks"),
            (C_FINAL, "PHASE D.1.7D", "Final dataset - READY_FOR_D2"),
            (C_FUTURE, "PHASE D.2 (planned)", "Parse & normalize reinforcement values"),
        ]

        y = self.get_y() + 4
        for i, (color, label, sub) in enumerate(boxes):
            self.flow_box(x, y, box_w, box_h, label, sub, color)
            if i < len(boxes) - 1:
                self.arrow_down(cx, y + box_h, y + box_h + 8)
                y += box_h + 8
            else:
                y += box_h

        self.set_y(y + 6)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*C_ARROW)
        self.multi_cell(
            0,
            5,
            "Version 1 is frozen. All active development is in Version2/.",
            align="C",
        )

    def phase_detail_pages(self) -> None:
        self.add_page()
        self.section_title("Phase A - Framing Beam Extraction", C_FOUNDATION)
        self._phase_block(
            [
                ("Input", "Framing plan DXF files (data/framing/)"),
                ("Process", "Extract beam marks, geometry, grid references from framing layers"),
                ("Runner", "docs/run_phases_abc.py"),
                ("Output", "phase_a/framing_beams.json, framing_validation.json"),
            ]
        )

        self.section_title("Phase B - Reinforcement Header Extraction", C_FOUNDATION)
        self._phase_block(
            [
                ("Input", "Reinforcement DXF files (data/reinforcement/)"),
                ("Process", "Extract beam reinforcement header blocks and metadata"),
                ("Runner", "docs/run_phases_abc.py"),
                ("Output", "phase_b/reinforcement_headers.json"),
            ]
        )

        self.section_title("Phase C - Beam Cell Builder", C_FOUNDATION)
        self._phase_block(
            [
                ("Input", "Framing beams + reinforcement headers"),
                ("Process", "Build beam cell grid; associate headers with framing beams"),
                ("Runner", "docs/run_phases_abc.py"),
                ("Output", "phase_c/beam_cells.json, beam_cells_validation.json"),
                ("Debug", "phase_c_debug/ - cell & sketch debug JSON + DXF overlays"),
            ]
        )

        self.section_title("Phase C.5 - Sketch Ownership", C_FOUNDATION)
        self._phase_block(
            [
                ("Input", "Beam cells, sketches, header occurrences"),
                ("Process", "Assign sketch regions to beam occurrences"),
                ("Runner", "run_sketch_ownership.py"),
                ("Output", "phase_c5/sketch_ownership.json, header_occurrences.json"),
            ]
        )

        self.add_page()
        self.section_title("Phase D.1 - Raw Annotation Extraction", C_ANNOTATION)
        self._phase_block(
            [
                ("Input", "Reinforcement DXF + sketch ownership"),
                ("Process", "Extract TEXT/MTEXT annotations inside sketch regions"),
                ("Runner", "run_phase_d1_annotations.py"),
                ("Output", "phase_d1/beam_annotations_raw.json"),
            ]
        )

        d1_subphases = [
            (
                "D.1.1 Ownership Audit",
                "Audit annotation-to-sketch ownership assignments",
                "phase_d1_1/",
            ),
            (
                "D.1.2 Spatial Validation",
                "Validate annotation positions relative to sketch geometry",
                "phase_d1_2/",
            ),
            (
                "D.1.3 Region Validation",
                "Confirm annotations fall within ownership regions",
                "phase_d1_3/",
            ),
            (
                "D.1.3.1 Boundary Leakage",
                "Detect annotations leaking across region boundaries",
                "phase_d1_3_1/",
            ),
            (
                "D.1.4 Reassignment",
                "Reassign mis-owned annotations to correct sketches",
                "phase_d1_4/ -> beam_annotations_reassigned.json",
            ),
            (
                "D.1.5 Post-Reassignment Validation",
                "Validate ownership after reassignment",
                "phase_d1_5/",
            ),
            (
                "D.1.6 Type Classification",
                "Classify: BAR, STIRRUP, ANCHORAGE, SFR, DIMENSION, NOTE",
                "phase_d1_6/ -> annotation_types.json",
            ),
        ]

        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, "D.1 Sub-phases (ownership & classification)", new_x="LMARGIN", new_y="NEXT")
        for title, desc, out in d1_subphases:
            self._bullet_item(title, desc, out)

        self.add_page()
        self.section_title("Phase D.1.6A / D.1.6B - Coverage & Entity Survey", C_AUDIT)
        self._phase_block(
            [
                ("D.1.6A", "Coverage audit - TEXT/MTEXT vs ownership (100% coverage confirmed)"),
                ("D.1.6B", "DXF entity survey - stirrups/Ld/dims live in DIMENSION entities"),
                ("Key finding", "Engineering callouts not fully captured by TEXT/MTEXT alone"),
            ]
        )

        self.section_title("Phase D.1.7 - DIMENSION Extraction", C_ANNOTATION)
        self._phase_block(
            [
                ("Input", "Reassigned annotations + ownership + DIMENSION entities"),
                ("Process", "Extract DIMENSION overrides; integrate with ownership"),
                ("Output", "phase_d1_7/beam_annotations_extended.json (186 annotations)"),
                ("Counts", "BAR=97, STIRRUP=22, ANCHORAGE=6, DIMENSION=53, SFR=7"),
            ]
        )

        self.section_title("Phase D.1.7A - Dimension Source Audit", C_AUDIT)
        self._phase_block(
            [
                ("Purpose", "Trace DIMENSION text source: override vs measurement"),
                ("Finding", "687/688/530/537 = MEASUREMENT_VALUE (AutoCAD geometry)"),
                ("Finding", "Engineering text = DIMENSION_OVERRIDE (2L-Y8@100C/C, Ld, etc.)"),
                ("Output", "phase_d1_7a/dimension_source_audit.json"),
            ]
        )

        self.section_title("Phase D.1.7B - Engineering Annotation Filter", C_ANNOTATION)
        self._phase_block(
            [
                ("Input", "Extended annotations + dimension source audit"),
                ("KEEP", "BAR, STIRRUP, ANCHORAGE, SIDE_FACE_REINF engineering text"),
                ("REJECT", "MEASUREMENT_VALUE (687, 688, 530, 537…)"),
                ("GEOMETRY QA", "500, 1900, 2150 -> separate geometry channel"),
                ("Output", "phase_d1_7b/engineering_annotations.json (132 retained)"),
            ]
        )

        self.add_page()
        self.section_title("Phase D.1.7C - Integrity Audit (read-only)", C_AUDIT)
        self._phase_block(
            [
                ("Audits", "Fragments, stirrup completeness, anchorage, SFR, duplicates, types"),
                ("Finding", "1 false rejection: 'd' fragment near Ld+10db on B18_S1"),
                ("Finding", "29 duplicate ownership (shared template geometry)"),
                ("Finding", "2 partial SFR notes (IGNORE_NOTE policy)"),
                ("Result", "Parser readiness PASS (1.52% questionable)"),
                ("Output", "phase_d1_7c/ - integrity reports + validation"),
            ]
        )

        self.section_title("Phase D.1.7D - Dataset Finalization", C_FINAL)
        self._phase_block(
            [
                ("Resolution", "'d' -> MERGED_WITH_ANCHORAGE (Ld+10db), IGNORE_FRAGMENT"),
                ("Deduplication", "50 entries removed (same text+position across sketches)"),
                ("SFR policy", "VALID_SFR=PARSE, PARTIAL_SFR=IGNORE_NOTE"),
                ("Final counts", "80 parser-ready: BAR=49, STIRRUP=22, ANCHORAGE=6, SFR=3"),
                ("Status", "READY_FOR_D2 - questionable annotations = 0"),
                ("Output", "phase_d1_7d/engineering_annotations_final.json"),
                ("Policies", "d2_parser_policy.json, sfr_parsing_policy.json"),
            ]
        )

        self.section_title("Phase D.2 - Planned Next Step", C_FUTURE)
        self._phase_block(
            [
                ("Input", "engineering_annotations_final.json + parser policies"),
                ("Goal", "Parse BAR qty/dia, stirrup spacing, anchorage, SFR bar info"),
                ("Status", "NOT STARTED - awaiting review approval"),
            ]
        )

    def data_flow_diagram(self) -> None:
        self.add_page()
        self.section_title("Key Data Flow - Annotation Pipeline", C_INPUT)

        # Horizontal flow for key artifacts
        y = self.get_y() + 6
        h = 16
        w = 38
        gap = 6
        start_x = 12
        steps = [
            (C_FOUNDATION, "sketch_\nownership", "phase_c5"),
            (C_ANNOTATION, "beam_annotations\n_raw", "phase_d1"),
            (C_ANNOTATION, "beam_annotations\n_reassigned", "phase_d1_4"),
            (C_ANNOTATION, "beam_annotations\n_extended", "phase_d1_7"),
            (C_ANNOTATION, "engineering_\nannotations", "phase_d1_7b"),
            (C_FINAL, "engineering_\nannotations_final", "phase_d1_7d"),
        ]

        for i, (color, label, folder) in enumerate(steps):
            x = start_x + i * (w + gap)
            if x + w > 200:
                break
            self.flow_box(x, y, w, h, label.replace("\n", " "), folder, color, 7)
            if i < len(steps) - 1:
                self.arrow_right(x + w, x + w + gap, y + h / 2)

        self.set_y(y + h + 12)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, "Parallel / side channels", new_x="LMARGIN", new_y="NEXT")
        channels = [
            "phase_d1_7b/geometry_dimension_annotations.json - QA dims (500, 1900, 2150)",
            "phase_d1_7b/rejected_measurement_annotations.json - AutoCAD measurements (687, etc.)",
            "phase_d1_7d/fragment_resolution_report.json - dedup log + fragment resolution",
        ]
        for ch in channels:
            self._bullet_item("", ch, "")

        self.ln(4)
        self.section_title("Validation Gates", C_AUDIT)
        gates = [
            ("A/B/C", "Framing & cell validation JSON per phase"),
            ("D.1.2–D.1.5", "Spatial, region, boundary, post-reassignment checks"),
            ("D.1.7B", "PASS - no measurement leakage into engineering set"),
            ("D.1.7C", "WARN -> integrity issues documented"),
            ("D.1.7D", "PASS - READY_FOR_D2"),
        ]
        for gate, desc in gates:
            self._bullet_item(gate, desc, "")

    def runner_reference(self) -> None:
        self.add_page()
        self.section_title("Runner Command Reference", C_INPUT)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*C_TEXT)
        cmds = [
            "cd Version2",
            "$env:PYTHONPATH=\".\"",
            "",
            "# Foundation",
            "python docs/run_phases_abc.py",
            "python run_sketch_ownership.py",
            "",
            "# Annotation pipeline",
            "python PY/run_phase_d1_annotations.py",
            "python PY/run_phase_d11_annotation_audit.py",
            "python PY/run_phase_d12_spatial_validation.py",
            "python PY/run_phase_d13_region_validation.py",
            "python PY/run_phase_d131_boundary_leakage.py",
            "python PY/run_phase_d14_reassignment.py",
            "python PY/run_phase_d15_post_reassignment_validation.py",
            "python PY/run_phase_d16_annotation_classification.py",
            "python PY/run_phase_d16a_annotation_coverage.py",
            "python PY/run_phase_d16b_entity_survey.py",
            "python PY/run_phase_d17_dimension_extraction.py",
            "python PY/run_phase_d17a_dimension_source_audit.py",
            "python run_phase_d17b_engineering_filter.py",
            "python run_phase_d17c_integrity_audit.py",
            "python run_phase_d17d_engineering_dataset_finalization.py",
        ]
        for cmd in cmds:
            if cmd == "":
                self.ln(2)
            elif cmd.startswith("#"):
                self.set_font("Helvetica", "B", 9)
                self.cell(0, 5, cmd, new_x="LMARGIN", new_y="NEXT")
                self.set_font("Helvetica", "", 9)
            else:
                self.set_fill_color(*C_LIGHT)
                self.cell(0, 5, cmd, fill=True, new_x="LMARGIN", new_y="NEXT")

    def _phase_block(self, items: list[tuple[str, str]]) -> None:
        self.set_font("Helvetica", "", 9)
        for label, text in items:
            self.set_font("Helvetica", "B", 9)
            self.cell(28, 5, f"{label}:")
            self.set_font("Helvetica", "", 9)
            self.multi_cell(0, 5, text)
            self.ln(1)

    def _bullet_item(self, title: str, desc: str, out: str) -> None:
        self.set_font("Helvetica", "B", 9)
        prefix = f"* {title}" if title else "*"
        if title:
            self.cell(0, 5, prefix, new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 8)
            self.cell(4)
            self.multi_cell(0, 4, desc)
            if out:
                self.set_font("Helvetica", "I", 7)
                self.set_text_color(*C_ARROW)
                self.cell(4)
                self.cell(0, 4, f"-> {out}", new_x="LMARGIN", new_y="NEXT")
                self.set_text_color(*C_TEXT)
        else:
            self.set_font("Helvetica", "", 8)
            self.multi_cell(0, 4, f"{prefix} {desc}")
        self.ln(1)


def main() -> None:
    pdf = WorkflowPDF()
    pdf.title_page()
    pdf.overview_flowchart()
    pdf.phase_detail_pages()
    pdf.data_flow_diagram()
    pdf.runner_reference()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_PATH))
    print(f"Generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
