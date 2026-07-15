"""
Engineering Context Cache — singleton per GN DXF path.

Ensures the GN DXF is parsed only once per Python process regardless of how
many pipeline modules call EngineeringContextFactory.
"""
from __future__ import annotations
import threading
import pathlib
from typing import Dict, Optional

from .engineering_context_model import EngineeringContext

_lock = threading.Lock()
_cache: Dict[str, EngineeringContext] = {}


def get_cached(gn_dxf_path: pathlib.Path) -> Optional[EngineeringContext]:
    key = str(gn_dxf_path.resolve())
    return _cache.get(key)


def put_cached(gn_dxf_path: pathlib.Path, ctx: EngineeringContext) -> None:
    key = str(gn_dxf_path.resolve())
    with _lock:
        _cache[key] = ctx


def clear_cache() -> None:
    with _lock:
        _cache.clear()
