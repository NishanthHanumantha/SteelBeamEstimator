# PHASE W.18B — SPACER RULE CORRECTION & EXTENT PRESERVATION

Date: 2026-08-29  
HEAD at implementation start: `3b159bff` (W.17 audit / W.18A forensic)  
Production: FROZEN at W.14  
Mode: Implementation + local/regression validation only.

Classification: **W18B_IMPLEMENTATION_COMPLETE_PASS**

Production mutation: **NO**

---

## 1. Root cause from W.18A

W.18A classified Galera spacer failures as multiple cooperating causes:

| Cause | Failure |
| --- | --- |
| A | PieceGenerator emits `CONTINUOUS_BAR` + `TOP_EXTRA_LEFT` + `TOP_EXTRA_RIGHT` for the same extra (B1 2-Y16). M.2 treated them as three independent extra layers. |
| B | Extra without unique geometric overlap used **fabrication `cut_length_mm`** (span + 2Ld + hooks) as overlap. B1 qty 7 from 5918.3 mm; B10 qty 4 from 2424.2 mm; B23 qty 5 from 3710.1 mm. |
| C | Unique-extent collapse of MAIN `[0, span]` and EXTRA `[0, span]` (stacked layers counted as one interval → overlap count &lt; 2). |
| D | LEFT/RIGHT extras collapsed when fallback clear lengths matched. |
| F | `to_l2_compatible` dropped `piece_start_mm` / `piece_end_mm` and M.2 zone metadata, so a post-export-only L.2 patch could not recover extents. |

W.18B therefore corrects **M.2 / injector / L.2 export / BBS aggregation**, not Excel.

Physical overlap length is **not** fabrication cut length.

---

## 2. Files changed

| File | Change |
| --- | --- |
| `Version10/src/PhaseV9_spacer_rule/spacer_engine.py` | Geometric overlap only; drop CONTINUOUS when LEFT/RIGHT exist; round-half-up qty; no unique-extent collapse across roles; zone aggregation helper |
| `Version10/src/PhaseV9_spacer_rule/spacer_models.py` | `piece_type` / labels / ids on groups; `raw_quantity`; `component_zones`; `clear_span_mm` |
| `Version10/src/PhaseV9_spacer_rule/r13_injector.py` | Never set extra clear from `cut_length_mm`; pass piece identity; aggregate equivalent rows before emit |
| `Version10/src/PhaseR1.3_pipeline_integration/engineering_bar_builder.py` | `to_l2_compatible` preserves piece extents and M.2 zone metadata |
| `Version10/src/PhaseVB.1_production_output_completion/bbs_completion_engine.py` | Merge equivalent spacer BBS rows (same dia + cut) |
| `Version10/src/PhaseV9_spacer_rule/__init__.py` | MODEL_VERSION 9.2.0 |
| `Version10/src/PhaseV9_spacer_rule/tests/test_spacer_engine.py` | Qty 2150 → round-half-up 3; no cut-length fallback |
| `Version10/src/PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py` | Tests A–J |
| `Version10/webapp/deployment/_w18b_spacer_replay.py` | Local B1/B10/B23 replay |
| `Version10/webapp/deployment/W18B_SPACER_VALIDATION_TRACE.json` | Replay trace |
| `Version10/webapp/deployment/PHASE_W18B_SPACER_RULE_CORRECTION.md` | This artifact |

Unchanged on purpose: PieceGenerator, hybrid, stirrup, Ld/Dvlp.L, production runner, production workbooks.

---

## 3. Exact algorithm change

### 3.1 Overlap length

Overlap = intersection of **piece geometric extents** (`piece_start_mm`, `piece_end_mm`).

`cut_length_mm` is **never** used as `zone_length_mm`. If an EXTRA has no geometric extent, the zone is unresolved and **no spacer row** is emitted for that extra (warning recorded). MAIN without extents may still be synthesized as `[0, clear_span_mm]` (existing injector behavior).

### 3.2 CONTINUOUS + LEFT + RIGHT

Same extra family = same face + role + diameter + normalized label (`#L`/`#R` stripped).

If that family has LEFT and/or RIGHT **and** a CONTINUOUS piece, **drop CONTINUOUS**. LEFT and RIGHT remain distinct physical zones.

### 3.3 Sweep-line

Keep every layer extent. MAIN `[0, span]` and EXTRA `[0, span]` both contribute +1 so stacked layers still form one full-span overlap (not zero). Zones with identical **intervals** on the same face are still merged; zones with identical **lengths** but different positions (LEFT vs RIGHT) are not.

### 3.4 Quantity

```
raw_quantity = (overlap_length_mm / 1000.0) + 1
quantity     = round_half_up(raw_quantity)   # floor(x + 0.5); not banker's rounding
```

Spacing remains **1000 mm**. Diameter remains **25 mm**.

### 3.5 Spacer cut (unchanged)

```
spacer_cut_length = beam_width - (2 * cover)
```

Galera cover = 30 mm. B1: 200 − 60 = 140 mm. B10/B23: 600 − 60 = 540 mm.

### 3.6 Aggregation

M.2 keeps LEFT/RIGHT as separate zone records (`component_zones`).

Injector aggregates equivalent rows (same beam, face, dia, spacing, cut) into **one** `SPACER_BAR` EngineeringBar.

BBS also merges equivalent spacer `BarSteelWeight` rows (same dia + cut) as a second safety net.

---

## 4. Quantity rounding rule

| Overlap | raw = L/1000 + 1 | round-half-up |
| ---: | ---: | ---: |
| 1040 mm | 2.04 | **2** |
| 1500 mm | 2.50 | **3** (Python `round(2.5)` is 2; estimator uses 3) |
| 2490 mm | 3.49 | **3** |
| 2500 mm | 3.50 | **4** |
| 2150 mm | 3.15 | **3** (was ceil-based 4) |

---

## 5. B1 behavior

Drawing: 2-Y16 = full-span top extra **plus** LEFT support **plus** RIGHT support. Those are piece representations of **one** extra, not three layers.

Replay (Galera identities, PieceGenerator extents, live M.2 → L.2 → VB.1 → BBS):

| Piece | type | start | end | fabrication cut (not overlap) |
| --- | --- | ---: | ---: | ---: |
| PCE::B1::… 2-Y20 | TOP_MAIN | 0 | 4158.3 | 6358.3 |
| PCE::B1::… 2-Y16 | CONTINUOUS_BAR | 0 | 4158.3 | 5918.3 — **dropped** |
| PCE::B1::… 2-Y16#L | TOP_EXTRA_LEFT | 0 | 1039.575 | 2799.6 |
| PCE::B1::… 2-Y16#R | TOP_EXTRA_RIGHT | 3118.725 | 4158.3 | 2799.6 |

| Zone | overlap | raw | qty |
| --- | ---: | ---: | ---: |
| LEFT | 1039.575 mm | 2.039575 | 2 |
| RIGHT | 1039.575 mm | 2.039575 | 2 |

- Spacer cut: **140 mm**
- L.2: **one** spacer_bars row, quantity **4**, `zones` retains both intervals
- BBS key: `B1|SPACER|25|0.14` quantity **4**
- W.18A was **3 + 7 + 3**. Corrected: **not reproduced**.

---

## 6. B10 behavior

| Piece | type | start | end | fabrication cut (not overlap) |
| --- | --- | ---: | ---: | ---: |
| 5Y20 | TOP_MAIN | 0 | 2656.6 | 4856.6 |
| 5-Y16 LEFT | TOP_EXTRA_LEFT | 0 | 664.15 | 2424.2 |
| 5-Y16 RIGHT | TOP_EXTRA_RIGHT | 1992.45 | 2656.6 | 2424.2 |

| Zone | overlap | raw | qty |
| --- | ---: | ---: | ---: |
| LEFT | 664.15 mm | 1.66415 | 2 |
| RIGHT | 664.15 mm | 1.66415 | 2 |

- Spacer cut: **540 mm** (not 2424.2)
- BBS: one line, qty **4**
- Previous qty 4 from hooked cut was **numerically coincidental**, not physically correct. Length source is now piece extent.

---

## 7. B23 behavior

| Piece | type | start | end | fabrication cut (not overlap) |
| --- | --- | ---: | ---: | ---: |
| 5-Y20 | TOP_MAIN | 0 | 7800.351 | 10000.4 |
| 5Y16#L | TOP_EXTRA_LEFT | 0 | 1950.088 | 3710.1 |
| 5Y16#R | TOP_EXTRA_RIGHT | 5850.263 | 7800.351 | 3710.1 |

| Zone | overlap | raw | qty |
| --- | ---: | ---: | ---: |
| LEFT | 1950.088 mm | 2.950088 | 3 |
| RIGHT | 1950.088 mm | 2.950088 | 3 |

- Spacer cut: **540 mm** (not 3710.1)
- BBS: one line, qty **6**
- W.18A was one row qty **5** from hooked cut. Corrected quantity is **6**.

---

## 8. L.2 extent preservation

`EngineeringBarBuilder.to_l2_compatible` now copies:

- `piece_start_mm`, `piece_end_mm`, `detail_id`
- `zone_start_mm`, `zone_end_mm`, `zone_length_mm`, `extent_fallback`, `raw_quantity`, `zones`
- slim `engineering_metadata` of the same keys

Replay confirmed longitudinal `piece_start_mm` present and spacer `zones` retained.

---

## 9. Regression results

Existing: `pytest Version10/src/PhaseV9_spacer_rule/tests/test_spacer_engine.py`

W.18B: `pytest Version10/src/PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py`

Combined: **29 passed**.

Replay: `python Version10/webapp/deployment/_w18b_spacer_replay.py`  
Output: `W18B_SPACER_VALIDATION_TRACE.json`

A full Galera DXF production run was **not** executed (production freeze). Replay uses W.18A Galera bar identities + PieceGenerator 0.25L/0.75L extents + live injector / L.2 / VB.1 / BBS.

---

## 10. Production mutation status

**NO**

- No deploy
- No production calculation data mutation
- No production runner / workbook change
- No commit unless later instructed
