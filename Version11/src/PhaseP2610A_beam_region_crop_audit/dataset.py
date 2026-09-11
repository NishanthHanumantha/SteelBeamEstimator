"""Locate Fourth/Fifth reinforcement DXFs. Read-only. No R.1 association."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .config import BENCHMARK_BEAMS, TARGET_BEAMS

_V10 = Path(__file__).resolve().parents[2]
_REPO = _V10.parent

_SET_FOLDER_HINTS = {
    "Fourth": ("4th Set", "Fourth Set"),
    "Fifth": ("5th Set", "Fifth Set"),
}


def repo_root(version10_root: Optional[Path] = None) -> Path:
    return Path(version10_root or _V10).resolve().parent


def find_reinforcement_dxf_for_set(version10_root: Path, set_key: str) -> Path:
    repo = repo_root(version10_root)
    test_input = repo / "Test_Input"
    hints = _SET_FOLDER_HINTS.get(set_key) or (set_key,)
    if test_input.exists():
        for child in sorted(test_input.iterdir()):
            if not child.is_dir():
                continue
            name = child.name
            if not any(h.lower() in name.lower() for h in hints):
                continue
            reinf = child / "reinforcement"
            if not reinf.is_dir():
                continue
            dxfs = sorted(reinf.glob("*.dxf"))
            if dxfs:
                return dxfs[0]
    web = Path(version10_root) / "data" / "web_runs"
    if web.exists():
        key = set_key.lower()
        runs = [p for p in web.iterdir() if p.is_dir() and key in p.name.lower()]
        runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for run in runs:
            for p in run.rglob("*.dxf"):
                blob = f"{p.parent.name} {p.name}".lower()
                if "reinforc" in blob:
                    return p
    raise FileNotFoundError(f"no reinforcement DXF for set_key={set_key!r}")


def load_benchmark_targets(version10_root: Optional[Path] = None) -> List[Dict[str, object]]:
    v10 = Path(version10_root or _V10).resolve()
    dxf_by_set: Dict[str, Path] = {}
    out: List[Dict[str, object]] = []
    for set_key, beam_id in BENCHMARK_BEAMS:
        if set_key not in dxf_by_set:
            dxf_by_set[set_key] = find_reinforcement_dxf_for_set(v10, set_key)
        dxf = dxf_by_set[set_key]
        out.append(
            {
                "set_key": set_key,
                "beam_id": beam_id,
                "source_dxf": str(dxf),
                "drawing_set": set_key,
            }
        )
    if len(out) != TARGET_BEAMS:
        raise RuntimeError(f"expected {TARGET_BEAMS} benchmark beams, loaded {len(out)}")
    return out


__all__ = ["find_reinforcement_dxf_for_set", "load_benchmark_targets", "repo_root"]
