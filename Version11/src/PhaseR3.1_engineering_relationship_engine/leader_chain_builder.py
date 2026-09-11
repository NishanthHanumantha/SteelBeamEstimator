"""
leader_chain_builder.py — Build leader chains from individual leader segments.
MODEL_VERSION: 8.1.0

In some drawings, leaders are composed of multiple connected segments.
This module chains connected LeaderObjects into a single logical leader chain.

Chain connection criterion: the tail of one leader is within
CHAIN_JOIN_THRESHOLD_MM of the tip of another.

No engineering interpretation — purely geometric chaining.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from .relationship_models import LeaderObject

CHAIN_JOIN_THRESHOLD_MM = 50.0


def _dist(p1: Tuple, p2: Tuple) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


class LeaderChainBuilder:
    """
    Group connected leaders into chains.
    Each chain represents a complete annotation → bar connection.
    """

    def build_chains(
        self, leaders: List[LeaderObject]
    ) -> Dict[str, List[str]]:
        """
        Returns: {chain_id: [leader_id, ...]} mapping.
        For most leaders, the chain contains a single leader_id.
        """
        # Simple approach: most leaders in structural drawings are single-segment
        # Use chain only when two leaders connect tip-to-tail
        chains: Dict[str, List[str]] = {}
        used: set = set()

        leader_by_id = {l.leader_id: l for l in leaders}

        chain_idx = 0
        for ldr in leaders:
            if ldr.leader_id in used:
                continue
            chain = [ldr.leader_id]
            used.add(ldr.leader_id)

            # Look for continuation: another leader whose tail is near this tip
            for other in leaders:
                if other.leader_id in used:
                    continue
                d_tail_to_tip = _dist(
                    (other.tail_x, other.tail_y),
                    (ldr.tip_x, ldr.tip_y),
                )
                if d_tail_to_tip <= CHAIN_JOIN_THRESHOLD_MM:
                    chain.append(other.leader_id)
                    used.add(other.leader_id)

            chain_id = f"CHAIN::{chain_idx:04d}"
            chains[chain_id] = chain
            chain_idx += 1

        return chains
