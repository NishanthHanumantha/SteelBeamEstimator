"""
Phase V.ROOT.1 -- phase_vroot1_orchestrator.py
Mandatory entry point for the complete engineering pipeline.

Sequence:
    1. Discover project from input folder
    2. Build drawing manifest
    3. Discover beams dynamically from DXF
    4. Build beam registry
    5. Initialize engineering objects (writes V5 adapter files)
    6. Build pipeline context
    7. Check dependencies
    8. Validate (9 rules)
    9. Collect statistics
    10. Generate report
    11. Export 8 artefacts

MODEL_VERSION: 7.1.0
"""
from __future__ import annotations

import pathlib
import time
from datetime import datetime
from typing import Any, Dict, Optional

from project_discovery          import ProjectDiscovery
from drawing_manifest_builder   import DrawingManifestBuilder
from drawing_classifier         import DrawingClassifier
from project_context_builder    import ProjectContextBuilder
from dynamic_beam_discovery     import DynamicBeamDiscovery
from beam_registry_builder      import BeamRegistryBuilder
from engineering_object_initializer import EngineeringObjectInitializer
from pipeline_context_builder   import PipelineContextBuilder
from dependency_checker         import DependencyChecker
from initialization_validator   import InitializationValidator, PIPELINE_INITIALIZATION_ERROR
from initialization_statistics  import InitializationStatistics
from initialization_reporter    import InitializationReporter
from initialization_export      import InitializationExport

MODEL_VERSION = "7.1.0"
PHASE_ID      = "V.ROOT.1"

_ROOT = pathlib.Path(__file__).resolve().parents[3]   # SteelBeamEstimator/
_V7   = _ROOT / "Version8"


class PhaseVROOT1Orchestrator:
    """
    Mandatory pipeline entry point.
    Accepts ANY input folder and produces dynamic engineering objects
    ready for L.2 and all downstream phases.
    """

    def __init__(
        self,
        input_folder: Optional[pathlib.Path] = None,
        write_adapters: bool = True,
        raise_on_failure: bool = True,
    ) -> None:
        self._input = input_folder or self._default_input()
        self._write_adapters  = write_adapters
        self._raise_on_failure = raise_on_failure

    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        print()
        print("=" * 72)
        print("Phase V.ROOT.1 -- Dynamic DXF Discovery & Pipeline Initialization")
        print(f"MODEL_VERSION : {MODEL_VERSION}")
        print(f"Input folder  : {self._input}")
        print("=" * 72)

        # STEP 1 — Project discovery
        print("\n[STEP 1] Project discovery ...")
        disc = ProjectDiscovery()
        project_manifest = disc.discover(self._input)
        print(f"  Project       : {project_manifest['project_name']}")
        print(f"  Building      : {project_manifest['building']}")
        print(f"  Floor         : {project_manifest['floor']}")
        print(f"  DXF files     : {project_manifest['dxf_count']}")

        # STEP 2 — Drawing manifest
        print("\n[STEP 2] Building drawing manifest ...")
        dmb = DrawingManifestBuilder()
        drawing_manifest = dmb.build(self._input)
        print(f"  Total drawings: {drawing_manifest['total_drawings']}")
        print(f"  Type counts   : {drawing_manifest['type_counts']}")
        print(f"  Reinf. DXF    : {drawing_manifest.get('primary_reinforcement_drawing', 'NOT FOUND')}")

        # STEP 3 — Dynamic beam discovery from DXF
        print("\n[STEP 3] Dynamic beam discovery from DXF ...")
        primary_dxf = drawing_manifest.get('primary_reinforcement_drawing')
        if not primary_dxf:
            print("  [WARN] No reinforcement DXF found -- trying all DXF files")
            dxf_files = project_manifest.get('dxf_files', [])
            primary_dxf = dxf_files[0] if dxf_files else None

        if primary_dxf:
            discoverer = DynamicBeamDiscovery(cluster_radius=500.0)
            discovery_result = discoverer.discover(pathlib.Path(primary_dxf))
        else:
            discovery_result = {
                'dxf_path': '', 'dxf_stem': '', 'beam_count': 0,
                'total_text_entities': 0, 'label_entities': 0,
                'cluster_count': 0, 'elapsed_s': 0.0,
                'beams': [], 'raw_labels': [], 'error': 'No DXF file found',
            }

        print(f"  Text entities : {discovery_result['total_text_entities']}")
        print(f"  Label matches : {discovery_result['label_entities']}")
        print(f"  Beams found   : {discovery_result['beam_count']}")
        print(f"  Parse time    : {discovery_result['elapsed_s']:.2f}s")
        if discovery_result.get('error'):
            print(f"  [WARN] {discovery_result['error']}")

        # STEP 4 — Beam registry
        print("\n[STEP 4] Building beam registry ...")
        rrb = BeamRegistryBuilder()
        beam_registry = rrb.build(
            discovery_result=discovery_result,
            project_id=project_manifest['project_id'],
            drawing_path=primary_dxf or '',
        )
        print(f"  Beams registered : {beam_registry['beam_count']}")
        if beam_registry['beam_ids']:
            ids_preview = beam_registry['beam_ids'][:10]
            more = f" ... (+{beam_registry['beam_count']-10} more)" if beam_registry['beam_count'] > 10 else ''
            print(f"  Beam IDs (first 10): {ids_preview}{more}")

        # STEP 5 — Engineering objects
        print("\n[STEP 5] Initializing engineering objects ...")
        ctx_builder = ProjectContextBuilder()
        project_context = ctx_builder.build(project_manifest, drawing_manifest, beam_registry)

        initializer = EngineeringObjectInitializer(
            write_adapters=self._write_adapters,
            backup=True,
        )
        eng_obj_result = initializer.initialize(beam_registry, project_context)
        print(f"  Beam schedule entries : {eng_obj_result['objects_generated']['beam_schedule']}")
        print(f"  Engineering objects   : {eng_obj_result['objects_generated']['engineering_objects']}")
        print(f"  Adapter files written : {len(eng_obj_result.get('adapter_paths', {}))}")
        for k, v in eng_obj_result.get('adapter_paths', {}).items():
            print(f"    [{k}] -> {v}")

        # STEP 6 — Pipeline context
        print("\n[STEP 6] Building pipeline context ...")
        pcb = PipelineContextBuilder()
        pipeline_context = pcb.build(
            project_context=project_context,
            drawing_manifest=drawing_manifest,
            beam_registry=beam_registry,
            eng_obj_result=eng_obj_result,
        )
        print(f"  L.2 ready    : {pipeline_context['downstream_config']['l2_ready']}")
        print(f"  Dynamic init : {pipeline_context['quality']['dynamic_initialization']}")

        # STEP 7 — Dependency check
        print("\n[STEP 7] Checking dependencies ...")
        dc = DependencyChecker()
        dep_check = dc.check(pipeline_context, beam_registry, eng_obj_result)
        print(f"  Dependency check: {'PASS' if dep_check['dependency_check_passed'] else 'WARN'}")
        if dep_check['issues']:
            for iss in dep_check['issues']:
                print(f"  [WARN] {iss}")

        # STEP 8 — Validation (9 rules)
        print("\n[STEP 8] Validation ...")
        validator = InitializationValidator()
        validation = validator.validate(
            project_manifest=project_manifest,
            drawing_manifest=drawing_manifest,
            discovery_result=discovery_result,
            beam_registry=beam_registry,
            eng_obj_result=eng_obj_result,
            pipeline_context=pipeline_context,
            dep_check=dep_check,
        )
        for rule, passed in sorted(validation['rules_passed'].items()):
            icon = "PASS" if passed else "FAIL"
            detail = validation['rules_detail'].get(rule, '')
            print(f"  [{icon}]  {rule}: {detail}")

        if not validation['validation_passed'] and self._raise_on_failure:
            validator.raise_on_failure(validation)

        # STEP 9 — Statistics
        total_elapsed = round(time.perf_counter() - t0, 2)
        stats_module = InitializationStatistics()
        stats = stats_module.collect(
            project_manifest=project_manifest,
            drawing_manifest=drawing_manifest,
            discovery_result=discovery_result,
            beam_registry=beam_registry,
            eng_obj_result=eng_obj_result,
            pipeline_context=pipeline_context,
            dep_check=dep_check,
            validation=validation,
            total_elapsed_s=total_elapsed,
        )

        # STEP 10 — Report
        print("\n[STEP 10] Building report ...")
        reporter = InitializationReporter()
        report = reporter.build_report(
            project_manifest=project_manifest,
            drawing_manifest=drawing_manifest,
            discovery_result=discovery_result,
            beam_registry=beam_registry,
            eng_obj_result=eng_obj_result,
            pipeline_context=pipeline_context,
            dep_check=dep_check,
            validation=validation,
            stats=stats,
        )

        # STEP 11 — Export
        print("\n[STEP 11] Exporting artefacts ...")
        exporter = InitializationExport()
        export_status = exporter.export_all(
            project_manifest=project_manifest,
            drawing_manifest=drawing_manifest,
            beam_registry=beam_registry,
            eng_obj_result=eng_obj_result,
            pipeline_context=pipeline_context,
            dep_check=dep_check,
            stats=stats,
            report=report,
        )
        ev = exporter.validate_exports(export_status)
        print(f"  Exports: {ev['passed']}/{ev['total']} OK")
        print(f"  Output: {ev['output_dir']}")

        # Final summary
        print()
        print("=" * 72)
        rules_ok = f"{validation['passed_count']}/9 passed"
        status   = "COMPLETE" if validation['validation_passed'] else "COMPLETE (with warnings)"
        print(f"V.ROOT.1 {status} -- Rules: {rules_ok} -- Beams: {beam_registry['beam_count']}")
        print(f"Total elapsed: {total_elapsed:.2f}s")
        print("=" * 72)

        return {
            'model_version':    MODEL_VERSION,
            'phase':            PHASE_ID,
            'timestamp':        datetime.now().isoformat(),
            'input_folder':     str(self._input),
            'project_manifest': project_manifest,
            'drawing_manifest': drawing_manifest,
            'discovery_result': discovery_result,
            'beam_registry':    beam_registry,
            'project_context':  project_context,
            'eng_obj_result':   eng_obj_result,
            'pipeline_context': pipeline_context,
            'dep_check':        dep_check,
            'validation':       validation,
            'statistics':       stats,
            'report':           report,
            'export_validation': ev,
            'total_elapsed_s':  total_elapsed,
            'initialization_passed': validation['validation_passed'],
        }

    @staticmethod
    def _default_input() -> pathlib.Path:
        """Default to Benchmark Set 2 if no folder specified."""
        for candidate in [
            _V7 / "data/Benchmark_Set_2",
            _V7 / "data/Benchmark_Set_1",
            _V7 / "data/input",
        ]:
            if candidate.exists() and any(candidate.rglob('*.dxf')):
                return candidate
        return _V7 / "data"
