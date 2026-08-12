"""Reports for P2.5.1 Quantity Intent Schema."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .models import QuantityIntent


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_reports(
    *,
    out_root: Path,
    meta: Dict[str, Any],
    intents: Sequence[QuantityIntent],
    metrics: Dict[str, Any],
    validation_summary: Dict[str, Any],
    golden: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    unit_tests: Dict[str, Any],
    decision: str,
    beam_count: int,
    input_stats: Dict[str, Any],
) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    rows = [i.to_row() for i in intents]
    _write_csv(out_root / "quantity_intent_matrix.csv", rows)
    _dump(out_root / "quantity_intent_matrix.json", [i.to_dict() for i in intents])
    _dump(out_root / "metrics.json", metrics)
    _dump(out_root / "validation_results.json", validation_summary)
    _dump(out_root / "regression.json", regression)
    _dump(out_root / "determinism.json", determinism)
    _dump(out_root / "golden_results.json", golden)

    unresolved = metrics.get("top_unresolved_patterns") or []
    lines = [
        "# P2.5.1 Quantity Intent Report",
        "",
        f"- MODEL_VERSION: `{meta.get('model_version')}`",
        f"- Decision: **{decision}**",
        f"- Fourth Set beams processed: `{beam_count}`",
        f"- Claude: NONE",
        f"- Engineering changes: NONE",
        "",
        "## Input",
        "",
        f"- Accepted annotations (eligible): `{input_stats.get('accepted_annotations')}`",
        f"- Accepted leader chains: `{input_stats.get('accepted_chains')}`",
        f"- Accepted OWN geometry items: `{input_stats.get('owned_geometry')}`",
        f"- Rejected evidence excluded: YES (package-level)",
        "",
        "## Quantity Intent Results",
        "",
        f"1. Total accepted annotations: `{metrics.get('eligible_annotations')}`",
        f"2. Quantity intents generated: `{metrics.get('quantity_intents_generated')}`",
        f"3. Explicit quantity intents: `{metrics.get('explicit_quantity')}`",
        f"4. Composite intents: `{metrics.get('composite_quantity')}`",
        f"5. Spacing-based intents: `{metrics.get('spacing_stirrup')}`",
        f"6. Unresolved intents: `{metrics.get('unresolved')}`",
        f"7. Invalid intents: `{metrics.get('invalid')}`",
        f"8. Role distribution: `{metrics.get('role_distribution')}`",
        f"9. Diameter distribution: `{metrics.get('diameter_distribution')}`",
        f"10. Quantity distribution: `{metrics.get('quantity_distribution')}`",
        f"11. Top unresolved patterns: `{unresolved}`",
        f"12. Evidence linkage / provenance coverage: `{metrics.get('PROVENANCE_COVERAGE')}%`",
        f"13. Provenance coverage: `{metrics.get('PROVENANCE_COVERAGE')}%`",
        f"14. Determinism: `{determinism.get('determinism_status')}`",
        f"15. Regression unchanged: `{regression.get('unchanged')}`",
        "",
        "## Metrics",
        "",
        f"- QUANTITY_INTENT_COVERAGE: `{metrics.get('QUANTITY_INTENT_COVERAGE')}%`",
        f"- EXPLICIT_QUANTITY_RATE: `{metrics.get('EXPLICIT_QUANTITY_RATE')}%`",
        f"- UNRESOLVED_QUANTITY_RATE: `{metrics.get('UNRESOLVED_QUANTITY_RATE')}%`",
        f"- PROVENANCE_COVERAGE: `{metrics.get('PROVENANCE_COVERAGE')}%`",
        f"- VALIDATION_PASS_RATE: `{metrics.get('VALIDATION_PASS_RATE')}%`",
        f"- COMPOSITE_RATE: `{metrics.get('COMPOSITE_RATE')}%`",
        f"- SPACING_BASED_RATE: `{metrics.get('SPACING_BASED_RATE')}%`",
        "",
        "## Golden",
        "",
        f"```json\n{json.dumps(golden, indent=2, default=str)}\n```",
        "",
        "## Note",
        "",
        "These metrics measure schema coverage and parsing structure — not quantity accuracy.",
        "",
    ]
    _md(out_root / "P2.5.1_QuantityIntent_Report.md", "\n".join(lines))

    # Executive-style summary for Cursor response support
    _md(
        out_root / "ExecutiveSummary.md",
        "\n".join(
            [
                "# Executive Summary — P2.5.1 Quantity Intent Schema",
                "",
                f"- MODEL_VERSION: `{meta.get('model_version')}`",
                f"- PASS decision: **{decision}**",
                f"- Unit tests: `{unit_tests.get('passed')}/{unit_tests.get('total')}`",
                f"- Determinism: `{determinism.get('determinism_status')}`",
                f"- Regression unchanged: `{regression.get('unchanged')}`",
                f"- Claude: NONE",
                f"- Engineering changes: NONE",
                "",
                f"- Intents: `{metrics.get('quantity_intents_generated')}` / eligible `{metrics.get('eligible_annotations')}`",
                f"- Explicit: `{metrics.get('explicit_quantity')}` Spacing: `{metrics.get('spacing_stirrup')}` Unresolved: `{metrics.get('unresolved')}`",
                f"- QUANTITY_INTENT_COVERAGE: `{metrics.get('QUANTITY_INTENT_COVERAGE')}%`",
                f"- VALIDATION_PASS_RATE: `{metrics.get('VALIDATION_PASS_RATE')}%`",
                "",
            ]
        ),
    )
