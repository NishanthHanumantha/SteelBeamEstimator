"""Generate Pipeline_Flowchart.pdf, .md, and .html from shared phase data."""

from pathlib import Path

from fpdf import FPDF

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
OUTPUT_PDF = DOCS_DIR / "Pipeline_Flowchart.pdf"
OUTPUT_MD = DOCS_DIR / "Pipeline_Flowchart.md"
OUTPUT_HTML = DOCS_DIR / "Pipeline_Flowchart.html"

C_BG_BOX = (33, 38, 45)
C_INPUT = (49, 109, 158)
C_FINAL = (192, 57, 43)
C_PLANNED = (61, 68, 77)
C_ARROW = (88, 166, 255)
C_WHITE = (255, 255, 255)
C_MUTED = (139, 148, 158)
C_PAGE = (13, 17, 23)
C_HEADER = (46, 125, 50)

# Page 1 — short labels only
SUMMARY_STEPS = [
    ("input", "DXF Input", "(Framing + Reinforcement)"),
    ("done", "Phase A", "Framing Beams"),
    ("done", "Phase B", "Reinforcement Headers"),
    ("done", "Phase C", "Beam Cells"),
    ("done", "Phase C.5", "Sketch Ownership"),
    ("done", "Phase D.1", "Raw Annotations"),
    ("done", "D.1.1 - D.1.5", "Ownership & Validation"),
    ("done", "D.1.6", "Type Classification"),
    ("done", "D.1.6A / B", "Coverage & Entity Survey"),
    ("done", "D.1.7", "DIMENSION Extraction"),
    ("done", "D.1.7A", "Source Audit"),
    ("done", "D.1.7B", "Engineering Filter (132)"),
    ("done", "D.1.7C", "Integrity Audit"),
    ("done", "D.1.7D", "80 parser-ready"),
    ("done", "D.1.7E", "SFR Ownership Validator"),
    ("final", "Phase D.2", "Parsing - READY_FOR_PHASE_E"),
]

# Page 2 — same phases as page 1, each with brief process line
DETAIL_STEPS = [
    (
        "input",
        "DXF Input",
        "Framing plan and reinforcement drawing DXF files",
    ),
    (
        "done",
        "Phase A - Framing Beams",
        "Extract beam marks, geometry, grid references from framing layers",
    ),
    (
        "done",
        "Phase B - Reinforcement Headers",
        "Extract beam reinforcement header blocks and metadata",
    ),
    (
        "done",
        "Phase C - Beam Cells",
        "Build beam cell grid; associate headers with framing beams",
    ),
    (
        "done",
        "Phase C.5 - Sketch Ownership",
        "Assign sketch regions to beam occurrences",
    ),
    (
        "done",
        "Phase D.1 - Raw Annotations",
        "Extract TEXT/MTEXT annotations inside sketch regions",
    ),
    (
        "done",
        "D.1.1 - D.1.5 - Ownership & Validation",
        "Audit ownership, spatial/region checks, boundary leakage, reassignment",
    ),
    (
        "done",
        "D.1.6 - Type Classification",
        "Classify BAR, STIRRUP, ANCHORAGE, SFR, DIMENSION, NOTE",
    ),
    (
        "done",
        "D.1.6A / B - Coverage & Entity Survey",
        "Coverage audit; survey DIMENSION entities for engineering text",
    ),
    (
        "done",
        "D.1.7 - DIMENSION Extraction",
        "Extract DIMENSION overrides; integrate with ownership (186 total)",
    ),
    (
        "done",
        "D.1.7A - Source Audit",
        "Trace DIMENSION source: engineering override vs measurement value",
    ),
    (
        "done",
        "D.1.7B - Engineering Filter",
        "Keep engineering text; reject AutoCAD measurements (132 retained)",
    ),
    (
        "done",
        "D.1.7C - Integrity Audit",
        "Audit fragments, stirrups, anchorage, SFR, duplicates, readiness",
    ),
    (
        "done",
        "D.1.7D - Final Dataset",
        "Deduplicate, resolve fragments; 80 parser-ready annotations",
    ),
    (
        "done",
        "D.1.7E - SFR Ownership Validator",
        "Geometry-based SIDE_FACE_REINF ownership scoring before parsing",
    ),
    (
        "final",
        "Phase D.2 - Parsing",
        "Parse bar qty/dia, stirrup spacing, anchorage, validated SFR",
    ),
]


def _color(kind: str) -> tuple[int, int, int]:
    if kind == "input":
        return C_INPUT
    if kind == "final":
        return C_FINAL
    if kind == "planned":
        return C_PLANNED
    return C_BG_BOX


class FlowchartPDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_MUTED)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def paint_page_bg(self):
        self.set_fill_color(*C_PAGE)
        self.rect(0, 0, 210, 297, style="F")

    def draw_arrow(self, cx: float, y1: float, y2: float) -> None:
        self.set_draw_color(*C_ARROW)
        self.set_line_width(0.35)
        self.line(cx, y1, cx, y2)
        self.line(cx, y2, cx - 2, y2 - 2)
        self.line(cx, y2, cx + 2, y2 - 2)


def _draw_summary_page(pdf: FlowchartPDF) -> None:
    pdf.add_page()
    pdf.paint_page_bg()

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(230, 237, 243)
    pdf.cell(
        0, 8, "Quick visual summary (current state)", align="C",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(
        0, 5, "Steel Beam Estimator V2 - full pipeline through D.2",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(6)

    box_w = 125
    box_h = 13
    cx = 105
    x = cx - box_w / 2
    y = pdf.get_y()

    for i, (kind, title, sub) in enumerate(SUMMARY_STEPS):
        color = _color(kind)
        pdf.set_fill_color(*color)
        pdf.set_draw_color(72, 79, 88)
        pdf.rect(x, y, box_w, box_h, style="FD")

        pdf.set_xy(x, y + 2.5)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*C_WHITE)
        pdf.cell(box_w, 4, title, align="C")

        pdf.set_xy(x, y + 6.5)
        pdf.set_font("Helvetica", "", 6.5)
        if kind == "done":
            pdf.set_text_color(*C_MUTED)
        else:
            pdf.set_text_color(255, 255, 255)
        pdf.cell(box_w, 4, sub, align="C")

        if i < len(SUMMARY_STEPS) - 1:
            pdf.draw_arrow(cx, y + box_h, y + box_h + 5)
            y += box_h + 5
        else:
            y += box_h


def _process_box_height(pdf: FlowchartPDF, process: str, box_w: float) -> float:
    pdf.set_font("Helvetica", "", 6.5)
    # Estimate wrapped lines for box width
    chars_per_line = int(box_w / 1.8)
    lines = max(1, (len(process) + chars_per_line - 1) // chars_per_line)
    return 7.5 + lines * 3.0


def _draw_detail_flow(pdf: FlowchartPDF) -> None:
    pdf.add_page()
    pdf.paint_page_bg()

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(230, 237, 243)
    pdf.cell(
        0, 8, "Pipeline flowchart with process summary", align="C",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(
        0, 5, "Each phase: name and brief process description",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)

    box_w = 170
    cx = 105
    x = cx - box_w / 2
    arrow_gap = 3
    bottom_margin = 16

    for i, (kind, title, process) in enumerate(DETAIL_STEPS):
        box_h = _process_box_height(pdf, process, box_w)
        if pdf.get_y() + box_h + arrow_gap > 297 - bottom_margin:
            pdf.add_page()
            pdf.paint_page_bg()
            pdf.ln(2)

        y = pdf.get_y()
        color = _color(kind)
        pdf.set_fill_color(*color)
        pdf.set_draw_color(72, 79, 88)
        pdf.rect(x, y, box_w, box_h, style="FD")

        pdf.set_xy(x + 3, y + 2.5)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*C_WHITE)
        pdf.multi_cell(box_w - 6, 3.5, title, align="C")

        pdf.set_xy(x + 4, pdf.get_y() + 0.5)
        pdf.set_font("Helvetica", "", 6.5)
        if kind == "done":
            pdf.set_text_color(*C_MUTED)
        else:
            pdf.set_text_color(240, 240, 240)
        pdf.multi_cell(box_w - 8, 3.2, process, align="C")

        if i < len(DETAIL_STEPS) - 1:
            pdf.draw_arrow(cx, y + box_h, y + box_h + arrow_gap)
            pdf.set_y(y + box_h + arrow_gap)
        else:
            pdf.set_y(y + box_h + 2)


def _mermaid_summary() -> str:
    lines = ["flowchart TB"]
    ids = []
    for i, (kind, title, sub) in enumerate(SUMMARY_STEPS):
        nid = f"n{i}"
        ids.append(nid)
        label = f"{title}<br/>{sub}".replace('"', "'")
        lines.append(f"    {nid}[\"{label}\"]")
    for i in range(len(ids) - 1):
        lines.append(f"    {ids[i]} --> {ids[i + 1]}")
    lines.append("    classDef input fill:#316d9e,color:#fff")
    lines.append("    classDef final fill:#c0392b,color:#fff")
    lines.append("    classDef planned fill:#6e7681,color:#fff")
    lines.append("    classDef done fill:#21262d,color:#e6edf3")
    for i, (kind, _, _) in enumerate(SUMMARY_STEPS):
        cls = kind if kind in ("input", "final", "planned") else "done"
        lines.append(f"    class n{i} {cls}")
    return "\n".join(lines)


def _write_markdown() -> None:
    lines = [
        "# Steel Beam Estimator — Pipeline Flowchart",
        "",
        "**Version 2** · full pipeline through D.2 · `READY_FOR_PHASE_E`",
        "",
        "Open in Cursor: **Markdown Preview** (`Ctrl+Shift+V` or preview icon).",
        "",
        "Also available: `Pipeline_Flowchart.pdf` · `Pipeline_Flowchart.html`",
        "",
        "---",
        "",
        "## Page 1 — Quick visual summary",
        "",
        "```mermaid",
        _mermaid_summary(),
        "```",
        "",
        "---",
        "",
        "## Page 2 — Flowchart with process descriptions",
        "",
    ]
    for kind, title, process in DETAIL_STEPS:
        badge = {
            "input": "INPUT",
            "final": "FINAL",
            "planned": "PLANNED",
            "done": "DONE",
        }.get(kind, "DONE")
        lines.append(f"### {title}")
        lines.append(f"**{badge}** · {process}")
        lines.append("")
        lines.append("↓")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Regenerate all formats: `python scripts/generate_flowchart_pdf.py`*")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {OUTPUT_MD}")


def _write_html() -> None:
    summary_steps_js = [
        {"kind": k, "title": t, "detail": d} for k, t, d in SUMMARY_STEPS
    ]
    detail_steps_js = [
        {"kind": k, "title": t, "detail": p} for k, t, p in DETAIL_STEPS
    ]

    import json

    summary_json = json.dumps(summary_steps_js)
    detail_json = json.dumps(detail_steps_js)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Pipeline Flowchart — Steel Beam Estimator</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      padding: 2rem 1rem 3rem;
    }}
    .page {{ max-width: 520px; margin: 0 auto 3rem; }}
    h1 {{ font-size: 1.15rem; margin-bottom: 0.25rem; }}
    h2 {{
      font-size: 0.95rem;
      color: #8b949e;
      margin: 2.5rem 0 1.25rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid #30363d;
    }}
    .subtitle {{ font-size: 0.8rem; color: #8b949e; margin-bottom: 1.5rem; }}
    .flow {{ display: flex; flex-direction: column; align-items: center; }}
    .node {{
      width: 100%; max-width: 420px;
      padding: 0.85rem 1.25rem;
      border: 1px solid #484f58;
      border-radius: 4px;
      background: #21262d;
      text-align: center;
    }}
    .node .title {{ font-size: 0.92rem; font-weight: 600; color: #f0f6fc; }}
    .node .detail {{ font-size: 0.78rem; color: #8b949e; margin-top: 0.35rem; line-height: 1.4; }}
    .node.input {{ background: #316d9e; border-color: #4a8bc4; }}
    .node.input .title, .node.input .detail {{ color: #fff; }}
    .node.input .detail {{ opacity: 0.9; }}
    .node.final {{ background: #c0392b; border-color: #e74c3c; }}
    .node.final .title, .node.final .detail {{ color: #fff; }}
    .node.planned {{ background: #3d444d; border-color: #6e7681; }}
    .connector {{ display: flex; flex-direction: column; align-items: center; height: 26px; }}
    .connector .line {{ width: 2px; height: 16px; background: #58a6ff; }}
    .connector .head {{
      width: 0; height: 0;
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 7px solid #58a6ff;
    }}
    footer {{ text-align: center; font-size: 0.7rem; color: #484f58; margin-top: 2rem; }}
  </style>
</head>
<body>
  <div class="page">
    <h1>Steel Beam Estimator — Pipeline Flowchart</h1>
    <p class="subtitle">Version 2 · Cursor-friendly HTML (same content as Pipeline_Flowchart.pdf)</p>
    <h2>Page 1 — Quick visual summary</h2>
    <div class="flow" id="summary"></div>
  </div>
  <div class="page">
    <h2>Page 2 — With process descriptions</h2>
    <div class="flow" id="detail"></div>
    <footer>Version2/docs/Pipeline_Flowchart.html</footer>
  </div>
  <script>
    function renderFlow(containerId, steps) {{
      const el = document.getElementById(containerId);
      steps.forEach((step, i) => {{
        const node = document.createElement("div");
        node.className = "node" + (step.kind === "input" ? " input" : step.kind === "final" ? " final" : step.kind === "planned" ? " planned" : "");
        node.innerHTML = `<div class="title">${{step.title}}</div><div class="detail">${{step.detail}}</div>`;
        el.appendChild(node);
        if (i < steps.length - 1) {{
          const conn = document.createElement("div");
          conn.className = "connector";
          conn.innerHTML = '<div class="line"></div><div class="head"></div>';
          el.appendChild(conn);
        }}
      }});
    }}
    renderFlow("summary", {summary_json});
    renderFlow("detail", {detail_json});
  </script>
</body>
</html>
"""
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated: {OUTPUT_HTML}")


def main() -> None:
    pdf = FlowchartPDF()
    pdf.set_auto_page_break(auto=False, margin=12)

    _draw_summary_page(pdf)
    _draw_detail_flow(pdf)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT_PDF))
    print(f"Generated: {OUTPUT_PDF} ({pdf.page_no()} pages)")

    _write_markdown()
    _write_html()


if __name__ == "__main__":
    main()
