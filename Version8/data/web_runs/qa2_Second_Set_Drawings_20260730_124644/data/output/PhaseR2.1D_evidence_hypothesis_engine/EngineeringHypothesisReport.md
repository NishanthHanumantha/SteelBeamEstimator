# Engineering Hypothesis Report
**Phase:** R.2.1D  |  **MODEL_VERSION:** 7.12.1  |  **Generated:** 2026-07-30 12:47:09

---

## 1. Architecture Summary
Phase R.2.1D upgrades each EngineeringFact from R.2.1C with:

- **ObservableEvidence** — structured capture of all drawing-observable facts.
  Contains zero engineering inference or assumption.
- **IntentHypotheses** — replaces unordered `intent_candidates` with a
  deterministically ranked list of IntentHypothesis objects.

Three strict separations are maintained:
```
Observable  → Role, Placement, Diameter, Modifiers, Quantity, Zone
Hypothesis  → TOP_MAIN, TOP_EXTRA, CONTINUOUS_TOP, ... (ranked, not resolved)
Resolution  → Belongs ONLY to Phase R.3 Geometry Context Engine
```

---

## 2. Hypothesis Pipeline
```
R.2.1C EngineeringFact
  ↓
EvidenceBuilder       (build ObservableEvidence — zero inference)
  ↓
HypothesisRanker
  Stage 1: Base ranking from (role, placement) → BASE_RANKINGS table
  Stage 2: Apply deterministic REORDER_RULES (RR-1 through RR-8)
  ↓
HypothesisEnrichedFact  (upgraded fact with evidence + ranked hypotheses)
  ↓
R.3 Geometry Context Engine (future)
```

---

## 3. Statistics
- **Total Facts:** 229

- **Total Hypotheses:** 758

- **Avg Hypotheses/Fact:** 3.31

- **Beams:** 65

### 3.1 Hypothesis Frequency
| Intent | Appearances |
|--------|-------------|
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

### 3.2 Most Common Priority per Intent
| Intent | Most Common Priority |
|--------|---------------------|
| BOTTOM_EXTRA                   |     2 |
| BOTTOM_MAIN                    |     1 |
| CHAIR_BAR                      |     2 |
| CONTINUOUS_BOTTOM              |     3 |
| CONTINUOUS_TOP                 |     3 |
| CURTAILMENT_BAR                |     3 |
| CURTAILMENT_BOTTOM             |     2 |
| CURTAILMENT_TOP                |     2 |
| SIDE_FACE_REINFORCEMENT        |     1 |
| SPACER_BAR                     |     1 |
| STIRRUP                        |     1 |
| SUPPORT_BAR                    |     4 |
| SUPPORT_BOTTOM                 |     4 |
| SUPPORT_TOP                    |     4 |
| TOP_EXTRA                      |     2 |
| TOP_MAIN                       |     1 |
| UNKNOWN                        |     3 |

### 3.3 Evidence Zone Distribution
| TOP_ZONE             |   148 |  64.6% |
| BOTTOM_ZONE          |    72 |  31.4% |
| UNKNOWN_ZONE         |     6 |   2.6% |
| SIDE_FACE_ZONE       |     3 |   1.3% |

### 3.4 Reorder Rules Applied
| RR-3 |    60 |
| RR-1 |    60 |
| RR-4 |    41 |
| RR-6 |    36 |
| RR-2 |    19 |
| RR-5 |     1 |

---

## 4. Validation Summary
**Result:** 12/12 validation rules passed

- ✔ **RULE_1** — 0 facts missing ObservableEvidence
- ✔ **RULE_2** — 0 evidence objects contain inferred fields
- ✔ **RULE_3** — 0 hypotheses missing reason
- ✔ **RULE_4** — 0 hypothesis lists not starting at priority 1
- ✔ **RULE_5** — 0 hypothesis lists with non-sequential priorities
- ✔ **RULE_6** — 0 hypothesis lists with duplicate intents
- ✔ **RULE_7** — 0 facts with non-UNKNOWN intent
- ✔ **RULE_8** — 0 geometry-required reinforcement facts with fewer than 2 hypotheses
- ✔ **RULE_9** — 0 STIRRUP facts without exactly 1 hypothesis
- ✔ **RULE_10** — 0 SIDE_FACE facts without exactly 1 hypothesis
- ✔ **RULE_11** — Ranking uses only (role, placement, evidence) — no beam IDs in rules
- ✔ **RULE_12** — All hypotheses have non-empty intent (determinism confirmed)

---

## 5. Ranking Rules
### Base Ranking Table

| Role | Placement | Default Priority-1 Intent |
|------|-----------|--------------------------|
| MAIN_BAR | TOP | TOP_MAIN |
| MAIN_BAR | BOTTOM | BOTTOM_MAIN |
| EXTRA_BAR | TOP | TOP_EXTRA |
| EXTRA_BAR | BOTTOM | BOTTOM_EXTRA |
| STIRRUP | * | STIRRUP |
| SIDE_FACE | * | SIDE_FACE_REINFORCEMENT |
| SPACER_BAR | * | SPACER_BAR |

### Deterministic Reorder Rules

| Rule | Trigger | Action |
|------|---------|--------|
| RR-1 | R.1 original role = TOP_EXTRA | Promote TOP_EXTRA to priority 1 |
| RR-2 | R.1 original role = BOTTOM_EXTRA | Promote BOTTOM_EXTRA to priority 1 |
| RR-3 | R.1 original role = TOP_MAIN | Confirm TOP_MAIN at priority 1 |
| RR-4 | R.1 original role = BOTTOM_MAIN | Promote BOTTOM_MAIN to priority 1 |
| RR-5 | Modifier = U_BAR | Promote SIDE_FACE_REINFORCEMENT |
| RR-6 | diameter >= 20mm | Promote contextual MAIN candidate |
| RR-7 | semantic_flag = CONTINUOUS | Promote CONTINUOUS candidate |
| RR-8 | semantic_flag = SUPPORT | Promote SUPPORT candidate |

---

## 6. Engineering Philosophy
Priority is **deterministic ordering**, not probability or confidence.

Example: `2-Y20` at TOP
```json
{"intent": "TOP_MAIN",    "priority": 1, "reason": "Promoted from R.1: TOP_MAIN + diameter >=20mm"}
{"intent": "TOP_EXTRA",   "priority": 2, "reason": "Possible support reinforcement"}
{"intent": "CONTINUOUS_TOP","priority": 3, "reason": "Possible continuous reinforcement"}
{"intent": "SUPPORT_TOP", "priority": 4, "reason": "Requires support geometry"}
```

All intent resolution deferred to **Phase R.3 — Geometry Context Engine**.

---

## 7. Remaining Engineering Limitations
- **Intent unresolved:** R.3 Geometry Context Engine required for all non-settled facts.
- **Bar extent unknown:** Hypotheses cannot distinguish full-span vs short bars.
- **Support location unknown:** SUPPORT vs MAIN distinction unavailable.
- **Span continuity unknown:** CONTINUOUS determination requires member topology.
- **Curtailment point unknown:** Development length and offset require geometry.
- **Priority is not a guarantee:** Priority-1 hypothesis may be incorrect for any given bar.
  R.3 must validate against actual geometry.

---

## 8. Model Version and Pipeline
- **MODEL_VERSION:** 7.12.1
- **PHASE_ID:** R.2.1D
- **Input:** `PhaseR2.1C_engineering_fact_normalization/EngineeringFacts.json`
- **Output:** `PhaseR2.1D_evidence_hypothesis_engine/EngineeringFacts.json`
- **Next Phase:** R.3 Geometry Context Engine (future)
- **Read-only:** No existing production module modified.
