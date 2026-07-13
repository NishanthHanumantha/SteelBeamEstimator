"""Scan Version6 source code and inventory every engineering rule. Read-only."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

RULE_CLASSES = (
    "Engine", "Determiner", "Resolver", "Calculator", "Builder",
    "Classifier", "Formula", "Cache", "RuleResolver",
)

ROLE_KEYWORDS: Dict[str, List[str]] = {
    "TOP_MAIN": ["TOP_MAIN", "top_main", "TopMain", "MAIN_BAR", "main_tension", "TENSION_POSITION"],
    "BOTTOM_MAIN": ["BOTTOM_MAIN", "bottom_main", "BottomMain", "BOTTOM_REINFORCEMENT"],
    "TOP_EXTRA": ["EXTRA_TOP", "extra_top", "TOP_EXTRA", "top_extra", "ExtraTop", "HAUNCH"],
    "BOTTOM_EXTRA": ["EXTRA_BOTTOM", "extra_bottom", "BOTTOM_EXTRA", "bottom_extra"],
    "STIRRUP": ["STIRRUP", "stirrup", "Stirrup", "TRANSVERSE", "transverse", "LINK_BAR", "link_bar"],
    "SIDE_FACE": ["SIDE_BAR", "side_bar", "SIDE_FACE", "side_face", "EDGE_BAR"],
    "SPACER_BAR": ["SPACER", "spacer", "SPACER_BAR"],
    "CHAIR_BAR": ["CHAIR", "chair", "CHAIR_BAR"],
    "DEVELOPMENT_LENGTH": ["development_length", "DevelopmentLength", "Ld", "get_ld", "DEVELOPMENT_LENGTH"],
    "HOOK": ["hook_length", "HookLength", "hook_rule", "HOOK", "HookRule"],
    "LAP_SPLICE": ["lap_length", "LapLength", "lap_factor", "LAP", "LapRule"],
    "CUT_LENGTH": ["cut_length", "CutLength", "CutLengthFormula", "CUT_LENGTH"],
    "CURTAILMENT": ["curtailment", "Curtailment", "CURTAILMENT"],
}

SCAN_DIRS = [
    "engineering_calculations",
    "engineering_intent",
    "engineering_specifications",
    "engineering_geometry",
    "general_notes",
    "reinforcement_calculation",
    "services",
]

PHASE_MAP: Dict[str, str] = {
    "engineering_calculations": "Phase I (I.3–I.17)",
    "engineering_intent": "Phase K.1",
    "engineering_specifications": "Phase H",
    "engineering_geometry": "Phase H.2",
    "general_notes": "Phase E",
    "reinforcement_calculation": "Phase I.2",
    "services": "Phase I (services layer)",
}


class EngineeringRuleInventory:
    """Discover and catalogue every engineering rule in Version6 source."""

    def __init__(self, src_root: Path) -> None:
        self._src = src_root

    def build(self) -> Dict[str, Any]:
        # Single-pass: read all source files once, build a corpus
        corpus: Dict[str, str] = {}
        for scan_dir in SCAN_DIRS:
            pkg_dir = self._src / scan_dir
            if not pkg_dir.exists():
                continue
            for py_file in sorted(pkg_dir.rglob("*.py")):
                if py_file.name.startswith("__"):
                    continue
                try:
                    corpus[str(py_file)] = py_file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    corpus[str(py_file)] = ""

        rules: List[Dict[str, Any]] = []
        rule_counter = [0]

        def _new_id() -> str:
            rule_counter[0] += 1
            return f"RULE::L.2::{rule_counter[0]:04d}"

        for file_path_str, source in corpus.items():
            py_file = Path(file_path_str)
            # Determine scan_dir for this file
            scan_dir_name = None
            for sd in SCAN_DIRS:
                if (self._src / sd) in py_file.parents:
                    scan_dir_name = sd
                    break
            if not scan_dir_name:
                continue
            self._scan_file(py_file, scan_dir_name, rules, _new_id, source)

        # Build a combined corpus string for import analysis (fast membership check)
        combined_corpus = "\n".join(corpus.values())

        for rule in rules:
            src_text = rule.pop("source_text", "")
            # Classify roles by scanning full file source (already in corpus)
            file_source = corpus.get(rule.get("_file_path", ""), src_text)
            covered = []
            for role, keywords in ROLE_KEYWORDS.items():
                if any(kw in file_source for kw in keywords):
                    covered.append(role)
            rule["roles_referenced"] = covered
            rule.pop("_file_path", None)

            # Dead-code check: is class_name mentioned anywhere else in the corpus?
            class_name = rule["class_or_function"]
            mention_count = combined_corpus.count(class_name)
            # The class definition itself accounts for at least 1 occurrence
            rule["imported_by_count"] = max(0, mention_count - 1)
            rule["dead_code_candidate"] = (
                mention_count <= 1
                and rule["class_type"] == "class"
            )

        return {
            "total_rules": len(rules),
            "rules": rules,
            "dead_code_candidates": [r for r in rules if r.get("dead_code_candidate")],
            "scan_dirs": SCAN_DIRS,
        }

    def _scan_file(
        self,
        py_file: Path,
        scan_dir: str,
        rules: List[Dict[str, Any]],
        new_id,
        source: str,
    ) -> None:
        try:
            module_path = str(py_file.relative_to(self._src.parent)).replace("\\", "/")
        except ValueError:
            module_path = py_file.name
        phase = PHASE_MAP.get(scan_dir, scan_dir)

        # Find class definitions matching rule naming patterns
        for m in re.finditer(r"^class\s+(\w+)", source, re.MULTILINE):
            class_name = m.group(1)
            if any(suffix in class_name for suffix in RULE_CLASSES):
                body = source[m.start():]
                methods = re.findall(r"    def\s+(\w+)\(", body[:2000])
                rules.append({
                    "rule_id": new_id(),
                    "class_or_function": class_name,
                    "class_type": "class",
                    "module": py_file.stem,
                    "module_path": module_path,
                    "phase_introduced": phase,
                    "package": scan_dir,
                    "methods": methods[:20],
                    "has_role_parameter": "role" in source[:3000],
                    "reachable": True,
                    "source_text": source[:200],
                    "_file_path": str(py_file),
                })

        # Find top-level functions with rule/engine/formula in name
        for m in re.finditer(r"^def\s+(\w+)\(", source, re.MULTILINE):
            fn_name = m.group(1)
            if any(kw in fn_name.lower() for kw in ("rule", "engine", "formula", "calculate", "compute")):
                rules.append({
                    "rule_id": new_id(),
                    "class_or_function": fn_name,
                    "class_type": "function",
                    "module": py_file.stem,
                    "module_path": module_path,
                    "phase_introduced": phase,
                    "package": scan_dir,
                    "methods": [],
                    "has_role_parameter": "role" in source[:1000],
                    "reachable": True,
                    "source_text": source[:100],
                    "_file_path": str(py_file),
                })
