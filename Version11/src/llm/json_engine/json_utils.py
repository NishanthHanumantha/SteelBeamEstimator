"""JSON utility helpers."""

from __future__ import annotations

import json
from typing import Any


def loads_strict(text: str) -> Any:
    """Parse JSON with strict error propagation."""
    return json.loads(text)


def dumps_compact(payload: Any) -> str:
    """Serialize JSON deterministically for checksums."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
