"""Phase R.2.0.1 master orchestrator — READ-ONLY Engineering Notation Inventory."""
from __future__ import annotations

import json
import pathlib
import time
from datetime import datetime
from typing import Any, Dict, Optional

import yaml

from .engineering_symbol_detector import EngineeringSymbolDetector
from .notation_export import NotationExport
from .notation_extractor import NotationExtractor
from .notation_frequency_analyzer import NotationFrequencyAnalyzer
from .notation_inventory_database import NotationInventoryDatabase
from .notation_inventory_loader import NotationInventoryLoader
from .notation_normalizer import NotationNormalizer
from .notation_pattern_grouper import NotationPatternGrouper
from .notation_reporter import NotationReporter
from .notation_statistics import NotationStatistics
from .notation_support_analyzer import NotationSupportAnalyzer
from .notation_validator import NotationValidator
from .semantic_category_classifier import SemanticCategoryClassifier


class PhaseR201Orchestrator:

    MODEL_VERSION = "7.9.1"

    def __init__(
        self,
        v7_root: pathlib.Path,
        config_path: Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
    ):
        self._v7 = v7_root
        cfg_path = config_path or (
            v7_root / "config" / "engineering_notation_inventory.yaml"
        )
        self._config = {}
        if cfg_path.exists():
            self._config = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        out_rel = self._config.get("paths", {}).get(
            "output_dir", "data/output/PhaseR2.0.1_engineering_notation_inventory"
        )
        self._out = output_dir or (v7_root / out_rel)

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print(f"\n{'='*70}")
        print("  PHASE R.2.0.1 - Engineering Notation Semantic Inventory")
        print(f"  MODEL_VERSION {self.MODEL_VERSION}  |  {datetime.utcnow().isoformat()}")
        print("  READ-ONLY DISCOVERY — NO PARSER / CALCULATION CHANGES")
        print(f"{'='*70}\n")

        paths = self._config.get("paths", {})
        dxf = self._v7 / paths.get(
            "dxf",
            "data/Benchmark_Set_2/reinforcement/Galera_GF_BeamReinforcementDetails.dxf",
        )
        registry = self._read_json(
            self._v7 / paths.get(
                "beam_registry",
                "data/output/PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json",
            )
        )

        print("[1/9] Loading DXF text inventory (R.2.0 recovery) ...")
        entities = NotationInventoryLoader(dxf, registry).load()
        print(f"      Entities: {len(entities)}")

        print("\n[2/9] Extracting notations ...")
        extracted = NotationExtractor().extract_all(entities)
        print(f"      Tokens extracted: {len(extracted)}")

        print("\n[3/9] Normalizing ...")
        normalized = NotationNormalizer().normalize_all(extracted)
        print(f"      Normalized: {len(normalized)}")

        print("\n[4/9] Pattern grouping ...")
        groups = NotationPatternGrouper().group(normalized)
        print(f"      Unique notations: {len(groups)}")

        print("\n[5/9] Symbol detection + category classification ...")
        symbols = EngineeringSymbolDetector().detect(groups)
        classifier = SemanticCategoryClassifier()
        categories = classifier.classify_all(groups)
        cat_dist = classifier.category_distribution(categories, groups)
        print(f"      Symbols: {symbols.get('symbol_count', 0)}")

        print("\n[6/9] Support status analysis (read-only regex) ...")
        support = NotationSupportAnalyzer().analyze(groups, categories, symbols)

        print("\n[7/9] Building vocabulary database + priorities ...")
        db = NotationInventoryDatabase()
        entries = db.build(groups, categories, support, symbols)
        priorities = db.build_priorities(entries)
        freq = NotationFrequencyAnalyzer().analyze(groups, support, categories)
        stats = NotationStatistics().compute(
            entities, entries, priorities, cat_dist, freq, symbols
        )
        print(f"      Vocabulary: {len(entries)}  Priorities: {len(priorities)}")

        print("\n[8/9] Validation ...")
        validation = NotationValidator().validate(
            entities, normalized, entries, priorities, stats
        )
        print(f"      Validation: {validation['score']}")

        print("\n[9/9] Exporting artefacts ...")
        supported = [e for e in entries if e.support_status == "SUPPORTED"]
        unsupported = [e for e in entries if e.support_status == "UNSUPPORTED"]
        partial = [e for e in entries if e.support_status == "PARTIALLY_SUPPORTED"]

        readiness = {
            "model_version": self.MODEL_VERSION,
            "ready_for_r21": True,
            "vocabulary_entries": len(entries),
            "unsupported_count": len(unsupported),
            "partial_count": len(partial),
            "priority_count": len(priorities),
            "supported_pct": stats.get("supported_pct"),
            "unsupported_pct": stats.get("unsupported_pct"),
            "high_impact_priorities": [
                p.to_dict() for p in priorities if p.impact == "HIGH"
            ],
        }

        artefacts = {
            "engineering_notation_inventory.json": {
                "model_version": self.MODEL_VERSION,
                "total": len(entries),
                "items": [e.to_dict() for e in entries],
            },
            "notation_frequency.json": freq,
            "notation_categories.json": {
                "by_notation": categories,
                "distribution": cat_dist,
            },
            "supported_notations.json": {
                "total": len(supported),
                "items": [e.to_dict() for e in supported],
            },
            "unsupported_notations.json": {
                "total": len(unsupported),
                "items": [e.to_dict() for e in unsupported],
                "partially_supported": [e.to_dict() for e in partial],
            },
            "notation_statistics.json": stats,
            "semantic_readiness.json": readiness,
            "implementation_priority.json": {
                "total": len(priorities),
                "items": [p.to_dict() for p in priorities],
            },
            "notation_validation.json": validation,
            "engineering_notation_report.json": {
                "model_version": self.MODEL_VERSION,
                "statistics": stats,
                "validation": validation,
                "readiness": readiness,
                "priorities": [p.to_dict() for p in priorities],
            },
        }

        markdown = NotationReporter().build_markdown(
            stats, validation, entries, priorities, unsupported
        )
        export_paths = NotationExport(self._out).export_all(artefacts, markdown)

        elapsed = round(time.perf_counter() - t0, 3)
        status = "PASS" if validation["all_passed"] else "FAIL"
        self._print_final(stats, priorities, validation, elapsed, status)

        return {
            "status": status,
            "model_version": self.MODEL_VERSION,
            "statistics": stats,
            "validation": validation,
            "priorities": [p.to_dict() for p in priorities],
            "readiness": readiness,
            "export_paths": export_paths,
            "elapsed_seconds": elapsed,
        }

    @staticmethod
    def _read_json(path: pathlib.Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _print_final(self, stats, priorities, validation, elapsed, status):
        print(f"\n{'='*70}")
        print(f"  PHASE R.2.0.1 COMPLETE - {status}")
        print(f"  Unique notations: {stats.get('total_unique_notations', 0)}")
        print(f"  Supported: {stats.get('supported_pct')}%")
        print(f"  Unsupported: {stats.get('unsupported_pct')}%")
        print(f"  Priorities for R.2.1: {len(priorities)}")
        print(f"  Validation: {validation['score']}")
        print(f"  Time: {elapsed}s")
        print(f"{'='*70}\n")
        for rid in sorted(validation["rules"].keys()):
            r = validation["rules"][rid]
            print(f"    {rid}: {r['status']} - {r['detail']}")
        print("\n  Top R.2.1 priorities:")
        for p in priorities[:8]:
            print(f"    {p.priority}. {p.notation} [{p.impact}] freq={p.frequency}")
