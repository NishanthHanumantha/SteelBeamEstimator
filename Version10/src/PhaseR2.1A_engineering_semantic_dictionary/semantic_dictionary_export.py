"""Export Phase R.2.1A artefacts."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict


class SemanticDictionaryExport:

    def __init__(self, output_dir: pathlib.Path):
        self._out = output_dir
        self._out.mkdir(parents=True, exist_ok=True)

    def export_all(self, artefacts: Dict[str, Any], markdown: str) -> Dict[str, str]:
        paths = {}
        for name, data in artefacts.items():
            path = self._out / name
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            paths[name] = str(path)
        md = self._out / "semantic_dictionary_report.md"
        md.write_text(markdown, encoding="utf-8")
        paths["semantic_dictionary_report.md"] = str(md)
        return paths
