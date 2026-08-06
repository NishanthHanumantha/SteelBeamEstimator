"""STEP 3 — Group identical normalized notations and compute frequency."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .notation_models import NormalizedNotation, NotationGroup


class NotationPatternGrouper:

    def group(self, notations: List[NormalizedNotation]) -> List[NotationGroup]:
        buckets: Dict[str, List[NormalizedNotation]] = defaultdict(list)
        for n in notations:
            buckets[n.normalized].append(n)

        groups: List[NotationGroup] = []
        for key, items in buckets.items():
            beams = sorted({i.beam_id for i in items if i.beam_id})
            entities = sorted({i.entity_id for i in items})
            drawings = sorted({i.drawing_id for i in items if i.drawing_id})
            examples = []
            for i in items:
                if i.source_text and i.source_text not in examples:
                    examples.append(i.source_text[:120])
                if len(examples) >= 5:
                    break
            locations = [
                {"x": i.x, "y": i.y} for i in items[:20]
            ]
            groups.append(NotationGroup(
                normalized_notation=key,
                frequency=len(items),
                beam_ids=beams,
                entity_ids=entities,
                drawing_ids=drawings,
                example_texts=examples,
                locations=locations,
            ))

        groups.sort(key=lambda g: (-g.frequency, g.normalized_notation))
        return groups
