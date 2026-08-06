"""
QA.3.0 — Drawing set discovery under Test_Input.
MODEL_VERSION: 10.0.0

Reuses QA.2 discoverer logic patterns without modifying that package.
Estimator Excel is recorded for benchmark-only use; never passed to production.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

MODEL_VERSION = "10.0.0"
PHASE_ID = "QA.3.0"

_GN_HINTS = ("general", "note", "gn", "notes")
_FR_HINTS = ("fram", "layout", "plan")
_RE_HINTS = ("reinforc", "rebar", "stirrup", "detail")

# Unseen generalization targets (matched by folder name, case-insensitive)
UNSEEN_SET_KEYS = ("Fourth", "Fifth", "Sixth")


@dataclass
class DiscoveredSet:
    name: str
    root: Path
    set_key: str  # Fourth / Fifth / Sixth / Other
    general_notes: Optional[Path] = None
    framing: Optional[Path] = None
    reinforcement: Optional[Path] = None
    estimator_excel: Optional[Path] = None
    warnings: List[str] = field(default_factory=list)
    unsupported_files: List[str] = field(default_factory=list)
    duplicate_role_notes: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return bool(
            self.general_notes
            and self.framing
            and self.reinforcement
            and self.estimator_excel
        )

    @property
    def is_unseen_target(self) -> bool:
        return self.set_key in UNSEEN_SET_KEYS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "set_key": self.set_key,
            "root": str(self.root),
            "general_notes": str(self.general_notes) if self.general_notes else None,
            "framing": str(self.framing) if self.framing else None,
            "reinforcement": str(self.reinforcement) if self.reinforcement else None,
            "estimator_excel": str(self.estimator_excel) if self.estimator_excel else None,
            "estimator_excel_usage": "benchmark_only",
            "is_complete": self.is_complete,
            "is_unseen_target": self.is_unseen_target,
            "warnings": list(self.warnings),
            "unsupported_files": list(self.unsupported_files),
            "duplicate_role_notes": list(self.duplicate_role_notes),
        }


def _set_key(name: str) -> str:
    low = name.lower()
    for key in UNSEEN_SET_KEYS:
        if key.lower() in low:
            return key
    if "first" in low:
        return "First"
    if "second" in low:
        return "Second"
    if "third" in low:
        return "Third"
    return "Other"


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
        p
        for p in root.rglob("*.xlsx")
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
    for sub in root.iterdir() if root.is_dir() else []:
        if not sub.is_dir():
            continue
        name = sub.name.lower().replace(" ", "_")
        if any(h in name for h in folder_hints):
            dxfs = sorted(sub.glob("*.dxf"))
            if dxfs:
                return _pick_dxf(dxfs, hints) or dxfs[0]
    all_dxfs = sorted(root.rglob("*.dxf"))
    return _pick_dxf(all_dxfs, hints)


class DrawingSetDiscovery:
    def __init__(self, test_input_root: Path):
        self.root = Path(test_input_root)

    def discover(self) -> List[DiscoveredSet]:
        if not self.root.exists():
            raise FileNotFoundError(f"Test_Input not found: {self.root}")
        sets: List[DiscoveredSet] = []
        for child in sorted(self.root.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            sets.append(self._parse_set(child))
        return sets

    def discover_unseen_targets(self) -> List[DiscoveredSet]:
        return [s for s in self.discover() if s.is_unseen_target]

    def _parse_set(self, folder: Path) -> DiscoveredSet:
        ds = DiscoveredSet(name=folder.name, root=folder, set_key=_set_key(folder.name))
        entries = list(folder.rglob("*"))
        if not any(p.is_file() for p in entries):
            ds.warnings.append("Empty folder")

        supported_ext = {".dxf", ".xlsx", ".xls"}
        for p in entries:
            if p.is_file() and p.suffix.lower() not in supported_ext:
                if p.name.startswith("~$") or p.name.startswith("."):
                    continue
                # ignore common junk
                if p.suffix.lower() in {".png", ".jpg", ".pdf", ".txt", ".md", ".json"}:
                    ds.unsupported_files.append(str(p.relative_to(folder)))
                elif p.suffix:
                    ds.unsupported_files.append(str(p.relative_to(folder)))

        ds.general_notes = _find_role_dxf(folder, _GN_HINTS, ("general", "note", "gn"))
        ds.framing = _find_role_dxf(folder, _FR_HINTS, ("fram", "layout"))
        ds.reinforcement = _find_role_dxf(folder, _RE_HINTS, ("reinforc", "rebar", "detail"))
        ds.estimator_excel = _find_excel(folder)

        # Duplicate DXF role detection
        dxfs = list(folder.rglob("*.dxf"))
        if len(dxfs) > 3:
            ds.duplicate_role_notes.append(
                f"{len(dxfs)} DXF files found (expected ~3 role files)"
            )

        if (
            ds.framing
            and ds.reinforcement
            and ds.framing.resolve() == ds.reinforcement.resolve()
        ):
            alts = [p for p in dxfs if p.resolve() != ds.framing.resolve()]
            alt = _pick_dxf(alts, _RE_HINTS)
            if alt:
                ds.reinforcement = alt
            else:
                ds.warnings.append("Framing and Reinforcement resolved to same DXF")

        if not ds.general_notes:
            ds.warnings.append("Missing General Notes DXF")
        if not ds.framing:
            ds.warnings.append("Missing Framing Plan DXF")
        if not ds.reinforcement:
            ds.warnings.append("Missing Reinforcement Plan DXF")
        if not ds.estimator_excel:
            ds.warnings.append("Missing Estimator Excel (benchmark ground truth)")
        return ds

    def write_report(self, out_path: Path, sets: Sequence[DiscoveredSet]) -> Dict[str, Any]:
        doc = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "test_input": str(self.root),
            "sets_discovered": len(sets),
            "unseen_targets": [
                s.name for s in sets if s.is_unseen_target
            ],
            "complete_unseen_targets": [
                s.name for s in sets if s.is_unseen_target and s.is_complete
            ],
            "sets": [s.to_dict() for s in sets],
            "notes": [
                "Estimator Excel is recorded for post-production benchmarking only.",
                "Production execution must not open estimator workbooks.",
            ],
        }
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc
