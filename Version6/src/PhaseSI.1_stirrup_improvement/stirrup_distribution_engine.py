"""
Stirrup Distribution Engine — Phase SI.1 MODULE 3

Creates the deterministic zone distribution for each beam.

Rules:
  UNIFORM  — Entire beam is one zone. No splitting.
  VARIABLE — Zones already built by StirrupZoneBuilder.
             Support zones with identical spacing SHALL be merged.
             No averaging. No interpolation.
"""
from typing import List, Dict, Tuple
from stirrup_models import StirrupZone, ZoneRole, StirrupType


class StirrupDistributionEngine:
    """
    Determines which zones should be merged and partitions the zone list
    into groups that will each produce ONE BBS row.
    """

    def distribute(
        self,
        zones: List[StirrupZone],
        stirrup_type: StirrupType,
    ) -> List[List[StirrupZone]]:
        """
        Returns a list of zone-groups.
        Each group = one BBS row.

        Rules:
          UNIFORM: [[full_zone]]
          VARIABLE:
            If left and right support have same spacing → merge into one group.
            Each middle zone becomes its own group.
        """
        if not zones:
            return []

        if stirrup_type == StirrupType.UNIFORM or len(zones) == 1:
            return [zones]

        left  = [z for z in zones if z.role == ZoneRole.LEFT_SUPPORT]
        mid   = [z for z in zones if z.role == ZoneRole.MIDSPAN]
        right = [z for z in zones if z.role == ZoneRole.RIGHT_SUPPORT]

        groups: List[List[StirrupZone]] = []

        # Can left and right support zones be merged?
        if (
            left and right
            and left[-1].spacing_mm == right[0].spacing_mm
        ):
            # Merge: produces one BBS row with combined quantity
            groups.append(left + right)
        else:
            if left:
                groups.append(left)
            if right:
                groups.append(right)

        # Each midspan zone is its own group
        for z in mid:
            groups.append([z])

        # Sort: merged support first (lowest start_mm), then midspan by position
        groups.sort(key=lambda g: (
            0 if any(z.role != ZoneRole.MIDSPAN for z in g) else 1,
            g[0].start_mm,
        ))

        return groups
