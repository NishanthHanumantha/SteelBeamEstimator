"""
Cluster raw findings into EngineeringIssue groups.
MODEL_VERSION: 8.7.0
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from error_classifier import ErrorClassifier
from engineering_issue_model import RawFinding

MODEL_VERSION = "8.7.0"


class ErrorClusterEngine:
    """Cluster by (category, subcategory) — never report findings independently."""

    def __init__(self):
        self._classifier = ErrorClassifier()

    def cluster(self, findings: List[RawFinding]) -> Dict[Tuple[str, str], List[RawFinding]]:
        buckets: Dict[Tuple[str, str], List[RawFinding]] = defaultdict(list)
        for finding in findings:
            info = self._classifier.classify(finding.error_type, finding.message, finding.entity)
            # enrich finding in place via replacement list values
            finding.role = info["role"] or finding.role
            finding.diameter = info["diameter"] or finding.diameter
            key = (info["category"], info["subcategory"])
            buckets[key].append(finding)
        # deterministic key order
        return {k: buckets[k] for k in sorted(buckets.keys(), key=lambda x: (x[0], x[1]))}

    def cluster_summary(self, clusters: Dict[Tuple[str, str], List[RawFinding]]) -> List[Dict[str, Any]]:
        out = []
        for (cat, sub), items in clusters.items():
            beams = sorted({f.entity for f in items if f.entity and f.entity not in ("*", "PROJECT")})
            out.append({
                "category": cat,
                "subcategory": sub,
                "frequency": len(items),
                "affected_beams": beams,
                "finding_ids": [f.finding_id for f in items],
            })
        return out
