"""
phase_r21b_orchestrator.py — Master orchestrator for Phase R.2.1B.
MODEL_VERSION: 7.11.0

Pipeline:
  1. Load R.1 annotations (reinforcement_annotations.json)
  2. Bootstrap Semantic Dictionary (R.2.1A)
  3. Interpret all annotations → EngineeringSemanticObjects
  4. Build enriched R.1 models JSON (corrected roles)
  5. Run production pipeline with enriched models
  6. Validate (12 rules)
  7. Compute statistics
  8. Export artefacts

Integration strategy:
  - NO R.1.* code is modified
  - NO VB1 code is modified
  - The enriched R.1 model JSON is passed to R.1.3's EngineeringBarBuilder
    as a different input path
  - VB1 is called with the resulting L2-compatible JSON
"""
from __future__ import annotations

import copy
import importlib.util
import json
import logging
import pathlib
import sys
import time
import types
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .engineering_meaning_builder import SEMANTIC_ROLE_TO_R1_ROLE
from .semantic_export import SemanticExport
from .semantic_interpreter import SemanticInterpreter
from .semantic_models import (
    EngineeringSemanticObject,
    ROLE_SIDE_FACE,
    ROLE_MAIN_BAR,
    ROLE_EXTRA_BAR,
    ROLE_STIRRUP,
    ROLE_SPACER_BAR,
    ROLE_DEVELOPMENT,
    ROLE_LAP,
)
from .semantic_reporter import SemanticReporter
from .semantic_statistics import SemanticStatistics
from .semantic_validation import SemanticValidation

log = logging.getLogger(__name__)

# ── Paths (relative to output_root) ───────────────────────────────────────────
_R1_ANN_REL   = "PhaseR.1_generalized_reinforcement_discovery/reinforcement_annotations.json"
_R1_MODEL_REL = "PhaseR.1_generalized_reinforcement_discovery/beam_reinforcement_models.json"
_REG_REL      = "PhaseVROOT.1_dynamic_pipeline_initialization/beam_registry.json"
_OUT_NAME     = "PhaseR2.1B_engineering_semantic_interpreter"


class PhaseR21BOrchestratorError(Exception):
    pass


class PhaseR21BOrchestrator:

    MODEL_VERSION = "8.9.0"
    PHASE_ID      = "R.2.1B"

    def __init__(
        self,
        engine_root: Optional[pathlib.Path] = None,
        output_root: Optional[pathlib.Path] = None,
        output_dir: Optional[pathlib.Path] = None,
        # Back-compat alias used by older callers
        v7_root: Optional[pathlib.Path] = None,
    ):
        root = engine_root if engine_root is not None else v7_root
        if root is None:
            raise ValueError("engine_root (or v7_root) is required")
        self._engine = pathlib.Path(root)
        self._output_root = pathlib.Path(output_root) if output_root else (self._engine / "data" / "output")
        self._out = pathlib.Path(output_dir) if output_dir else (self._output_root / _OUT_NAME)
        self._out.mkdir(parents=True, exist_ok=True)
        # Alias for any remaining internal references during transition
        self._v7 = self._engine

    # ── Public entry point ───────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        _banner(self.MODEL_VERSION)

        timings: Dict[str, float] = {}

        # ── Step 1: Load R.1 annotations ─────────────────────────────────────
        print("[1/8] Loading R.1 annotations ...")
        t = time.perf_counter()
        annotations_by_beam = self._load_annotations()
        total_anns = sum(len(v) for v in annotations_by_beam.values())
        timings["load_annotations"] = round(time.perf_counter() - t, 3)
        print(f"      {len(annotations_by_beam)} beams, {total_anns} annotations")

        # ── Step 2: Bootstrap Semantic Dictionary (R.2.1A) ───────────────────
        print("[2/8] Loading Semantic Dictionary (R.2.1A) ...")
        t = time.perf_counter()
        dictionary_entries, vocabulary_map = self._load_semantic_dictionary()
        timings["load_dictionary"] = round(time.perf_counter() - t, 3)
        print(f"      {len(dictionary_entries)} dictionary entries, "
              f"{len(vocabulary_map)} vocabulary aliases")

        # ── Step 3: Interpret all annotations ───────────────────────────────
        print("[3/8] Interpreting annotations ...")
        t = time.perf_counter()
        interpreter = SemanticInterpreter(dictionary_entries, vocabulary_map)
        esos_by_beam = interpreter.interpret_all(annotations_by_beam)
        total_esos = sum(len(v) for v in esos_by_beam.values())
        timings["interpret"] = round(time.perf_counter() - t, 3)
        overrides = sum(1 for e in _flat(esos_by_beam) if e.role_overridden)
        print(f"      {total_esos} semantic objects produced, {overrides} role overrides")
        self._print_key_examples(esos_by_beam)

        # ── Step 4: Build enriched R.1 models JSON ───────────────────────────
        print("[4/8] Building enriched R.1 models JSON ...")
        t = time.perf_counter()
        enriched_path = self._build_enriched_models(esos_by_beam, annotations_by_beam)
        timings["enrich"] = round(time.perf_counter() - t, 3)
        print(f"      Enriched model: {enriched_path.name}")

        # ── Step 5: Run production pipeline ──────────────────────────────────
        print("[5/8] Running production pipeline with enriched models ...")
        t = time.perf_counter()
        production_result = self._run_production(enriched_path)
        timings["production"] = round(time.perf_counter() - t, 3)
        steel = production_result.get("total_steel_kg", 0)
        wb    = production_result.get("workbook_generated", False)
        print(f"      Steel: {steel:.1f} kg  |  Workbook: {'YES' if wb else 'NO'}")

        # ── Step 6: Validate ─────────────────────────────────────────────────
        print("[6/8] Running 12-rule validation ...")
        t = time.perf_counter()
        validator = SemanticValidation()
        validation = validator.validate(
            esos_by_beam         = esos_by_beam,
            annotations_by_beam  = annotations_by_beam,
            workbook_generated   = wb,
        )
        timings["validate"] = round(time.perf_counter() - t, 3)
        print(f"      {validation['summary']}")

        # ── Step 7: Statistics ───────────────────────────────────────────────
        print("[7/8] Computing statistics ...")
        statistics = SemanticStatistics().compute(esos_by_beam)

        # ── Step 8: Export ───────────────────────────────────────────────────
        print("[8/8] Exporting artefacts ...")
        reporter  = SemanticReporter()
        report_md = reporter.generate(statistics, validation, production_result, self.MODEL_VERSION)
        exporter  = SemanticExport(self._out)
        exported  = exporter.export_all(
            esos_by_beam     = esos_by_beam,
            statistics       = statistics,
            validation       = validation,
            report_md        = report_md,
            production_result= production_result,
        )
        print(f"      {len(exported)} artefacts written to {self._out}")

        elapsed = round(time.perf_counter() - t0, 2)
        _print_summary(validation, statistics, production_result, elapsed)

        return {
            "model_version":   self.MODEL_VERSION,
            "phase":           self.PHASE_ID,
            "total_annotations": total_anns,
            "total_esos":      total_esos,
            "role_overrides":  overrides,
            "validation":      validation,
            "statistics":      statistics,
            "production":      production_result,
            "output_dir":      str(self._out),
            "timings":         timings,
            "elapsed_seconds": elapsed,
        }

    # ── Load helpers ─────────────────────────────────────────────────────────

    def _load_annotations(self) -> Dict[str, List[Dict[str, Any]]]:
        ann_path = self._output_root / _R1_ANN_REL
        if not ann_path.exists():
            raise PhaseR21BOrchestratorError(f"Annotations not found: {ann_path}")
        data = json.loads(ann_path.read_text(encoding="utf-8"))
        return data.get("by_beam", {})

    def _load_semantic_dictionary(self) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Bootstrap R.2.1A semantic dictionary loader."""
        r21a_dir = self._engine / "src/PhaseR2.1A_engineering_semantic_dictionary"
        if not r21a_dir.exists():
            log.warning("R.2.1A not found — using empty dictionary")
            return {}, {}

        pkg_name = "PhaseR21A"
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(r21a_dir)]
            sys.modules[pkg_name] = pkg

        for sub in [
            "__init__",
            "semantic_dictionary_models",
            "semantic_dictionary_cache",
            "semantic_dictionary_versioning",
            "notation_inventory_loader",
            "engineering_vocabulary_resolver",
            "semantic_dictionary_builder",
            "semantic_dictionary_loader",
        ]:
            mod_key = f"{pkg_name}.{sub}"
            if mod_key not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    mod_key, r21a_dir / f"{sub}.py"
                )
                if spec is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = pkg_name
                sys.modules[mod_key] = mod
                spec.loader.exec_module(mod)

        loader_mod = sys.modules.get(f"{pkg_name}.semantic_dictionary_loader")
        if loader_mod is None:
            return {}, {}

        loader = loader_mod.SemanticDictionaryLoader(self._engine)
        try:
            dictionary = loader.load()
        except Exception as exc:
            log.warning("Dictionary load failed: %s — using empty dict", exc)
            return {}, {}

        # Flatten entries to plain dicts
        entries_dict: Dict[str, Any] = {}
        for key, entry in dictionary.entries.items():
            try:
                import dataclasses
                entries_dict[key] = dataclasses.asdict(entry)
            except Exception:
                entries_dict[key] = {
                    "notation": key,
                    "engineering_meaning": getattr(entry, "engineering_meaning", "UNKNOWN"),
                    "engineering_role":    getattr(entry, "engineering_role", None),
                    "position":            getattr(entry, "position", None),
                    "category":            getattr(entry, "category", "UNKNOWN"),
                }

        vocab_map: Dict[str, str] = {}
        for alias, canonical in dictionary.vocabulary_map.items():
            vocab_map[alias] = canonical

        return entries_dict, vocab_map

    # ── Enriched model builder ───────────────────────────────────────────────

    def _build_enriched_models(
        self,
        esos_by_beam: Dict[str, List[EngineeringSemanticObject]],
        annotations_by_beam: Dict[str, List[Dict[str, Any]]],
    ) -> pathlib.Path:
        """
        Patch the R.1 beam_reinforcement_models.json with semantic role overrides.

        For each annotation where role_overridden=True:
          - Remove the bar label from the current (incorrect) group
          - Add it to the semantically-correct group (creating if needed)
        """
        r1_path = self._output_root / _R1_MODEL_REL
        if not r1_path.exists():
            raise PhaseR21BOrchestratorError(f"R.1 models not found: {r1_path}")

        r1_data = json.loads(r1_path.read_text(encoding="utf-8"))
        models  = copy.deepcopy(r1_data.get("models", {}))

        # Build annotation_id → ESO index for quick lookup
        ann_eso_index: Dict[str, EngineeringSemanticObject] = {
            e.annotation_id: e
            for beam_esos in esos_by_beam.values()
            for e in beam_esos
        }

        # Build bar_label → current_role for each beam
        # (needed to find which group to remove label from)
        for beam_id, esos in esos_by_beam.items():
            beam_model = models.get(beam_id, {})
            if not beam_model:
                continue
            groups = beam_model.get("groups", {})

            for eso in esos:
                if not eso.role_overridden:
                    continue

                # Determine target R.1 role from semantic role
                target_r1_role = SEMANTIC_ROLE_TO_R1_ROLE.get(eso.engineering_role)
                if target_r1_role is None:
                    continue  # MAIN/EXTRA — no fixed override

                old_r1_role = eso.original_r1_role
                bar_label   = _find_bar_label_for_eso(eso, annotations_by_beam.get(beam_id, []))

                if not bar_label:
                    log.debug("No bar label for %s — skipping enrich", eso.annotation_id)
                    continue

                # Remove from old group
                old_grp = groups.get(old_r1_role, {})
                if bar_label in old_grp.get("labels", []):
                    old_labels = list(old_grp.get("labels", []))
                    old_dias   = list(old_grp.get("diameters_mm", []))
                    # Remove first occurrence of bar_label and its paired diameter
                    idx = old_labels.index(bar_label)
                    old_labels.pop(idx)
                    if idx < len(old_dias):
                        old_dias.pop(idx)
                    old_grp["labels"]       = old_labels
                    old_grp["diameters_mm"] = old_dias
                    old_grp["total_quantity"] = max(
                        0, old_grp.get("total_quantity", 0) - eso.quantity
                    )
                    old_grp["bar_count"] = len(old_labels)
                    if not old_labels:
                        groups.pop(old_r1_role, None)
                    else:
                        groups[old_r1_role] = old_grp

                # Add to (or create) new group
                if target_r1_role not in groups:
                    groups[target_r1_role] = {
                        "group_id":      f"GRP-{beam_id}-{target_r1_role}-SEM{uuid.uuid4().hex[:6]}",
                        "role":          target_r1_role,
                        "total_quantity": 0,
                        "diameters_mm":  [],
                        "labels":        [],
                        "bar_count":     0,
                        "semantic_enriched": True,
                    }
                new_grp = groups[target_r1_role]
                if bar_label not in new_grp["labels"]:
                    new_grp["labels"].append(bar_label)
                    new_grp["diameters_mm"].append(eso.diameter)
                    new_grp["total_quantity"] = new_grp.get("total_quantity", 0) + eso.quantity
                    new_grp["bar_count"] = len(new_grp["labels"])
                    new_grp.setdefault("semantic_notes", []).append(
                        f"Semantic override: {old_r1_role} → {target_r1_role} "
                        f"(source={eso.source}, flags={eso.semantic_flags})"
                    )
                groups[target_r1_role] = new_grp
                beam_model["groups"] = groups
                models[beam_id] = beam_model

        enriched = {
            **r1_data,
            "models": models,
            "semantic_enriched": True,
            "enriched_by": "Phase R.2.1B",
            "enriched_version": self.MODEL_VERSION,
            "enriched_at": datetime.utcnow().isoformat(),
        }
        out_path = self._out / "beam_reinforcement_models_semantic.json"
        out_path.write_text(
            json.dumps(enriched, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return out_path

    # ── Production pipeline ──────────────────────────────────────────────────

    def _run_production(self, enriched_r1_path: pathlib.Path) -> Dict[str, Any]:
        """
        Run production pipeline with enriched R.1 model.

        Strategy:
          1. Bootstrap R.1.3 EngineeringBarBuilder with enriched_r1_path
          2. Produce L2-compatible beam models
          3. Write to a new intermediate JSON
          4. Bootstrap VB1 with that JSON
        """
        try:
            reg_path = self._output_root / _REG_REL
            l2_path  = self._out / "beam_reinforcement_models_semantic_l2.json"

            # Bootstrap R.1.3 EngineeringBarBuilder
            ctx = self._load_engineering_context()
            bar_builder = self._bootstrap_bar_builder(enriched_r1_path, reg_path, ctx)
            beam_models, build_stats = bar_builder.build_all()
            l2_data = bar_builder.to_l2_compatible(beam_models)
            l2_data["source"] = "Phase R.2.1B — Semantic Enriched Pipeline"
            l2_data["model_version"] = self.MODEL_VERSION
            l2_path.write_text(
                json.dumps(l2_data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(f"      L2 model: {build_stats['total_bars']} bars across "
                  f"{build_stats['beams_with_bars']} beams")

            # Bootstrap VB1
            vb1_result = self._bootstrap_vb1(l2_path)
            return vb1_result

        except Exception as exc:
            log.error("Production pipeline error: %s", exc, exc_info=True)
            return {
                "total_steel_kg": 0.0,
                "beams_reaching_steel": 0,
                "bbs_rows": 0,
                "workbook_generated": False,
                "error": str(exc),
            }

    def _load_engineering_context(self) -> Dict[str, Any]:
        try:
            r2a_dir = self._v7 / "src/PhaseR.2A_engineering_context"
            pkg_name = "PhaseR2A"
            if pkg_name not in sys.modules:
                pkg = types.ModuleType(pkg_name)
                pkg.__path__ = [str(r2a_dir)]
                sys.modules[pkg_name] = pkg

            mod_key = f"{pkg_name}.engineering_context_parser"
            if mod_key not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    mod_key, r2a_dir / "engineering_context_parser.py"
                )
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = pkg_name
                sys.modules[mod_key] = mod
                spec.loader.exec_module(mod)

            parser = sys.modules[mod_key]
            loader, _, _ = parser.parse_engineering_context(self._v7)
            return loader.summary() if loader else {}
        except Exception:
            return {}

    def _bootstrap_bar_builder(self, r1_path, reg_path, ctx):
        r13_dir  = self._v7 / "src/PhaseR1.3_pipeline_integration"
        pkg_name = "PhaseR13"

        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(r13_dir)]
            sys.modules[pkg_name] = pkg

        for sub in [
            "engineering_bar_model",
            "engineering_bar_builder",
        ]:
            mod_key = f"{pkg_name}.{sub}"
            if mod_key not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    mod_key, r13_dir / f"{sub}.py"
                )
                if spec is None:
                    raise ImportError(f"Cannot find {sub} in {r13_dir}")
                mod = importlib.util.module_from_spec(spec)
                mod.__package__ = pkg_name
                sys.modules[mod_key] = mod
                spec.loader.exec_module(mod)

        ebb_mod = sys.modules[f"{pkg_name}.engineering_bar_builder"]
        return ebb_mod.EngineeringBarBuilder(r1_path, reg_path, ctx)

    def _bootstrap_vb1(self, l2_path: pathlib.Path) -> Dict[str, Any]:
        vb1_dir = self._v7 / "src/PhaseVB.1_production_output_completion"
        if str(vb1_dir) not in sys.path:
            sys.path.insert(0, str(vb1_dir))

        try:
            if "phase_vb1_orchestrator" not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    "phase_vb1_orchestrator",
                    vb1_dir / "phase_vb1_orchestrator.py",
                )
                mod = importlib.util.module_from_spec(spec)
                sys.modules["phase_vb1_orchestrator"] = mod
                spec.loader.exec_module(mod)

            vb1_mod = sys.modules["phase_vb1_orchestrator"]
            vb1 = vb1_mod.PhaseVB1Orchestrator(
                v7_root=self._v7,
                l2_path=l2_path,
                use_r13_integration=False,
            )
            result_obj = vb1.run()
            return _extract_vb1_result(result_obj)

        except Exception as exc:
            log.error("VB1 bootstrap error: %s", exc, exc_info=True)
            return {
                "total_steel_kg": 0.0,
                "beams_reaching_steel": 0,
                "bbs_rows": 0,
                "workbook_generated": False,
                "error": str(exc),
            }

    # ── Debug helpers ────────────────────────────────────────────────────────

    def _print_key_examples(
        self, esos_by_beam: Dict[str, List[EngineeringSemanticObject]]
    ) -> None:
        all_esos = _flat(esos_by_beam)
        overrides = [e for e in all_esos if e.role_overridden]
        if overrides:
            print(f"      Key overrides ({min(3, len(overrides))} shown):")
            for e in overrides[:3]:
                print(f"        {e.beam_id}/{e.annotation_id}: "
                      f"{e.original_r1_role} -> {e.engineering_role} "
                      f"[{e.engineering_meaning}] mods={e.modifiers}")


# ── Module helpers ───────────────────────────────────────────────────────────

def _flat(esos_by_beam: Dict[str, List[EngineeringSemanticObject]]) -> List[EngineeringSemanticObject]:
    return [e for elist in esos_by_beam.values() for e in elist]


def _find_bar_label_for_eso(
    eso: EngineeringSemanticObject,
    annotations: List[Dict[str, Any]],
) -> str:
    for ann in annotations:
        if ann.get("annotation_id") == eso.annotation_id:
            return ann.get("bar_label", "")
    return ""


def _extract_vb1_result(result_obj) -> Dict[str, Any]:
    """Extract plain dict from VB1 ProductionOutputResult or dict."""
    if isinstance(result_obj, dict):
        r = result_obj
        steel = r.get("steel_weight_kg") or r.get("total_steel_kg") or 0.0
        wb    = bool(r.get("workbook_path") or r.get("workbook_generated"))
        beams = r.get("beam_count") or r.get("beams_reaching_steel") or 0
        bbs   = r.get("bbs_row_count") or r.get("bbs_rows") or 0
    else:
        # ProductionOutputResult dataclass
        steel = getattr(result_obj, "steel_weight_kg", 0.0)
        wb    = bool(
            getattr(result_obj, "workbook_path", "")
            or getattr(result_obj, "workbook_validated", False)
        )
        beams = getattr(result_obj, "beam_count", 0)
        bbs   = getattr(result_obj, "bbs_row_count", 0)

    return {
        "total_steel_kg":      float(steel),
        "beams_reaching_steel": int(beams),
        "beams_reaching_bbs":  int(bbs),
        "bbs_rows":            int(bbs),
        "workbook_generated":  wb,
    }


def _banner(version: str) -> None:
    print(f"\n{'=' * 70}")
    print("  PHASE R.2.1B — Engineering Semantic Interpreter")
    print(f"  MODEL_VERSION {version}  |  {datetime.utcnow().isoformat()}")
    print(f"{'=' * 70}\n")


def _print_summary(
    validation: Dict[str, Any],
    statistics: Dict[str, Any],
    production: Dict[str, Any],
    elapsed: float,
) -> None:
    print(f"\n{'=' * 70}")
    print("  PHASE R.2.1B COMPLETE")
    print(f"  Validation: {validation.get('summary', 'N/A')}")
    print(f"  Objects: {statistics.get('total_semantic_objects', 0)}")
    print(f"  Overrides: {statistics.get('role_overrides', 0)}")
    print(f"  Coverage: {statistics.get('semantic_coverage_pct', 0):.1f}%")
    steel = production.get("total_steel_kg", 0)
    wb    = production.get("workbook_generated", False)
    print(f"  Steel: {steel:.1f} kg  |  Workbook: {'YES' if wb else 'NO'}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"{'=' * 70}\n")
