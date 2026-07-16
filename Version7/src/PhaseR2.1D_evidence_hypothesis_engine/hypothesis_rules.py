"""
hypothesis_rules.py — Central deterministic ranking rules for Phase R.2.1D.
MODEL_VERSION: 7.12.1

This module defines:

  BASE_RANKINGS  — default (role, placement) → [(intent, reason), ...] table.
                   Applied before any reordering.

  REORDER_RULES  — ordered list of deterministic reordering rule descriptors.
                   Each rule is applied in sequence after base ranking.

No ML, no probabilities, no beam-specific logic, no geometry.

Derived from reference drawing engineering rules (B1, B2, B8-B10):
  - Default ordering reflects the most common engineering interpretation.
  - Reordering rules use only observable signals (R.1 role, modifier, diameter,
    semantic flag) to promote specific hypotheses.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# ── Intent constants ─────────────────────────────────────────────────────────
TOP_MAIN           = "TOP_MAIN"
TOP_EXTRA          = "TOP_EXTRA"
CONTINUOUS_TOP     = "CONTINUOUS_TOP"
SUPPORT_TOP        = "SUPPORT_TOP"
CURTAILMENT_TOP    = "CURTAILMENT_TOP"
BOTTOM_MAIN        = "BOTTOM_MAIN"
BOTTOM_EXTRA       = "BOTTOM_EXTRA"
CONTINUOUS_BOTTOM  = "CONTINUOUS_BOTTOM"
SUPPORT_BOTTOM     = "SUPPORT_BOTTOM"
CURTAILMENT_BOTTOM = "CURTAILMENT_BOTTOM"
SUPPORT_BAR        = "SUPPORT_BAR"
SPACER_BAR         = "SPACER_BAR"
CHAIR_BAR          = "CHAIR_BAR"
STIRRUP_INTENT     = "STIRRUP"
SIDE_FACE_REINF    = "SIDE_FACE_REINFORCEMENT"
CURTAILMENT_BAR    = "CURTAILMENT_BAR"
UNKNOWN_INTENT     = "UNKNOWN"

# ── Base ranking table ────────────────────────────────────────────────────────
# (role, placement) → [(intent, reason), ...]  — default priority order
BASE_RANKINGS: Dict[Tuple[str, str], List[Tuple[str, str]]] = {

    ("MAIN_BAR", "TOP"): [
        (TOP_MAIN,       "Default top longitudinal reinforcement"),
        (TOP_EXTRA,      "Possible support reinforcement"),
        (CONTINUOUS_TOP, "Possible continuous reinforcement"),
        (SUPPORT_TOP,    "Requires support geometry"),
    ],

    ("MAIN_BAR", "BOTTOM"): [
        (BOTTOM_MAIN,       "Default bottom longitudinal reinforcement"),
        (BOTTOM_EXTRA,      "Possible support zone reinforcement"),
        (CONTINUOUS_BOTTOM, "Possible continuous reinforcement"),
        (SUPPORT_BOTTOM,    "Requires support geometry"),
    ],

    ("MAIN_BAR", "UNKNOWN"): [
        (TOP_MAIN,          "Default top longitudinal reinforcement"),
        (BOTTOM_MAIN,       "Default bottom longitudinal reinforcement"),
        (TOP_EXTRA,         "Possible top support reinforcement"),
        (BOTTOM_EXTRA,      "Possible bottom support reinforcement"),
        (CONTINUOUS_TOP,    "Possible continuous top reinforcement"),
        (CONTINUOUS_BOTTOM, "Possible continuous bottom reinforcement"),
    ],

    ("EXTRA_BAR", "TOP"): [
        (TOP_EXTRA,      "Short bar over support zone"),
        (CURTAILMENT_TOP,"Curtailed top reinforcement"),
        (SUPPORT_TOP,    "Requires support geometry"),
    ],

    ("EXTRA_BAR", "BOTTOM"): [
        (BOTTOM_EXTRA,      "Short bar at bottom"),
        (CURTAILMENT_BOTTOM,"Curtailed bottom reinforcement"),
        (SUPPORT_BOTTOM,    "Requires support geometry"),
        (SUPPORT_BAR,       "Possible support bar"),
    ],

    ("EXTRA_BAR", "UNKNOWN"): [
        (TOP_EXTRA,      "Possible top extra bar"),
        (BOTTOM_EXTRA,   "Possible bottom extra bar"),
        (CURTAILMENT_BAR,"Curtailed bar — position unknown"),
        (SUPPORT_BAR,    "Possible support bar"),
    ],

    ("STIRRUP", "UNKNOWN"): [
        (STIRRUP_INTENT, "Transverse confinement reinforcement"),
    ],
    ("STIRRUP", "TOP"): [
        (STIRRUP_INTENT, "Transverse confinement reinforcement"),
    ],
    ("STIRRUP", "BOTTOM"): [
        (STIRRUP_INTENT, "Transverse confinement reinforcement"),
    ],
    ("STIRRUP", "SIDE"): [
        (STIRRUP_INTENT, "Transverse confinement reinforcement"),
    ],

    ("SIDE_FACE", "BOTH_FACE"): [
        (SIDE_FACE_REINF, "Explicit side face annotation (S.F.R.)"),
    ],
    ("SIDE_FACE", "SIDE"): [
        (SIDE_FACE_REINF, "Explicit side face annotation"),
    ],
    ("SIDE_FACE", "UNKNOWN"): [
        (SIDE_FACE_REINF, "Side face reinforcement by role"),
    ],

    ("SPACER_BAR", "TOP"): [
        (SPACER_BAR, "Bar spacer function at top"),
        (CHAIR_BAR,  "Chair/support function possible"),
    ],
    ("SPACER_BAR", "BOTTOM"): [
        (SPACER_BAR, "Bar spacer function at bottom"),
        (CHAIR_BAR,  "Chair/support function possible"),
    ],
    ("SPACER_BAR", "UNKNOWN"): [
        (SPACER_BAR, "Bar spacer function"),
        (CHAIR_BAR,  "Chair/support function possible"),
    ],

    ("UNKNOWN", "TOP"): [
        (TOP_MAIN,       "Default top longitudinal reinforcement"),
        (TOP_EXTRA,      "Possible support reinforcement"),
        (UNKNOWN_INTENT, "Role unknown — geometry required"),
    ],
    ("UNKNOWN", "BOTTOM"): [
        (BOTTOM_MAIN,    "Default bottom longitudinal reinforcement"),
        (BOTTOM_EXTRA,   "Possible support zone reinforcement"),
        (UNKNOWN_INTENT, "Role unknown — geometry required"),
    ],
    ("UNKNOWN", "UNKNOWN"): [
        (UNKNOWN_INTENT, "Role and placement unknown — geometry required"),
    ],
    ("UNKNOWN", "SIDE"): [
        (SIDE_FACE_REINF, "Possible side face reinforcement"),
        (UNKNOWN_INTENT,  "Role unknown — geometry required"),
    ],
    ("UNKNOWN", "BOTH_FACE"): [
        (SIDE_FACE_REINF, "Bilateral placement indicates side face"),
        (UNKNOWN_INTENT,  "Role unknown — geometry required"),
    ],
}

# ── Reordering rule descriptors ────────────────────────────────────────────────
# Each dict describes one deterministic reordering rule.
# Applied in sequence — later rules override earlier promotions.
#
# Fields:
#   "rule_id"     : human-readable identifier
#   "description" : what the rule does
#   "trigger"     : callable(evidence_dict) → bool
#   "promote"     : the intent to move to priority 1
#   "reason"      : new reason string for the promoted hypothesis

REORDER_RULES = [

    {
        "rule_id":     "RR-1",
        "description": "R.1 classified TOP_EXTRA → promote TOP_EXTRA to priority 1",
        "trigger":     lambda ev: ev.get("r1_original_role") == "TOP_EXTRA",
        "promote":     TOP_EXTRA,
        "reason":      "Promoted from R.1 engineering signal: TOP_EXTRA classification",
    },

    {
        "rule_id":     "RR-2",
        "description": "R.1 classified BOTTOM_EXTRA → promote BOTTOM_EXTRA to priority 1",
        "trigger":     lambda ev: ev.get("r1_original_role") == "BOTTOM_EXTRA",
        "promote":     BOTTOM_EXTRA,
        "reason":      "Promoted from R.1 engineering signal: BOTTOM_EXTRA classification",
    },

    {
        "rule_id":     "RR-3",
        "description": "R.1 classified TOP_MAIN → promote TOP_MAIN to priority 1 (default held)",
        "trigger":     lambda ev: ev.get("r1_original_role") == "TOP_MAIN",
        "promote":     TOP_MAIN,
        "reason":      "Promoted from R.1 engineering signal: TOP_MAIN classification",
    },

    {
        "rule_id":     "RR-4",
        "description": "R.1 classified BOTTOM_MAIN → promote BOTTOM_MAIN to priority 1",
        "trigger":     lambda ev: ev.get("r1_original_role") == "BOTTOM_MAIN",
        "promote":     BOTTOM_MAIN,
        "reason":      "Promoted from R.1 engineering signal: BOTTOM_MAIN classification",
    },

    {
        "rule_id":     "RR-5",
        "description": "U_BAR modifier → promote SIDE_FACE_REINFORCEMENT if present",
        "trigger":     lambda ev: "U_BAR" in (ev.get("modifiers") or []),
        "promote":     SIDE_FACE_REINF,
        "reason":      "Promoted: U_BAR modifier indicates side face or bilateral reinforcement",
    },

    {
        "rule_id":     "RR-6",
        "description": "Diameter >=20mm → promote MAIN candidate (TOP_MAIN or BOTTOM_MAIN)",
        "trigger":     lambda ev: float(ev.get("diameter") or 0.0) >= 20.0,
        "promote":     None,  # context-dependent: see HypothesisRanker._apply_large_diameter
        "reason":      "Promoted: Large diameter (>=20mm) favours main bar interpretation",
        "is_diameter_rule": True,
    },

    {
        "rule_id":     "RR-7",
        "description": "CONTINUOUS semantic flag → promote CONTINUOUS candidate",
        "trigger":     lambda ev: "CONTINUOUS" in (ev.get("semantic_flags") or []),
        "promote":     None,  # context-dependent: CONTINUOUS_TOP or CONTINUOUS_BOTTOM
        "reason":      "Promoted: CONTINUOUS semantic flag observed",
        "is_continuous_rule": True,
    },

    {
        "rule_id":     "RR-8",
        "description": "SUPPORT semantic flag → promote SUPPORT candidate",
        "trigger":     lambda ev: "SUPPORT" in (ev.get("semantic_flags") or []),
        "promote":     None,  # context-dependent: SUPPORT_TOP or SUPPORT_BOTTOM
        "reason":      "Promoted: SUPPORT semantic flag observed",
        "is_support_rule": True,
    },
]
