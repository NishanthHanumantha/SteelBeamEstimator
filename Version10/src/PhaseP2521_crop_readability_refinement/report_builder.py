"""Status / inspection reports for P2.5.2.1."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    CLAUDE,
    ENGINEERING_CHANGES,
    MODEL_VERSION,
    PHASE_ID,
    PHASE_NAME,
    READABILITY_FAIL,
    READABILITY_PARTIAL,
    READABILITY_PASS,
    READABILITY_REVIEW_REQUIRED,
)

MODEL_VERSION_LOCAL = MODEL_VERSION


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_reports(
    *,
    out_root: Path,
    summary: Dict[str, Any],
) -> Dict[str, str]:
    out_root = Path(out_root)
    reports_dir = out_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    counts = summary.get("counts") or {}
    gold = summary.get("golden") or {}
    det = summary.get("determinism") or {}
    reg = summary.get("regression") or {}
    inspection = summary.get("visual_inspection") or {}
    review = summary.get("manual_review") or []

    status_md = f"""# P2.5.2.1 STATUS

MODEL_VERSION: {MODEL_VERSION}
PASS / FAIL: {summary.get('pass_fail')}

## Candidate counts
- total active: {counts.get('total_active')}
- refined successfully: {counts.get('refined_successfully')}
- readability PASS: {counts.get('readability_pass')}
- readability PARTIAL: {counts.get('readability_partial')}
- readability FAIL: {counts.get('readability_fail')}
- readability review required: {counts.get('readability_review_required')}

## Crop counts
- local refined: {counts.get('local_refined')}
- context refined: {counts.get('context_refined')}
- extreme: {counts.get('extreme')}
- clipped: {counts.get('clipped')}
- missing target: {counts.get('missing_target')}
- missing annotation: {counts.get('missing_annotation')}

## Frozen P2.5.2 invariants
- vision candidates: {counts.get('p252_vision_candidates')} (expected 14)
- deferred: {counts.get('p252_deferred')} (expected 16)
- excluded: {counts.get('p252_excluded')} (expected 293)
- invariants_ok: {counts.get('invariants_ok')}

## Golden cases
- B97A: {json.dumps(gold.get('b97a'), default=str)}
- OCR Stirrup: {json.dumps(gold.get('ocr_stirrup'), default=str)}
- Development Note: {json.dumps(gold.get('development_note'), default=str)}
- SFR Note: {json.dumps(gold.get('sfr_note'), default=str)}

## Determinism
- Run 1 vs Run 2: {det.get('determinism_status')}
- fingerprint: `{det.get('fingerprint')}`

## Claude
- Calls made: {summary.get('claude_calls', 0)}

## Engineering
- Changes made: {ENGINEERING_CHANGES}

## Regression
- P2.4 / T18 / T17 / T16 / R.3.1 / R1.3 / P2.5.0 / P2.5.1 / P2.5.2 fingerprints unchanged: {reg.get('unchanged')}
- details: {json.dumps({"unchanged": reg.get("unchanged"), "changed_keys": reg.get("changed_keys")}, default=str)}

## Visual inspection
- contact sheets: {inspection.get('local_contact_sheet', {}).get('path')} ; {inspection.get('beam_context_contact_sheet', {}).get('path')}
- individual crops: {inspection.get('individual_crops_root')}
- candidates requiring manual review: {json.dumps(review, default=str)}

## Final decision
{summary.get('decision')}
"""

    status_path = out_root / "P2.5.2.1_STATUS.md"
    status_path.write_text(status_md, encoding="utf-8")
    _dump(reports_dir / "P2521_summary.json", summary)
    _dump(out_root / "meta.json", {
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "model_version": MODEL_VERSION,
        "claude": CLAUDE,
        "engineering_changes": ENGINEERING_CHANGES,
        "decision": summary.get("decision"),
        "pass_fail": summary.get("pass_fail"),
    })
    return {
        "status_md": str(status_path),
        "summary_json": str(reports_dir / "P2521_summary.json"),
    }


__all__ = ["write_reports"]
