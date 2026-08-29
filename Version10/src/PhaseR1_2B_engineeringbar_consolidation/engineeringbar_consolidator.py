"""
EngineeringBarConsolidator — merge duplicate evidence into Physical Members.
MODEL_VERSION: 8.3.1

Merges only when evidence strongly indicates the same physical reinforcement.
Does NOT sum quantities. Preserves full evidence lineage.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Tuple

from .engineeringbar_duplicate_detector import (
    EngineeringBarDuplicateDetector,
    similarity_score,
)
from .physical_reinforcement_model import PhysicalReinforcementMember

MODEL_VERSION = "8.3.1"


class EngineeringBarConsolidator:
    """Consolidate EngineeringBars into PhysicalReinforcementMembers."""

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self._detector = EngineeringBarDuplicateDetector(threshold=threshold)

    def consolidate(
        self, beam_models: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Returns:
          consolidated_beam_models (same schema as input, bars replaced)
          consolidation_report
        """
        audit_before = self._detector.audit(beam_models)
        detection = self._detector.detect(beam_models)

        # Index duplicate groups by beam
        groups_by_beam: Dict[str, List[Dict[str, Any]]] = {}
        for g in detection.get("groups", []):
            groups_by_beam.setdefault(g["beam_id"], []).append(g)

        consolidated: List[Dict[str, Any]] = []
        physical_members: List[Dict[str, Any]] = []
        traceability: List[Dict[str, Any]] = []
        member_seq = 0

        bars_before = audit_before["total_engineering_bars"]
        bars_after = 0

        for bm in beam_models:
            bid = bm.get("beam_id")
            bars = list(bm.get("bars") or [])
            consumed = set()
            new_bars: List[Dict[str, Any]] = []

            for g in groups_by_beam.get(bid, []):
                idxs = g["member_indices"]
                for i in idxs:
                    consumed.add(i)
                member_seq += 1
                member = self._merge_bars(
                    beam_id=bid,
                    bars=[bars[i] for i in idxs],
                    indices=idxs,
                    member_seq=member_seq,
                    group_id=g["group_id"],
                )
                physical_members.append(member.to_dict())
                new_bars.append(member.to_engineering_bar_dict())
                traceability.append({
                    "member_id": member.member_id,
                    "beam_id": bid,
                    "source_indices": idxs,
                    "source_labels": member.evidence_labels,
                    "merged_evidence_ids": member.merged_evidence_ids,
                    "annotation_ids": member.annotation_ids,
                    "consolidation_reason": member.consolidation_reason,
                    "similarity_score": member.similarity_score,
                    "confidence": member.confidence,
                })

            # Unmerged bars become singleton physical members
            for i, bar in enumerate(bars):
                if i in consumed:
                    continue
                member_seq += 1
                member = self._singleton(bid, bar, i, member_seq)
                physical_members.append(member.to_dict())
                new_bars.append(member.to_engineering_bar_dict())
                traceability.append({
                    "member_id": member.member_id,
                    "beam_id": bid,
                    "source_indices": [i],
                    "source_labels": member.evidence_labels,
                    "merged_evidence_ids": member.merged_evidence_ids,
                    "annotation_ids": member.annotation_ids,
                    "consolidation_reason": "singleton_unique_physical_member",
                    "similarity_score": 1.0,
                    "confidence": member.confidence,
                })

            bars_after += len(new_bars)
            out_bm = dict(bm)
            out_bm["bars"] = new_bars
            out_bm["bar_count"] = len(new_bars)
            out_bm["consolidation_phase"] = "R.1.2B"
            consolidated.append(out_bm)

        report = {
            "model_version": MODEL_VERSION,
            "threshold": self.threshold,
            "bars_before": bars_before,
            "bars_after": bars_after,
            "bars_removed_as_duplicates": bars_before - bars_after,
            "duplicate_groups_merged": detection.get("duplicate_group_count", 0),
            "physical_member_count": len(physical_members),
            "detection": {
                "duplicate_group_count": detection.get("duplicate_group_count"),
                "redundant_bar_count": detection.get("redundant_bar_count"),
            },
        }
        return consolidated, {
            "report": report,
            "audit_before": audit_before,
            "detection": detection,
            "physical_members": physical_members,
            "traceability": traceability,
        }

    def _merge_bars(
        self,
        beam_id: str,
        bars: List[Dict[str, Any]],
        indices: List[int],
        member_seq: int,
        group_id: str,
    ) -> PhysicalReinforcementMember:
        # Canonical bar: prefer most common quantity, then first
        qty_counts = Counter(int(b.get("quantity") or 0) for b in bars)
        best_qty = qty_counts.most_common(1)[0][0]
        canonical = next(
            (b for b in bars if int(b.get("quantity") or 0) == best_qty),
            bars[0],
        )

        labels = []
        for b in bars:
            lbl = b.get("bar_label") or ""
            if lbl and lbl not in labels:
                labels.append(lbl)

        # Mean pairwise similarity among group
        scores = []
        for i in range(len(bars)):
            for j in range(i + 1, len(bars)):
                s, _ = similarity_score(bars[i], bars[j])
                scores.append(s)
        mean_sim = round(sum(scores) / len(scores), 4) if scores else 1.0

        evidence_ids = [f"{beam_id}::{i}" for i in indices]
        annotation_ids = []
        intent_ids = []
        for b in bars:
            meta = b.get("engineering_metadata") or {}
            for key in ("annotation_id", "group_id", "source_annotation_id"):
                if meta.get(key):
                    annotation_ids.append(str(meta[key]))
            for aid in meta.get("annotation_ids") or []:
                annotation_ids.append(str(aid))
            if meta.get("intent_id"):
                intent_ids.append(str(meta["intent_id"]))

        canon_meta = dict(canonical.get("engineering_metadata") or {})
        return PhysicalReinforcementMember(
            member_id=f"PRM::{beam_id}::{member_seq:04d}",
            beam_id=beam_id,
            bar_role=str(canonical.get("bar_role")),
            diameter_mm=float(canonical.get("diameter_mm") or 0),
            quantity=int(best_qty),
            zone=str(canonical.get("zone") or ""),
            spacing_mm=canonical.get("spacing_mm"),
            development_length_mm=canonical.get("development_length_mm"),
            cover_mm=canonical.get("cover_mm"),
            steel_grade=str(canonical.get("steel_grade") or "Y"),
            concrete_grade=str(canonical.get("concrete_grade") or "M30"),
            hook_rule=canonical.get("hook_rule"),
            lap_rule_mm=canonical.get("lap_rule_mm"),
            bar_label=str(canonical.get("bar_label") or (labels[0] if labels else "")),
            source_phase="R.1.2B",
            evidence_bar_indices=list(indices),
            evidence_labels=labels,
            annotation_ids=annotation_ids,
            merged_evidence_ids=evidence_ids,
            consolidation_reason=(
                f"Merged {len(bars)} EngineeringBars via {group_id} "
                f"(same physical reinforcement; quantity not summed)"
            ),
            similarity_score=mean_sim,
            confidence=min(1.0, 0.7 + 0.1 * len(bars)),
            engineering_metadata={
                **{k: canon_meta[k] for k in (
                    "extent", "continuity", "support_type", "layer",
                    "intent_confidence", "role_confidence",
                    "diameter_confidence", "extent_confidence",
                    "intent_reason", "detail_id", "piece_id", "support_region",
                    "curtailment_type", "spacing_pattern",
                    "stirrup_zone_count", "stirrup_segments",
                    "development_rule", "development_source",
                    "hook_type", "anchor_type", "side_face",
                    "detail_confidence", "piece_type", "fabrication_type",
                    "shape_code", "cut_length_mm", "piece_confidence",
                    "piece_start_mm", "piece_end_mm", "evidence",
                    "validation_flags",
                ) if k in canon_meta},
                "intent_id": intent_ids[0] if intent_ids else canon_meta.get("intent_id"),
                "detail_id": canon_meta.get("detail_id"),
                "piece_id": canon_meta.get("piece_id"),
                "merged_intent_ids": intent_ids,
                "duplicate_group_id": group_id,
                "original_bar_count": len(bars),
                "classification": canon_meta.get(
                    "classification", "R.1_DXF_DISCOVERY"
                ),
            },
        )

    @staticmethod
    def _singleton(
        beam_id: str, bar: Dict[str, Any], index: int, member_seq: int
    ) -> PhysicalReinforcementMember:
        meta = bar.get("engineering_metadata") or {}
        ann = []
        for key in ("annotation_id", "group_id", "source_annotation_id"):
            if meta.get(key):
                ann.append(str(meta[key]))
        return PhysicalReinforcementMember(
            member_id=f"PRM::{beam_id}::{member_seq:04d}",
            beam_id=beam_id,
            bar_role=str(bar.get("bar_role")),
            diameter_mm=float(bar.get("diameter_mm") or 0),
            quantity=int(bar.get("quantity") or 0),
            zone=str(bar.get("zone") or ""),
            spacing_mm=bar.get("spacing_mm"),
            development_length_mm=bar.get("development_length_mm"),
            cover_mm=bar.get("cover_mm"),
            steel_grade=str(bar.get("steel_grade") or "Y"),
            concrete_grade=str(bar.get("concrete_grade") or "M30"),
            hook_rule=bar.get("hook_rule"),
            lap_rule_mm=bar.get("lap_rule_mm"),
            bar_label=str(bar.get("bar_label") or ""),
            source_phase="R.1.2B",
            evidence_bar_indices=[index],
            evidence_labels=[str(bar.get("bar_label") or "")],
            annotation_ids=ann,
            merged_evidence_ids=[f"{beam_id}::{index}"],
            consolidation_reason="singleton_unique_physical_member",
            similarity_score=1.0,
            confidence=0.9,
            engineering_metadata=dict(meta),
        )
