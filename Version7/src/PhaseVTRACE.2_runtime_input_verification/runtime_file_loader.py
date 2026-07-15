"""
runtime_file_loader.py — Simulates and records every file load that L.2 performs.

Strategy (READ-ONLY):
  Import InterpretationCollector from L.2 and call collect() on it directly.
  This calls the real L.2 code but does NOT trigger any output writes
  (only InterpretationEngine.run() writes outputs, and we do NOT call that).
  All file reads are intercepted by monkey-patching json.loads + pathlib.Path.read_text
  BEFORE the import, then restored immediately after collect() returns.

  Zero engineering logic is modified — only the built-in I/O primitives are
  wrapped temporarily within THIS process, restored on exit.

MODEL_VERSION: 7.1.3  |  READ-ONLY
"""

from __future__ import annotations
import json
import pathlib
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .runtime_models import RuntimeLoadEvent


_LOAD_LOG: List[dict] = []


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_intercepted_read_text(original_read_text):
    """Wrap pathlib.Path.read_text to log every JSON file read."""
    def _intercepted(self, encoding=None, errors=None):
        result = original_read_text(self, encoding=encoding, errors=errors)
        if str(self).lower().endswith(".json"):
            entry = {
                "sequence":  len(_LOAD_LOG) + 1,
                "timestamp": _timestamp(),
                "path":      str(self),
                "size":      len(result),
                "caller":    "pathlib.Path.read_text",
            }
            _LOAD_LOG.append(entry)
        return result
    return _intercepted


def _make_intercepted_yaml_load(original_yaml_load):
    def _intercepted(stream, *args, **kwargs):
        path_hint = getattr(stream, 'name', str(stream)[:80]) if hasattr(stream, 'name') else "stream"
        result = original_yaml_load(stream, *args, **kwargs)
        entry = {
            "sequence":  len(_LOAD_LOG) + 1,
            "timestamp": _timestamp(),
            "path":      path_hint,
            "size":      0,
            "caller":    "yaml.safe_load",
        }
        _LOAD_LOG.append(entry)
        return result
    return _intercepted


class RuntimeFileLoader:
    """
    Invokes L.2's InterpretationCollector.collect() with I/O interception active.
    Returns:
      - The collect() snapshot (inputs as L.2 sees them)
      - The ordered load log
    """

    def __init__(self, project_root: pathlib.Path, l2_src_dir: pathlib.Path):
        self._root    = project_root
        self._l2_src  = l2_src_dir
        self._log: List[dict] = []

    def run(self) -> Tuple[Optional[dict], List[dict]]:
        global _LOAD_LOG
        _LOAD_LOG = []

        # ── Install interception ──────────────────────────────────────────────
        original_read_text = pathlib.Path.read_text

        try:
            import yaml as _yaml
            original_yaml_load = _yaml.safe_load
        except ImportError:
            _yaml = None
            original_yaml_load = None

        pathlib.Path.read_text = _make_intercepted_read_text(original_read_text)
        if _yaml and original_yaml_load:
            _yaml.safe_load = _make_intercepted_yaml_load(original_yaml_load)

        snapshot = None
        try:
            # ── Bootstrap L.2 src onto sys.path (same as the runner does) ────
            l2_str = str(self._l2_src)
            if l2_str not in sys.path:
                sys.path.insert(0, l2_str)

            from interpretation_collector import InterpretationCollector
            collector = InterpretationCollector(self._root)
            snapshot  = collector.collect()

        except Exception as exc:
            snapshot = {"_error": str(exc)}

        finally:
            # ── Restore original I/O ─────────────────────────────────────────
            pathlib.Path.read_text = original_read_text
            if _yaml and original_yaml_load:
                _yaml.safe_load = original_yaml_load

        self._log = list(_LOAD_LOG)
        return snapshot, self._log

    def get_load_events(self) -> List[RuntimeLoadEvent]:
        events = []
        for entry in self._log:
            path = entry.get("path", "")
            events.append(RuntimeLoadEvent(
                sequence     = entry["sequence"],
                key          = pathlib.Path(path).name,
                absolute_path = path,
                beam_count   = None,
                beam_ids     = [],
                load_status  = "LOADED",
                caller       = entry.get("caller", ""),
                note         = f"size={entry.get('size', 0)}B",
            ))
        return events
