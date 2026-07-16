"""Read-only loader for production R.1 regex and MTEXT stripper."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from typing import Any, Callable

_R1_PKG = "PhaseR1_production_readonly"
_loaded = False
_strip_mtext: Callable[[str], str] = None  # type: ignore
_MTEXT_CODE = None
_RE_BAR = None
_RE_STIRRUP = None
_RE_COMPOSITE = None
_NOISE_PATTERNS = None
_is_noise: Callable[[str], bool] = None  # type: ignore


def ensure_production_regex_loaded() -> None:
    global _loaded, _strip_mtext, _MTEXT_CODE
    global _RE_BAR, _RE_STIRRUP, _RE_COMPOSITE, _NOISE_PATTERNS, _is_noise
    if _loaded:
        return

    src = pathlib.Path(__file__).resolve().parent.parent
    pkg_dir = src / "PhaseR.1_generalized_reinforcement_discovery"

    pkg_mod = types.ModuleType(_R1_PKG)
    pkg_mod.__path__ = [str(pkg_dir)]
    pkg_mod.__package__ = _R1_PKG
    sys.modules[_R1_PKG] = pkg_mod

    def _load_sub(name: str):
        spec = importlib.util.spec_from_file_location(
            f"{_R1_PKG}.{name}", pkg_dir / f"{name}.py"
        )
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = _R1_PKG
        sys.modules[f"{_R1_PKG}.{name}"] = mod
        spec.loader.exec_module(mod)
        return mod

    _load_sub("reinforcement_models")
    seg = _load_sub("beam_detail_segmenter")
    ann = _load_sub("annotation_discovery")

    _strip_mtext = seg._strip_mtext
    _MTEXT_CODE = seg._MTEXT_CODE
    _RE_BAR = ann._RE_BAR
    _RE_STIRRUP = ann._RE_STIRRUP
    _RE_COMPOSITE = ann._RE_COMPOSITE
    _NOISE_PATTERNS = ann._NOISE_PATTERNS
    _is_noise = ann._is_noise
    _loaded = True


def get_strip_mtext():
    ensure_production_regex_loaded()
    return _strip_mtext


def get_mtext_code_pattern():
    ensure_production_regex_loaded()
    return _MTEXT_CODE


def get_production_patterns():
    ensure_production_regex_loaded()
    return {
        "RE_BAR": _RE_BAR,
        "RE_STIRRUP": _RE_STIRRUP,
        "RE_COMPOSITE": _RE_COMPOSITE,
        "NOISE_PATTERNS": _NOISE_PATTERNS,
        "is_noise": _is_noise,
    }
