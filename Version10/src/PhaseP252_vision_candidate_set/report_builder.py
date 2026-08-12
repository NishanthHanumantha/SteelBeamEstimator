"""Reports for P2.5.2."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _csv(path: Path, rows: List[Dict[str, Any]]) -> None:
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
    selections: Sequence[Dict[str, Any]],
    manifests: Sequence[Dict[str, Any]],
    metrics: Dict[str, Any],
    golden: Dict[str, Any],
    regression: Dict[str, Any],
    determinism: Dict[str, Any],
    unit_tests: Dict[str, Any],
    decision: str,
) -> None:
    reports = out_root / "reports"
    manifests_dir = out_root / "manifests"
    metrics_dir = out_root / "metrics"
    for d in (reports, manifests_dir, metrics_dir, out_root / "regression", out_root / "determinism"):
        d.mkdir(parents=True, exist_ok=True)

    _dump(manifests_dir / "VisionCandidateManifest.json", list(manifests))
    rows = []
    for m in manifests:
        rows.append(
            {
                "candidate_id": m.get("candidate_id"),
                "beam_id": m.get("beam_id"),
                "annotation_id": m.get("annotation_id"),
                "raw_text": m.get("raw_text"),
                "outcome": m.get("outcome"),
                "priority": m.get("candidate_priority"),
                "reasons": "|".join(m.get("candidate_reason_codes") or []),
                "quantity_status": m.get("quantity_status"),
                "crop_qa_status": m.get("crop_qa_status"),
                "crop_w_mm": (m.get("crop_dimensions_mm") or {}).get("w_mm"),
                "crop_h_mm": (m.get("crop_dimensions_mm") or {}).get("h_mm"),
                "local_crop": m.get("crop_local_path"),
                "beam_context_crop": m.get("crop_beam_context_path"),
                "vision_status": m.get("future_vision_status"),
                "norm_hint": m.get("candidate_normalization_hint"),
            }
        )
    _csv(manifests_dir / "VisionCandidateMatrix.csv", rows)

    # classification summary of all selections
    class_rows = []
    for s in selections:
        class_rows.append(
            {
                "candidate_id": s.get("candidate_id"),
                "beam_id": s.get("beam_id"),
                "annotation_id": s.get("annotation_id"),
                "raw_text": s.get("raw_text"),
                "outcome": s.get("outcome"),
                "priority": s.get("candidate_priority"),
                "reasons": "|".join(s.get("candidate_reason_codes") or []),
                "quantity_status": (s.get("deterministic_intent") or {}).get(
                    "quantity_status"
                ),
            }
        )
    _csv(reports / "CandidateClassification.csv", class_rows)

    # Review index
    idx = ["# Candidate Review Index — P2.5.2", ""]
    for m in sorted(manifests, key=lambda x: (x.get("candidate_priority") or "P9", x.get("candidate_id") or "")):
        idx.append(f"## {m.get('candidate_id')}")
        idx.append(f"- beam: `{m.get('beam_id')}`")
        idx.append(f"- annotation: `{m.get('annotation_id')}`")
        idx.append(f"- raw text: `{m.get('raw_text')}`")
        idx.append(f"- outcome/priority: `{m.get('outcome')}` / `{m.get('candidate_priority')}`")
        idx.append(f"- reasons: `{m.get('candidate_reason_codes')}`")
        idx.append(f"- local crop: `{m.get('crop_local_path')}`")
        idx.append(f"- beam context crop: `{m.get('crop_beam_context_path')}`")
        idx.append(f"- crop dims mm: `{m.get('crop_dimensions_mm')}`")
        idx.append(f"- QA: `{m.get('crop_qa_status')}`")
        idx.append("")
    _md(reports / "CandidateReviewIndex.md", "\n".join(idx))

    _md(
        reports / "CandidateClassification.md",
        "\n".join(
            [
                "# Candidate Classification — P2.5.2",
                "",
                "Rules:",
                "- EXPLICIT / SPACING_BASED / COMPOSITE → EXCLUDED (VISION_NOT_REQUIRED)",
                "- OCR-corrupted unresolved stirrups → VISION_CANDIDATE P0 (OCR_CORRUPTION)",
                "- Other UNRESOLVED reinforcement → VISION_CANDIDATE P1",
                "- Ld / Ld+… → DEFERRED (DEFER_ENGINEERING_RULE)",
                "- SFR descriptive notes → VISION_CANDIDATE P2 (SEMANTIC_CONTEXT_REQUIRED)",
                "",
                f"Metrics: `{json.dumps(metrics, indent=2)}`",
                "",
            ]
        ),
    )

    qa_lines = [
        "# Crop QA Report — P2.5.2",
        "",
        f"- QA PASS rate: `{metrics.get('CROP_QA_PASS_RATE')}%`",
        f"- QA PARTIAL rate: `{metrics.get('CROP_QA_PARTIAL_RATE')}%`",
        f"- QA FAIL rate: `{metrics.get('CROP_QA_FAIL_RATE')}%`",
        f"- Extreme crops: `{metrics.get('EXTREME_CROP_COUNT')}`",
        f"- Rejected evidence included: `{metrics.get('REJECTED_EVIDENCE_INCLUDED_COUNT')}`",
        "",
    ]
    for m in manifests:
        qa = m.get("crop_qa") or {}
        qa_lines.append(
            f"- `{m.get('candidate_id')}`: {m.get('crop_qa_status')} "
            f"flags={qa.get('flags')} hard={qa.get('hard_fails')}"
        )
    _md(reports / "CropQAReport.md", "\n".join(qa_lines))

    _dump(metrics_dir / "metrics.json", metrics)
    _dump(out_root / "regression" / "RegressionReport.json", regression)
    _dump(out_root / "determinism" / "DeterminismReport.json", determinism)
    _dump(out_root / "golden_results.json", golden)

    rc = metrics.get("reason_code_counts") or {}
    summary = [
        "# P252 SUMMARY — Vision Candidate Set + Visual Evidence",
        "",
        f"- MODEL_VERSION: `{meta.get('model_version')}`",
        f"- Decision: **{decision}**",
        f"- Unit tests: `{unit_tests.get('passed')}/{unit_tests.get('total')}`",
        f"- Determinism: `{determinism.get('determinism_status')}`",
        f"- Regression unchanged: `{regression.get('unchanged')}`",
        f"- Claude: NONE",
        f"- Engineering changes: NONE",
        "",
        "## Candidate selection",
        "",
        f"- Eligible intents: `{metrics.get('TOTAL_ELIGIBLE_INTENTS')}`",
        f"- Unresolved: `{metrics.get('UNRESOLVED_COUNT')}`",
        f"- OCR-corrupted: `{metrics.get('OCR_CORRUPTED_COUNT')}`",
        f"- Vision candidates: `{metrics.get('VISION_CANDIDATE_COUNT')}`",
        f"- Deferred: `{metrics.get('DEFERRED_COUNT')}`",
        f"- Excluded: `{metrics.get('EXCLUDED_COUNT')}`",
        f"- P0/P1/P2/P3: `{metrics.get('P0_COUNT')}`/`{metrics.get('P1_COUNT')}`/`{metrics.get('P2_COUNT')}`/`{metrics.get('P3_COUNT')}`",
        "",
        "## Visual evidence quality",
        "",
        f"- Local crops: `{metrics.get('CANDIDATES_WITH_LOCAL_CROP')}`",
        f"- Beam context crops: `{metrics.get('CANDIDATES_WITH_BEAM_CONTEXT_CROP')}`",
        f"- Crop QA PASS/PARTIAL/FAIL rates: "
        f"`{metrics.get('CROP_QA_PASS_RATE')}`/`{metrics.get('CROP_QA_PARTIAL_RATE')}`/`{metrics.get('CROP_QA_FAIL_RATE')}`",
        f"- Extreme crops: `{metrics.get('EXTREME_CROP_COUNT')}`",
        "",
        "## Future Vision work",
        "",
        "- All candidates have `future_vision_status = PENDING`",
        "- No Claude calls in P2.5.2",
        "- P2.5.3 may send local + beam-context crops with structured metadata",
        "",
        "## Reason codes",
        "",
        f"```json\n{json.dumps(rc, indent=2)}\n```",
        "",
        "## Golden",
        "",
        f"```json\n{json.dumps(golden, indent=2, default=str)}\n```",
        "",
    ]
    _md(reports / "P252_SUMMARY.md", "\n".join(summary))
    _md(out_root / "ExecutiveSummary.md", "\n".join(summary))
