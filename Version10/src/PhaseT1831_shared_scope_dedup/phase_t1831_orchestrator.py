"""
Phase T1.8.3.1 orchestrator — Shared Engineering Scope Deduplication.
MODEL_VERSION: 9.5.4
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PhaseT183_shared_engineering_ownership.ownership_merger import (
    merge_beam_ownership,
)
from PhaseT183_shared_engineering_ownership.shared_scope_detector import (
    detect_shared_candidates,
)

from .dedup_registry import rebuild_registry_from_scopes
from .scope_dedup_qa import (
    validate_dedup,
    write_json,
    write_render_comparison,
)
from .shared_scope_deduplicator import deduplicate_scopes

MODEL_VERSION = "9.5.4"
PHASE_ID = "T1.8.3.1"
_OUT_NAME = "PhaseT1831_shared_scope_dedup"
_T183 = "PhaseT183_shared_engineering_ownership"


class PhaseT1831Orchestrator:
    def __init__(
        self,
        engine_root: Path,
        run_root: Path,
        output_root: Optional[Path] = None,
    ):
        self.engine_root = Path(engine_root)
        self.run_root = Path(run_root)
        self.output_root = (
            Path(output_root) if output_root else self.run_root / "data" / "output"
        )
        self.out_dir = self.output_root / _OUT_NAME
        self.t183_dir = self.output_root / _T183

    def run(self) -> Dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        scopes_path = self.t183_dir / "EngineeringScopes.json"
        reg_path = self.t183_dir / "SharedAnnotationRegistry.json"
        merged_path = self.t183_dir / "MergedOwnership.json"
        own_path = (
            self.output_root / "PhaseT18_beam_ownership" / "BeamOwnership.json"
        )
        graph_path = (
            self.output_root / "PhaseT17_annotation_graph" / "AnnotationGraph.json"
        )
        if not scopes_path.exists() or not reg_path.exists() or not merged_path.exists():
            return {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "success": False,
                "error": "T1.8.3 artefacts missing — run T1.8.3 first",
            }

        scopes_doc = json.loads(scopes_path.read_text(encoding="utf-8"))
        reg_before = json.loads(reg_path.read_text(encoding="utf-8"))
        merged_before = json.loads(merged_path.read_text(encoding="utf-8"))
        own_doc = json.loads(own_path.read_text(encoding="utf-8"))
        graph = json.loads(graph_path.read_text(encoding="utf-8"))

        candidates = detect_shared_candidates(
            graph=graph, ownership_by_beam=own_doc.get("by_beam") or {}
        )

        print("[T1.8.3.1] Deduplicating shared engineering scopes...")
        dedup = deduplicate_scopes(
            list(scopes_doc.get("scopes") or []), candidates=candidates
        )
        print(
            f"  shared scopes {dedup['shared_scopes_before']} -> {dedup['shared_scopes_after']}"
        )
        for d in dedup.get("duplicates_removed") or []:
            print(
                f"  removed {d.get('removed_scope_id')} kept {d.get('kept_scope_id')}"
            )

        reg_after, shared_anns = rebuild_registry_from_scopes(
            dedup["scopes"], candidates
        )

        # Runtime merge (unchanged T1.8.3 merger) from deduped registry
        merges_after: Dict[str, Dict[str, Any]] = {}
        for bid, own in (own_doc.get("by_beam") or {}).items():
            merges_after[bid] = merge_beam_ownership(
                bid,
                own,
                reg_after.get("by_beam") or {},
                enable_shared=True,
            )
        merges_before = merged_before.get("by_beam") or {}

        validation = validate_dedup(
            dedup_result=dedup,
            registry_before=reg_before,
            registry_after=reg_after,
            merges_before=merges_before,
            merges_after=merges_after,
        )

        # Artefacts
        write_json(
            self.out_dir / "EngineeringScopes.dedup.json",
            {
                "model_version": MODEL_VERSION,
                "phase_id": PHASE_ID,
                "scopes": dedup["scopes"],
                "dedup": {
                    k: dedup[k]
                    for k in (
                        "scopes_before",
                        "scopes_after",
                        "shared_scopes_before",
                        "shared_scopes_after",
                        "duplicates_removed",
                        "merge_log",
                        "registry_deduplicated",
                    )
                },
            },
        )
        write_json(self.out_dir / "SharedAnnotationRegistry.json", reg_after)
        write_json(
            self.out_dir / "MergedOwnership.json",
            {"model_version": MODEL_VERSION, "by_beam": merges_after},
        )
        write_json(
            self.out_dir / "ScopeDedupQA.json",
            {
                "phase_id": PHASE_ID,
                "model_version": MODEL_VERSION,
                "generated_at": generated_at,
                **validation,
            },
        )
        write_json(
            self.out_dir / "RegistryComparison.json",
            {
                "model_version": MODEL_VERSION,
                "before": {
                    "shared_annotation_count": reg_before.get("shared_annotation_count"),
                    "annotation_ids": sorted(
                        (reg_before.get("by_annotation") or {}).keys()
                    ),
                },
                "after": {
                    "shared_annotation_count": reg_after.get("shared_annotation_count"),
                    "annotation_ids": sorted(
                        (reg_after.get("by_annotation") or {}).keys()
                    ),
                },
                "duplicates_removed": dedup.get("duplicates_removed"),
                "sfr_registry_after": validation.get("sfr_registry_after"),
            },
        )
        write_json(
            self.out_dir / "OwnershipComparison.json",
            {
                "model_version": MODEL_VERSION,
                "focus": validation.get("ownership_comparison"),
                "expected": {
                    "B8": {"owned": 3, "shared": 1, "effective": 4},
                    "B9": {"owned": 5, "shared": 0, "effective": 5},
                    "B10": {"owned": 2, "shared": 0, "effective": 2},
                },
            },
        )
        write_render_comparison(
            self.out_dir / "RenderComparison.md",
            runtime_unchanged=bool(
                validation.get("checks", {}).get("effective_runtime_unchanged")
            ),
            ownership_cmp=validation.get("ownership_comparison") or {},
        )

        notes_src = Path(__file__).resolve().parent / "EngineeringNotes.md"
        if notes_src.exists():
            shutil.copy2(notes_src, self.out_dir / "EngineeringNotes.md")

        summary = {
            "phase_id": PHASE_ID,
            "model_version": MODEL_VERSION,
            "generated_at": generated_at,
            "success": True,
            "out_dir": str(self.out_dir),
            "validation": validation.get("visual_validation"),
            "checks": validation.get("checks"),
            "shared_scopes_before": dedup.get("shared_scopes_before"),
            "shared_scopes_after": dedup.get("shared_scopes_after"),
            "registry_annotation_ids": sorted(
                (reg_after.get("by_annotation") or {}).keys()
            ),
        }
        write_json(self.out_dir / "t1831_run_summary.json", summary)
        print(f"  validation -> {summary['validation']}")
        return summary
