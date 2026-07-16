"""Build end-to-end annotation trace records."""
from __future__ import annotations
from typing import Any, Dict, List

from .annotation_inventory import PipelineDataLoader
from .annotation_trace_models import AnnotationInventoryItem, AnnotationTraceRecord


class AnnotationTraceBuilder:

    def build_all(self, loader: PipelineDataLoader) -> List[AnnotationTraceRecord]:
        records = []
        for item in loader.inventory:
            records.append(self._trace_one(item, loader))
        return records

    def _trace_one(
        self, item: AnnotationInventoryItem, loader: PipelineDataLoader
    ) -> AnnotationTraceRecord:
        rec = AnnotationTraceRecord(
            annotation_id=item.annotation_id,
            beam_id=item.beam_id,
            normalized_text=item.normalized_text,
            diameter_mm=item.diameter_mm,
            role=item.semantic_role,
        )

        if item.source == "DXF_FORENSIC":
            rec.first_loss_stage = "AnnotationDiscovery"
            rec.root_cause = "REGEX_NOT_MATCHED"
            rec.status = "LOST"
            return rec

        if not item.is_reinforcement:
            rec.first_loss_stage = "AnnotationDiscovery"
            rec.root_cause = "CLASSIFIER_FILTERED"
            rec.status = "IGNORED"
            return rec

        grp = loader.group_for_annotation(item)
        if not grp:
            rec.first_loss_stage = "ReinforcementGroupBuilder"
            rec.root_cause = "GROUP_MERGED"
            rec.status = "LOST"
            return rec

        rec.group_id = grp.get("group_id", "")
        labels = grp.get("labels", [])
        rec.group_merged = len(labels) > 1 and item.normalized_text in labels
        rec.group_expanded = labels.count(item.normalized_text) > 1

        eng_bars = loader.eng_bars_for_group(
            item.beam_id, rec.group_id, item.semantic_role, item.normalized_text
        )
        if not eng_bars:
            rec.first_loss_stage = "EngineeringBarBuilder"
            rec.root_cause = "ENGINEERING_BAR_NOT_CREATED"
            rec.status = "LOST"
            return rec

        rec.engineering_bar_ids = [
            f"{item.beam_id}::{b.get('bar_role')}::{b.get('bar_label')}"
            for b in eng_bars
        ]
        if len(eng_bars) > 1:
            rec.root_cause = "ENGINEERING_BAR_DUPLICATED"

        steel_role = self._steel_role(item.semantic_role)
        steel_hit = self._match_steel(item, steel_role, loader)
        rec.steel_consumed = steel_hit is not None
        if not rec.steel_consumed:
            rec.first_loss_stage = "SteelWeightCompletion"
            rec.root_cause = rec.root_cause or "STEEL_SKIPPED"
            rec.status = "LOST"
            return rec

        rec.bbs_consumed = self._match_bbs(item, steel_hit, loader)
        if not rec.bbs_consumed:
            rec.first_loss_stage = "BBSCompletionEngine"
            rec.root_cause = "BBS_SKIPPED"
            rec.status = "LOST"
            return rec

        dia = int(item.diameter_mm)
        rec.diameter_bucket = f"Y{dia}"
        dia_in_summary = any(
            d.get("diameter_mm") == dia
            for d in loader.steel_json.get("diameter_summary", [])
        )
        if not dia_in_summary and dia > 0:
            rec.first_loss_stage = "DiameterSummary"
            rec.root_cause = "DIAMETER_SKIPPED"
            rec.status = "LOST"
            return rec

        rec.beam_total = item.beam_id in {
            b.get("beam_id")
            for b in loader.steel_json.get("beam_weights", [])
        }
        rec.excel_reached = loader.workbook_path is not None and rec.bbs_consumed
        if item.semantic_role == "STIRRUP" and steel_hit:
            rec.root_cause = rec.root_cause or "STIRRUP_ENGINE_REPLACED"

        rec.status = "CONSUMED" if rec.excel_reached else "PARTIAL"
        return rec

    @staticmethod
    def _steel_role(role: str) -> str:
        return {
            "SPACER_BAR": "SPACER",
            "SIDE_FACE_REINFORCEMENT": "SIDE_FACE",
        }.get(role, role)

    def _match_steel(
        self, item: AnnotationInventoryItem, steel_role: str, loader: PipelineDataLoader
    ):
        if not loader.steel_summary_computed:
            return None
        for bw in loader.steel_summary_computed.beam_weights:
            if bw.beam_id != item.beam_id:
                continue
            for bar in bw.bar_weights:
                if bar.role != steel_role:
                    continue
                if int(bar.diameter_mm) != int(item.diameter_mm):
                    continue
                if item.normalized_text and bar.bar_label == item.normalized_text:
                    return bar
                if int(bar.quantity) == item.quantity:
                    return bar
        return None

    def _match_bbs(self, item, steel_bar, loader) -> bool:
        for row in loader.bbs_rows_computed:
            if row.is_beam_header:
                continue
            if row.beam_id != item.beam_id:
                continue
            if abs(float(row.diameter_mm or 0) - item.diameter_mm) < 0.1:
                if steel_bar and row.total_weight_kg:
                    if abs(row.total_weight_kg - steel_bar.total_weight_kg) < 1.0:
                        return True
                if int(row.quantity or 0) == item.quantity:
                    return True
        return False
