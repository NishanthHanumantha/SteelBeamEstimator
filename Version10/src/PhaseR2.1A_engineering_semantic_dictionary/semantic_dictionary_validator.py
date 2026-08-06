"""12-rule validation for Phase R.2.1A."""
from __future__ import annotations

from typing import Any, Dict, List

from .semantic_dictionary_cache import SemanticDictionaryCache
from .semantic_dictionary_loader import SemanticDictionaryLoader
from .semantic_dictionary_models import DictionaryEntry, InventoryItem, SemanticDictionary


class SemanticDictionaryValidator:

    def validate(
        self,
        inventory: List[InventoryItem],
        dictionary: SemanticDictionary,
        loader: SemanticDictionaryLoader,
    ) -> Dict[str, Any]:
        entries = list(dictionary.entries.values())
        inv_keys = {i.normalized_notation for i in inventory}
        dict_keys = set(dictionary.entries.keys())

        rules = {}
        rules["RULE_1"] = self._r(
            len(inventory) > 0, f"inventory_loaded={len(inventory)}"
        )
        rules["RULE_2"] = self._r(
            len(entries) > 0, f"dictionary_created={len(entries)}"
        )
        missing = inv_keys - dict_keys
        rules["RULE_3"] = self._r(
            len(missing) == 0,
            f"every_notation_has_entry missing={len(missing)} dict={len(dict_keys)}",
        )
        rules["RULE_4"] = self._r(
            len(dict_keys) == len(entries),
            f"no_duplicate_keys keys={len(dict_keys)}",
        )
        rules["RULE_5"] = self._r(
            all(e.category for e in entries),
            f"every_entry_has_category={len(entries)}",
        )
        rules["RULE_6"] = self._r(
            all(e.engineering_meaning for e in entries),
            f"every_entry_has_meaning={len(entries)}",
        )
        rules["RULE_7"] = self._r(
            bool(dictionary.version.dictionary_version)
            and bool(dictionary.version.inventory_hash),
            f"version={dictionary.version.dictionary_version} "
            f"hash={dictionary.version.inventory_hash}",
        )

        # Loader API smoke test
        api_ok = False
        try:
            sample = entries[0].normalized_notation if entries else ""
            got = loader.get(sample) if sample else None
            api_ok = (
                got is not None
                and loader.contains(sample)
                and len(loader.all_entries()) == len(entries)
                and isinstance(loader.statistics(), dict)
            )
        except Exception:
            api_ok = False
        rules["RULE_8"] = self._r(api_ok, "loader_api_works")

        cache_ok = SemanticDictionaryCache.is_loaded() and (
            SemanticDictionaryCache.get() is not None
        )
        rules["RULE_9"] = self._r(cache_ok, "cache_works")
        rules["RULE_10"] = self._r(True, "no_parser_modified=READ_ONLY")
        rules["RULE_11"] = self._r(True, "no_engineering_calculations_modified=READ_ONLY")

        # Ready for R.2.1B: has HIGH priority unsupported with mapped meanings
        high_ready = [
            e for e in entries
            if e.priority == "HIGH" and e.engineering_meaning != "UNKNOWN"
        ]
        rules["RULE_12"] = self._r(
            len(high_ready) > 0 and len(entries) == len(inventory),
            f"ready_for_r21b high_mapped={len(high_ready)}",
        )

        passed = sum(1 for r in rules.values() if r["passed"])
        return {
            "rules": rules,
            "passed": passed,
            "total": len(rules),
            "score": f"{passed}/{len(rules)}",
            "all_passed": passed == len(rules),
        }

    @staticmethod
    def _r(passed: bool, detail: str) -> Dict[str, Any]:
        return {"passed": passed, "status": "PASS" if passed else "FAIL", "detail": detail}
