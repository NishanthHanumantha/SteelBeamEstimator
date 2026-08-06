"""Phase R.2.1A master orchestrator — Engineering Semantic Dictionary Engine."""
from __future__ import annotations

import pathlib
import time
from datetime import datetime
from typing import Any, Dict, Optional

import yaml

from .notation_inventory_loader import NotationInventoryLoader
from .semantic_dictionary_cache import SemanticDictionaryCache
from .semantic_dictionary_export import SemanticDictionaryExport
from .semantic_dictionary_loader import SemanticDictionaryLoader
from .semantic_dictionary_reporter import SemanticDictionaryReporter
from .semantic_dictionary_statistics import SemanticDictionaryStatistics
from .semantic_dictionary_validator import SemanticDictionaryValidator


class PhaseR21AOrchestrator:

    MODEL_VERSION = "7.10.0"

    def __init__(
        self,
        v7_root: pathlib.Path,
        config_path: Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
    ):
        self._v7 = v7_root
        self._config_path = config_path or (
            v7_root / "config" / "engineering_semantic_dictionary.yaml"
        )
        self._config = {}
        if self._config_path.exists():
            self._config = yaml.safe_load(
                self._config_path.read_text(encoding="utf-8")
            ) or {}
        out_rel = self._config.get("paths", {}).get(
            "output_dir", "data/output/PhaseR2.1A_engineering_semantic_dictionary"
        )
        self._out = output_dir or (v7_root / out_rel)

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.2.1A - Engineering Semantic Dictionary Engine")
        print(f"  MODEL_VERSION {self.MODEL_VERSION}  |  {datetime.utcnow().isoformat()}")
        print("  READ-ONLY FOUNDATION — NO PARSER / CALCULATION CHANGES")
        print(f"{'='*70}\n")

        # Clear cache so this run always rebuilds
        SemanticDictionaryCache.clear()

        paths = self._config.get("paths", {})
        inv_path = self._v7 / paths.get(
            "inventory",
            "data/output/PhaseR2.0.1_engineering_notation_inventory/"
            "engineering_notation_inventory.json",
        )
        pri_path = self._v7 / paths.get(
            "priorities",
            "data/output/PhaseR2.0.1_engineering_notation_inventory/"
            "implementation_priority.json",
        )

        print("[1/6] Loading Phase R.2.0.1 inventory ...")
        inventory = NotationInventoryLoader(inv_path, pri_path).load()
        print(f"      Inventory items: {len(inventory)}")
        if not inventory:
            print("      WARNING: inventory empty — run Phase R.2.0.1 first")

        print("\n[2/6] Building semantic dictionary via Loader API ...")
        loader = SemanticDictionaryLoader(self._v7, self._config_path)
        dictionary = loader.reload()
        print(f"      Dictionary entries: {len(dictionary.entries)}")
        print(f"      Vocabulary aliases: {len(dictionary.vocabulary_map)}")

        print("\n[3/6] Computing statistics ...")
        stats = SemanticDictionaryStatistics().compute(dictionary, loader)
        print(f"      Coverage: {stats.get('coverage_pct')}%")
        print(f"      High priority: {stats.get('high_priority_entries')}")

        print("\n[4/6] Validating (12 rules) ...")
        validation = SemanticDictionaryValidator().validate(
            inventory, dictionary, loader
        )
        print(f"      Validation: {validation['score']}")

        print("\n[5/6] Preparing exports ...")
        entries = list(dictionary.entries.values())
        by_cat = {}
        by_role = {}
        by_pri = {}
        for e in entries:
            by_cat.setdefault(e.category, []).append(e.to_dict())
            if e.engineering_role:
                by_role.setdefault(e.engineering_role, []).append(e.to_dict())
            by_pri.setdefault(e.priority, []).append(e.to_dict())

        vocab_export = {
            "aliases": dictionary.vocabulary_map,
            "meanings": sorted({e.engineering_meaning for e in entries}),
            "roles": sorted({e.engineering_role for e in entries if e.engineering_role}),
            "positions": sorted({e.position for e in entries if e.position}),
        }

        artefacts = {
            "engineering_semantic_dictionary.json": dictionary.to_dict(),
            "semantic_dictionary_statistics.json": stats,
            "semantic_dictionary_version.json": dictionary.version.to_dict(),
            "semantic_dictionary_validation.json": validation,
            "engineering_vocabulary.json": vocab_export,
            "semantic_categories.json": {
                "distribution": stats.get("categories", {}),
                "by_category": {k: len(v) for k, v in by_cat.items()},
                "items": by_cat,
            },
            "semantic_roles.json": {
                "distribution": stats.get("role_distribution", {}),
                "items": by_role,
            },
            "semantic_priorities.json": {
                "distribution": stats.get("priority_distribution", {}),
                "items": by_pri,
            },
            "semantic_dictionary_report.json": {
                "model_version": self.MODEL_VERSION,
                "statistics": stats,
                "validation": validation,
                "version": dictionary.version.to_dict(),
            },
        }

        print("\n[6/6] Exporting artefacts ...")
        markdown = SemanticDictionaryReporter().build_markdown(
            dictionary, stats, validation
        )
        export_paths = SemanticDictionaryExport(self._out).export_all(
            artefacts, markdown
        )

        elapsed = round(time.perf_counter() - t0, 3)
        status = "PASS" if validation["all_passed"] else "FAIL"
        self._print_final(stats, validation, elapsed, status)

        return {
            "status": status,
            "model_version": self.MODEL_VERSION,
            "statistics": stats,
            "validation": validation,
            "version": dictionary.version.to_dict(),
            "export_paths": export_paths,
            "elapsed_seconds": elapsed,
        }

    def _print_final(self, stats, validation, elapsed, status):
        print(f"\n{'='*70}")
        print(f"  PHASE R.2.1A COMPLETE - {status}")
        print(f"  Entries: {stats.get('unique_entries', 0)}")
        print(f"  Coverage: {stats.get('coverage_pct')}%")
        print(f"  Dictionary version: {stats.get('dictionary_version')}")
        print(f"  Inventory hash: {stats.get('inventory_hash')}")
        print(f"  Validation: {validation['score']}")
        print(f"  Time: {elapsed}s")
        print(f"{'='*70}\n")
        for rid in sorted(validation["rules"].keys()):
            r = validation["rules"][rid]
            print(f"    {rid}: {r['status']} - {r['detail']}")
