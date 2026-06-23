"""Generate Version2_Workflow.pdf from structured content."""

from pathlib import Path

from fpdf import FPDF

OUTPUT = Path(__file__).parent / "Version2_Workflow.pdf"


class WorkflowPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Steel Beam Estimator - Version 2 Workflow", align="R")
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def section_title(self, title: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 60, 120)
        self.ln(4)
        self.multi_cell(0, 8, title)
        self.ln(2)

    def sub_title(self, title: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(50, 50, 50)
        self.ln(2)
        self.multi_cell(0, 6, title)
        self.ln(1)

    def body(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5, f"  - {text}")

    def table_row(self, cols: list[str], widths: list[int], bold: bool = False) -> None:
        self.set_x(self.l_margin)
        style = "B" if bold else ""
        self.set_font("Helvetica", style, 9)
        for col, width in zip(cols, widths):
            self.cell(width, 6, col, border=1)
        self.ln()


def build_pdf() -> None:
    pdf = WorkflowPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(0, 12, "Steel Beam Estimator", ln=True)
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 8, "Version 2 - Pipeline Workflow Document", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, "Phases A through C.5.2 | June 2026 | Pre-Phase D", ln=True)
    pdf.ln(6)

    pdf.section_title("1. Executive Summary")
    pdf.body(
        "Version 2 extracts structural beam data from two AutoCAD DXF sources: "
        "the framing plan (beam marks and centreline geometry) and the reinforcement "
        "details sheet (section headers, grid layout, and detail sketches). "
        "The pipeline runs from framing extraction (Phase A) through reinforcement headers "
        "(Phase B), spatial grid cells (Phase C), sketch detection, and sketch-to-header "
        "ownership validation (Phases C.5 through C.5.2)."
    )
    pdf.body("Version 1 is frozen. All development occurs only inside Version2/.")

    pdf.sub_title("Current sample drawing results")
    widths = [55, 120]
    pdf.table_row(["Metric", "Value"], widths, bold=True)
    for metric, value in [
        ("Unique beams (framing)", "18 (B1-B18)"),
        ("Header occurrences", "24"),
        ("Sketches detected", "38"),
        ("Ownership assignments", "38"),
        ("Ownership status", "PASS"),
        ("Audit status", "PASS_WITH_WARNINGS"),
    ]:
        pdf.table_row([metric, value], widths)
    pdf.ln(4)

    pdf.section_title("2. Input Data")
    widths = [50, 70, 70]
    pdf.table_row(["File", "Path", "Purpose"], widths, bold=True)
    pdf.table_row(
        ["Framing plan", "data/framing/Beam_FramingPlan.dxf", "Labels + STR-BEAM geometry"],
        widths,
    )
    pdf.table_row(
        ["Reinforcement", "data/reinforcement/Beam_ReinforcementDetails.dxf", "SEC TEXT + details"],
        widths,
    )
    pdf.ln(4)

    pdf.section_title("3. Pipeline Phases")

    phases = [
        (
            "Phase A - Framing Plan Extraction",
            "Match B{n}(WxD) labels to STR-BEAM centreline segments. "
            "Flatten INSERT blocks. Outputs: framing_beams.json (18 beams), framing_validation.json.",
            "src/framing/framing_beam_extractor.py, src/parser/dxf_flattener.py",
        ),
        (
            "Phase B - Reinforcement Header Extraction",
            "Detect section titles on SEC TEXT layer. 24 raw occurrences; 18 unique marks. "
            "Duplicate marks (B3, B12, B13, B18) = multiple detail sketches, not duplicate beams.",
            "src/reinforcement/header_extractor.py",
        ),
        (
            "Phase C - Header Grid Segmentation",
            "Cluster headers into 4 rows by Y; assign column ownership cells with midpoint boundaries. "
            "Outputs: beam_cells.json, beam_cells_validation.json.",
            "src/grid/beam_cell_builder.py",
        ),
        (
            "Sketch Debug Detection",
            "Detect reinforcement sketches per header occurrence (1 beam = N sketches). "
            "38 sketches across 18 beams. Outputs: beam_sketches_debug.json, debug DXF.",
            "src/grid/beam_sketch_debug_detector.py, src/geometry/geometry_graph.py",
        ),
        (
            "Phase C.5 - Sketch Ownership",
            "Assign each sketch to nearest same-mark header occurrence by centroid distance. "
            "Outputs: header_occurrences.json, sketch_ownership.json, validation, debug DXF.",
            "src/grid/sketch_ownership_builder.py, header_occurrence_exporter.py",
        ),
        (
            "Phase C.5.1 - Audit Metrics",
            "Add distance_mm and confidence (HIGH/MEDIUM/LOW) per owned sketch. No assignment changes.",
            "src/grid/sketch_ownership_auditor.py",
        ),
        (
            "Phase C.5.2 - Audit Refinement",
            "Separate ownership errors from layout warnings. Long distance (>10m) = WARNING only. "
            "Ownership PASS; audit PASS_WITH_WARNINGS (B17_S2 at 12365 mm).",
            "src/grid/sketch_ownership_validator.py",
        ),
    ]
    for title, desc, modules in phases:
        pdf.sub_title(title)
        pdf.body(desc)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 4, f"Modules: {modules}")
        pdf.ln(2)

    pdf.add_page()
    pdf.section_title("4. Key Design Concepts")
    pdf.bullet("1 beam = N sketches: multiple header labels for one mark are intentional.")
    pdf.bullet("Occurrence-level ownership: B3_H1 and B3_H2 own different sketches.")
    pdf.bullet("Large header-to-sketch distance is normal (sections drawn below titles).")
    pdf.bullet("Debug DXF overlays on dedicated layers for AutoCAD visual verification.")
    pdf.bullet("Each phase produces validated JSON before the next phase runs.")
    pdf.ln(4)

    pdf.section_title("5. CLI Commands")
    pdf.body("Run from Version2/ with: $env:PYTHONPATH=\".\"")
    widths = [55, 40, 85]
    pdf.table_row(["Script", "Phases", "Key outputs"], widths, bold=True)
    for script, phase, outputs in [
        ("docs/run_phases_abc.py", "A, B, C", "framing, headers, cells"),
        ("docs/run_beam_cells_debug.py", "C debug", "beam_cells_debug.*"),
        ("run_beam_sketches_debug.py", "Sketches", "beam_sketches_debug.*"),
        ("run_sketch_ownership.py", "C.5-C.5.2", "ownership, validation, DXF"),
    ]:
        pdf.table_row([script, phase, outputs], widths)
    pdf.ln(4)

    pdf.section_title("6. Output Files (data/output/)")
    pdf.sub_title("JSON artifacts")
    for f in [
        "framing_beams.json, framing_validation.json",
        "reinforcement_headers.json, reinforcement_header_validation.json",
        "beam_cells.json, beam_cells_validation.json",
        "beam_sketches_debug.json, beam_sketches_debug_validation.json",
        "header_occurrences.json, sketch_ownership.json",
        "sketch_ownership_validation.json",
    ]:
        pdf.bullet(f)
    pdf.sub_title("DXF debug overlays")
    for f in [
        "beam_cells_debug.dxf - DEBUG_BEAM_CELLS",
        "beam_sketches_debug.dxf - sketch bboxes",
        "sketch_ownership_debug.dxf - DEBUG_SKETCH_OWNERSHIP (leaders, distances, WARNING)",
    ]:
        pdf.bullet(f)
    pdf.ln(4)

    pdf.section_title("7. Distance Distribution (C.5.2 audit)")
    widths = [60, 40]
    pdf.table_row(["Distance band", "Count"], widths, bold=True)
    for band, count in [
        ("0-1500 mm", "0"),
        ("1500-4000 mm", "16"),
        ("4000-8000 mm", "11"),
        ("8000+ mm", "11"),
    ]:
        pdf.table_row([band, count], widths)
    pdf.ln(4)

    pdf.section_title("8. Not Yet Implemented (Phase D+)")
    pdf.bullet("Phase D - annotation ownership within sketches")
    pdf.bullet("Reinforcement steel quantity parsing")
    pdf.bullet("Cross-linking framing spans to reinforcement details")
    pdf.bullet("Estimator / billing calculations")
    pdf.body("Next step: Phase D after review and approval of ownership validation.")

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Document version 1.0 | Generated from Version2 pipeline state", ln=True)

    pdf.output(OUTPUT)
    print(f"Wrote {OUTPUT.resolve()}")


if __name__ == "__main__":
    build_pdf()
