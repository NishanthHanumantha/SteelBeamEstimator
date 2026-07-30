# Engineering Fact Normalization Report
**Phase:** R.2.1C  |  **MODEL_VERSION:** 7.12.0  |  **Generated:** 2026-07-30 12:47:08

---

## 1. Architecture Summary
Phase R.2.1C removes premature engineering intent from R.2.1B Semantic Objects.
It produces geometry-independent `EngineeringFact` records — the clean contract
between the annotation parsing pipeline and the future R.3 Geometry Context Engine.

Three independent engineering concepts are separated:
- **Role** — observable from annotation text (MAIN_BAR, EXTRA_BAR, STIRRUP, ...)
- **Placement** — observable from position zone (TOP, BOTTOM, SIDE, BOTH_FACE)
- **Intent** — `UNKNOWN` until geometry proves otherwise (TOP_MAIN, BOTTOM_EXTRA, ...)

---

## 2. Normalization Pipeline
```
R.2.1B Engineering Semantic Object
  ↓
RoleNormalizer            (map ESO.engineering_role → canonical role)
  ↓
PlacementNormalizer       (map ESO.placement → canonical placement)
  ↓
IntentNormalizer          (remove premature intent → UNKNOWN + generate candidates)
  ↓
SemanticCandidateBuilder  (refine candidates with modifiers + diameter signals)
  ↓
ConfidenceNormalizer      (confidence scoped to role + placement only)
  ↓
EngineeringFact           (immutable dataclass)
  ↓
R.3 Geometry Context Engine (future)
```

---

## 3. Statistics
- **Total Facts:** 229

- **Beams Processed:** 65

- **Intent UNKNOWN:** 229 (100.0%)

- **Geometry Required:** 223 (97.4%)

- **Role Coverage:** 96.5%

- **Placement Coverage:** 97.4%

### 3.1 Role Distribution
| MAIN_BAR               |   101 |   44.1% |
| EXTRA_BAR              |    79 |   34.5% |
| SPACER_BAR             |    35 |   15.3% |
| UNKNOWN                |     8 |    3.5% |
| STIRRUP                |     3 |    1.3% |
| SIDE_FACE              |     3 |    1.3% |

### 3.2 Placement Distribution
| TOP                    |   148 |   64.6% |
| BOTTOM                 |    72 |   31.4% |
| UNKNOWN                |     6 |    2.6% |
| BOTH_FACE              |     3 |    1.3% |

### 3.3 Candidate Distribution
| TOP_EXTRA                      |   128 |
| SUPPORT_TOP                    |   120 |
| TOP_MAIN                       |    66 |
| BOTTOM_EXTRA                   |    61 |
| CONTINUOUS_TOP                 |    60 |
| CURTAILMENT_TOP                |    60 |
| SUPPORT_BOTTOM                 |    58 |
| BOTTOM_MAIN                    |    42 |
| CONTINUOUS_BOTTOM              |    41 |
| SPACER_BAR                     |    35 |
| CHAIR_BAR                      |    35 |
| SUPPORT_BAR                    |    19 |
| CURTAILMENT_BOTTOM             |    17 |
| UNKNOWN                        |     8 |
| STIRRUP                        |     3 |
| SIDE_FACE_REINFORCEMENT        |     3 |
| CURTAILMENT_BAR                |     2 |

### 3.4 Modifier Distribution
| SIDE_FACE_REINFORCEMENT        |     2 |
| U_BAR                          |     1 |
| BOTH_FACES                     |     1 |
| ONE_EACH_FACE                  |     1 |

---

## 4. Validation Summary
**Result:** 12/12 validation rules passed

- ✔ **RULE_1** — 229/229 semantic objects converted to facts
- ✔ **RULE_2** — 0 quantity mismatches
- ✔ **RULE_3** — 0 diameter mismatches
- ✔ **RULE_4** — 0 spacing mismatches
- ✔ **RULE_5** — 0 facts missing role
- ✔ **RULE_6** — 0 facts missing placement
- ✔ **RULE_7** — 0 facts with non-UNKNOWN intent
- ✔ **RULE_8** — 0 facts missing intent candidates
- ✔ **RULE_9** — Normalization logic uses no hardcoded beam IDs (verified by code review)
- ✔ **RULE_10** — Phase R.2.1C is additive: no steel/BBS/Excel equations modified
- ✔ **RULE_11** — 0 modifier mismatches
- ✔ **RULE_12** — Production workbook exists: C:\Users\nishanth.h\SteelBeamEstimator\Version8\data\output\Production_Output\Engineering_Review.xlsx

---

## 5. Intent Normalization Strategy
Engineering intent is UNKNOWN for all non-settled annotations.
Two roles are considered settled (no geometry needed):
- **STIRRUP** — transverse bar, unaffected by span geometry
- **SIDE_FACE** — explicitly annotated with S.F.R. modifier

All longitudinal bars require geometry to resolve intent:
- A 2-Y16 at TOP could be TOP_MAIN, TOP_EXTRA, CONTINUOUS_TOP, or SUPPORT_TOP.
- Only bar extent (start offset, end offset) and support location can distinguish.
- Reference drawings B1 and B2 demonstrate this clearly:
  - B1: Both 2-Y16 'Top Bar Extra' and 'Top Bar' appear at TOP
  - B2: 2-Y20 'Bottom Bar Extra' at supports vs 2-Y12 'Bottom Bar' mid-span

---

## 6. Candidate Generation Strategy
Candidates are generated from a deterministic table indexed by (role, placement).
Derived from reference drawing engineering rules (B1, B2, B8-B10):

| Role       | Placement | Candidates                                               |
|------------|-----------|----------------------------------------------------------|
| MAIN_BAR   | TOP       | TOP_MAIN, TOP_EXTRA, CONTINUOUS_TOP, SUPPORT_TOP         |
| MAIN_BAR   | BOTTOM    | BOTTOM_MAIN, BOTTOM_EXTRA, CONTINUOUS_BOTTOM, SUPPORT_BOTTOM |
| EXTRA_BAR  | TOP       | TOP_EXTRA, CURTAILMENT_TOP, SUPPORT_TOP                  |
| EXTRA_BAR  | BOTTOM    | BOTTOM_EXTRA, CURTAILMENT_BOTTOM, SUPPORT_BOTTOM          |
| STIRRUP    | *         | STIRRUP                                                  |
| SIDE_FACE  | *         | SIDE_FACE_REINFORCEMENT                                  |
| SPACER_BAR | *         | SPACER_BAR, CHAIR_BAR                                    |

Candidates are further refined by semantic signals: modifier type, original R.1 role,
and diameter magnitude (large-diameter bars promoted to MAIN candidates).

---

## 7. Remaining Engineering Limitations
- **Intent unresolved:** R.3 Geometry Context Engine is required to resolve all non-settled intents.
- **Bar extent unknown:** Start/end offsets of bars are not available from annotations alone.
- **Support location unknown:** Which end is near column or wall cannot be inferred from text.
- **Span continuity unknown:** Multi-span continuous bars cannot be detected without geometry.
- **Curtailment point unknown:** Development length and curtailment offset require drawing geometry.
- **Quantity multiplier deferred:** `ONE_EACH_FACE` modifiers do not multiply quantity here.
  The final quantity per face is deferred to the geometry-aware production stage.

---

## 8. Model Version and Pipeline
- **MODEL_VERSION:** 7.12.0
- **PHASE_ID:** R.2.1C
- **Input:** `PhaseR2.1B_engineering_semantic_interpreter/engineering_semantic_objects.json`
- **Output:** `PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json`
- **Next Phase:** R.3 Geometry Context Engine (future)
- **Read-only:** No existing production module modified.
