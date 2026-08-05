"""
T1.8.3 — Before/After ownership diff markdown + SharedOwnershipQA.json.
MODEL_VERSION: 9.5.3
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

MODEL_VERSION = "9.5.3"


def write_shared_ownership_qa(
    dest: Path,
    merges: Dict[str, Dict[str, Any]],
    *,
    generated_at: str,
    validation: Dict[str, Any],
) -> None:
    by_beam = {}
    for bid, m in sorted(merges.items()):
        c = m.get("counts") or {}
        by_beam[bid] = {
            "beam": bid,
            "owned": c.get("owned", 0),
            "shared": c.get("shared", 0),
            "effective": c.get("effective", 0),
            "owner_annotations": [a.get("text") for a in m.get("owner_annotations") or []],
            "shared_annotations": [a.get("text") for a in m.get("shared_annotations") or []],
            "effective_annotations": [
                a.get("text") for a in m.get("effective_annotations") or []
            ],
        }
    doc = {
        "phase_id": "T1.8.3",
        "model_version": MODEL_VERSION,
        "generated_at": generated_at,
        "by_beam": by_beam,
        "validation": validation,
    }
    Path(dest).write_text(json.dumps(doc, indent=2), encoding="utf-8")


def write_ownership_diff(
    dest: Path,
    merges: Dict[str, Dict[str, Any]],
    *,
    generated_at: str,
    focus: List[str],
) -> None:
    lines = [
        "# T1.8.3 — Ownership Diff (Before vs After Shared SFR)",
        "",
        f"**MODEL_VERSION:** {MODEL_VERSION}",
        f"**Generated:** {generated_at}",
        "",
        "Before = T1.8 owned only. After = owned + shared (runtime effective).",
        "",
    ]
    for bid in focus:
        m = merges.get(bid) or {}
        c = m.get("counts") or {}
        owned = c.get("owned", 0)
        shared = c.get("shared", 0)
        eff = c.get("effective", 0)
        lines.extend(
            [
                f"## {bid}",
                "",
                "### Before",
                "",
                f"- Owned: `{owned}`",
                f"- Shared: `0`",
                f"- Effective: `{owned}`",
                f"- Annotations: `{[a.get('text') for a in m.get('owner_annotations') or []]}`",
                "",
                "### After",
                "",
                f"- Owned: `{owned}`",
                f"- Shared: `{shared}`",
                f"- Effective: `{eff}`",
                f"- Shared annotations: `{[a.get('text') for a in m.get('shared_annotations') or []]}`",
                f"- Effective annotations: `{[a.get('text') for a in m.get('effective_annotations') or []]}`",
                "",
                "---",
                "",
            ]
        )
    Path(dest).write_text("\n".join(lines), encoding="utf-8")
