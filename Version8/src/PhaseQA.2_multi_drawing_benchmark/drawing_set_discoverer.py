"""
drawing_set_discoverer.py — Auto-discover Drawing Sets under Test_Input.
MODEL_VERSION: 8.9.0
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

MODEL_VERSION = "8.9.0"

_GN_HINTS = ("general", "note", "gn", "notes")
_FR_HINTS = ("fram", "layout", "plan")
_RE_HINTS = ("reinforc", "rebar", "stirrup", "detail")


@dataclass
class DrawingSet:
    """One auto-discovered drawing set with its four required inputs."""
    name: str
    root: Path
    general_notes: Optional[Path] = None
    framing: Optional[Path] = None
    reinforcement: Optional[Path] = None
    estimator_excel: Optional[Path] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return bool(
            self.general_notes
            and self.framing
            and self.reinforcement
            and self.estimator_excel
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "root": str(self.root),
            "general_notes": str(self.general_notes) if self.general_notes else None,
            "framing": str(self.framing) if self.framing else None,
            "reinforcement": str(self.reinforcement) if self.reinforcement else None,
            "estimator_excel": str(self.estimator_excel) if self.estimator_excel else None,
            "is_complete": self.is_complete,
            "warnings": list(self.warnings),
        }


def _pick_dxf(files: List[Path], hints: tuple) -> Optional[Path]:
    scored = []
    for p in files:
        name = p.name.lower()
        score = sum(1 for h in hints if h in name)
        scored.append((score, -p.stat().st_size, p))
    scored.sort(reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][2]
    return files[0] if files else None


def _find_excel(root: Path) -> Optional[Path]:
    preferred = [
        p for p in root.rglob("*.xlsx")
        if not p.name.startswith("~$")
        and (
            "estimator" in p.parent.name.lower()
            or "estimator" in p.name.lower()
            or "bbs" in p.name.lower()
        )
    ]
    pool = preferred or [
        p for p in root.rglob("*.xlsx") if not p.name.startswith("~$")
    ]
    if not pool:
        return None
    return sorted(pool, key=lambda p: p.stat().st_size, reverse=True)[0]


def _find_role_dxf(root: Path, hints: tuple, folder_hints: tuple) -> Optional[Path]:
    # Prefer role-named subfolders
    for sub in root.iterdir() if root.is_dir() else []:
        if not sub.is_dir():
            continue
        name = sub.name.lower().replace(" ", "_")
        if any(h in name for h in folder_hints):
            dxfs = sorted(sub.glob("*.dxf"))
            if dxfs:
                return _pick_dxf(dxfs, hints) or dxfs[0]
    # Fallback: all DXFs under the set
    all_dxfs = sorted(root.rglob("*.dxf"))
    return _pick_dxf(all_dxfs, hints)


class DrawingSetDiscoverer:
    """
    Discover Drawing Sets under Test_Input.

    A Drawing Set is any immediate child directory that contains
    (or whose subfolders contain) the four required artefacts.
    """

    def __init__(self, test_input_root: Path):
        self.root = Path(test_input_root)

    def discover(self) -> List[DrawingSet]:
        if not self.root.exists():
            raise FileNotFoundError(f"Test_Input not found: {self.root}")

        sets: List[DrawingSet] = []
        for child in sorted(self.root.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name.startswith("_"):
                continue
            ds = self._parse_set(child)
            sets.append(ds)
        return sets

    def _parse_set(self, folder: Path) -> DrawingSet:
        ds = DrawingSet(name=folder.name, root=folder)
        ds.general_notes = _find_role_dxf(
            folder, _GN_HINTS, ("general", "note", "gn")
        )
        ds.framing = _find_role_dxf(
            folder, _FR_HINTS, ("fram", "layout")
        )
        ds.reinforcement = _find_role_dxf(
            folder, _RE_HINTS, ("reinforc", "rebar", "detail")
        )
        ds.estimator_excel = _find_excel(folder)

        if not ds.general_notes:
            ds.warnings.append("Missing General Notes DXF")
        if not ds.framing:
            ds.warnings.append("Missing Framing Plan DXF")
        if not ds.reinforcement:
            ds.warnings.append("Missing Reinforcement Plan DXF")
        if not ds.estimator_excel:
            ds.warnings.append("Missing Estimator Excel")

        # Ensure framing != reinforcement when both resolved to same file
        if (
            ds.framing
            and ds.reinforcement
            and ds.framing.resolve() == ds.reinforcement.resolve()
        ):
            all_dxfs = [p for p in folder.rglob("*.dxf")]
            alts = [p for p in all_dxfs if p.resolve() != ds.framing.resolve()]
            alt = _pick_dxf(alts, _RE_HINTS)
            if alt:
                ds.reinforcement = alt

        return ds
