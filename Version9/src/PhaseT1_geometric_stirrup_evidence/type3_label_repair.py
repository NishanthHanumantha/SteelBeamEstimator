"""
T1 helper — recover Type3 stirrup pattern into bar_label for SI.1.
Residual-scoped; soft-no-op when flag off. MODEL_VERSION: 9.3.0
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "9.3.0"

_TYPE3_RE = re.compile(r"@\s*(\d+(?:\s*/\s*\d+)+)", re.I)
_AT_RE = re.compile(r"@\s*\d+", re.I)


def _t1_enabled(engine_root: Path) -> bool:
    cfg = engine_root / "config" / "geometric_stirrup_evidence.yaml"
    if not cfg.exists():
        return False
    for line in cfg.read_text(encoding="utf-8").splitlines():
        s = line.split("#", 1)[0].strip()
        if s.startswith("enable_geometry_stirrup_evidence"):
            return s.split(":", 1)[-1].strip().lower() in ("true", "1", "yes", "on")
    return True


def _engine_root() -> Optional[Path]:
    eng = (os.environ.get("STEEL_ENGINE_ROOT") or "").strip()
    if eng:
        return Path(eng)
    return None


def _set_id() -> str:
    run = (os.environ.get("STEEL_RUN_ROOT") or "").strip()
    name = Path(run).name.lower() if run else ""
    if "first" in name:
        return "Set1"
    if "second" in name:
        return "Set2"
    if "third" in name:
        return "Set3"
    return "Unknown"


def is_residual_beam(beam_id: str, *, groups: Optional[List[str]] = None) -> bool:
    """True if beam is in residual list. Optionally require specific target_group(s)."""
    root = _engine_root()
    if not root or not _t1_enabled(root):
        return False
    path = root / "data/output/Track1_geometric_evidence/residual_target_beams.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    sid = _set_id()
    want = set(groups) if groups else None
    for r in data.get("rows") or []:
        if not (
            r.get("included")
            and str(r.get("set_id")) == sid
            and str(r.get("beam_id")) == beam_id
        ):
            continue
        if want is None or str(r.get("target_group") or "") in want:
            return True
    return False


def recover_type3_spacings(beam_id: str) -> List[int]:
    out_env = (os.environ.get("STEEL_OUTPUT_ROOT") or "").strip()
    if not out_env:
        return []
    path = (
        Path(out_env)
        / "PhaseR.1_generalized_reinforcement_discovery"
        / "reinforcement_annotations.json"
    )
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    best: List[int] = []
    for a in (data.get("by_beam") or {}).get(beam_id) or []:
        if str(a.get("role") or "").upper() != "STIRRUP":
            continue
        text = str(a.get("clean_text") or "")
        m = _TYPE3_RE.search(text.replace("\\P", "").replace(" ", ""))
        if not m:
            continue
        parts = [int(x) for x in re.findall(r"\d+", m.group(1))]
        if len(parts) > len(best):
            best = parts
    return best


def repair_bar_label(beam_id: str, label: str, diameter_mm: float = 8.0) -> Tuple[str, Optional[List[int]]]:
    """
    For TARGET_WRONG_QTY residual beams only (T1.4): if R.1 has Type3 and label
    is truncated to the first spacing, rewrite so SI.1 expands zones once.
    """
    if not is_residual_beam(beam_id, groups=["TARGET_WRONG_QTY"]):
        return label, None
    spacings = recover_type3_spacings(beam_id)
    if len(spacings) < 2:
        return label, None
    # Already Type3?
    if _TYPE3_RE.search((label or "").replace(" ", "")):
        return label, spacings
    # Require truncated label's first @spacing to match Type3[0] (avoid wrong callout)
    m_at = _AT_RE.search(label or "")
    if m_at:
        try:
            first = int(re.search(r"\d+", m_at.group(0)).group(0))  # type: ignore
        except Exception:
            first = None
        if first is not None and first != int(spacings[0]):
            return label, None
    dia = int(round(float(diameter_mm or 8)))
    pattern = "/".join(str(s) for s in spacings)
    if m_at:
        new_label = _AT_RE.sub(f"@{pattern}", label, count=1)
        if "C/C" not in new_label.upper():
            new_label = new_label.rstrip() + "C/C"
    else:
        new_label = f"2L-Y{dia}@{pattern}C/C"
    return new_label, spacings


def load_t14_boundaries(beam_id: str, n_zones: int) -> Optional[List[Tuple[float, float]]]:
    """Return [(start,end), ...] from T1.2 pitch_change refinement, else None."""
    if n_zones < 2 or not is_residual_beam(beam_id):
        return None
    out_env = (os.environ.get("STEEL_OUTPUT_ROOT") or "").strip()
    if not out_env:
        return None
    path = (
        Path(out_env)
        / "PhaseT1_geometric_stirrup_evidence"
        / "stirrup_geometry_evidence.json"
    )
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    ev = (data.get("by_beam") or {}).get(beam_id) or {}
    refined = ev.get("zone_refinement") or {}
    if refined.get("method") != "pitch_change":
        return None
    segs = refined.get("segments") or []
    if len(segs) != n_zones:
        return None
    return [
        (float(s["start_mm"]), float(s["end_mm"]))
        for s in segs
    ]
