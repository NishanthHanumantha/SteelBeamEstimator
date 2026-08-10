"""
Bootstrap QA.2A normalizers/matchers for read-only GT comparison.
MODEL_VERSION: 10.6.0
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Any, Tuple

_SUBMODULES = [
    "__init__",
    "gt_models",
    "workbook_normalizer",
    "beam_matcher",
    "bar_matcher",
    "metrics_engine",
    "error_classifier",
    "report_compiler",
    "json_exporter",
    "excel_exporter",
    "phase_qa2a_orchestrator",
]


def bootstrap_qa2a(engine_root: Path) -> None:
    v10 = Path(engine_root)
    os.chdir(v10)
    pkg_dir = v10 / "src" / "PhaseQA.2A_ground_truth_benchmark"
    alias = "PhaseQA2A"
    r14 = str(v10 / "src" / "PhaseR1_4_production_accuracy_benchmark")
    for p in (r14, str(v10)):
        if p not in sys.path:
            sys.path.insert(0, p)

    if alias in sys.modules and "workbook_normalizer" in sys.modules:
        return

    pkg = types.ModuleType(alias)
    pkg.__path__ = [str(pkg_dir)]
    pkg.__package__ = alias
    sys.modules[alias] = pkg

    loaded = {}
    for sub in _SUBMODULES:
        full = f"{alias}.{sub}"
        spec = importlib.util.spec_from_file_location(full, pkg_dir / f"{sub}.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = alias
        sys.modules[full] = mod
        loaded[sub] = (spec, mod)
        if sub != "__init__":
            setattr(pkg, sub, mod)
            sys.modules[sub] = mod

    for sub in _SUBMODULES:
        spec, mod = loaded[sub]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        if sub == "__init__":
            for attr, val in vars(mod).items():
                if not attr.startswith("__"):
                    setattr(pkg, attr, val)
        else:
            sys.modules[sub] = mod
            setattr(pkg, sub, mod)


def load_matchers(engine_root: Path) -> Tuple[Any, Any, Any]:
    bootstrap_qa2a(engine_root)
    return (
        sys.modules["workbook_normalizer"].WorkbookNormalizer,
        sys.modules["beam_matcher"].BeamMatcher,
        sys.modules["bar_matcher"].BarMatcher,
    )
