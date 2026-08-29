# PHASE W.18A — SPACER BAR FORENSIC INVESTIGATION & RULE MAPPING

Date: 2026-08-29  
HEAD at investigation start: `3b159bff` (W.17 audit)  
Production: FROZEN at W.14  
Mode: READ-ONLY. No calculation modules were modified.

---

## 1. Executive Summary

Spacer bars in Version10 are **not read from the drawing**. They are **generated** by Phase M.2 `SpacerRuleEngine` (`PhaseV9_spacer_rule`) during R.1.3 export, then copied 1:1 through VB.1 and BBS.

Repeated spacer rows on a beam are created **inside M.2 zone emission**, before L.2 JSON is written. VB.1 / BBS / Excel do not clone spacer records.

**B1 (qty 3, 7, 3) is a mixture, not three independent physical layers:**

| L.2 spacer qty | Matches | Physical meaning |
| ---: | --- | --- |
| 3 | `ceil(0.25 × 4158.3 / 1000) + 1 = 3` | TOP_EXTRA_LEFT overlap with top main |
| 7 | `ceil(5918.3 / 1000) + 1 = 7` | extent_fallback using the **hooked cut** of a third 2-Y16 `CONTINUOUS_BAR` piece |
| 3 | same as first 3 | TOP_EXTRA_RIGHT overlap with top main |

The 2-Y16 extra is represented as **three pieces** (`CONTINUOUS_BAR` + `TOP_EXTRA_LEFT` + `TOP_EXTRA_RIGHT`). M.2 then emits geometric support-end zones **and** a fallback zone whose length is `cut_length_mm` (span + 2Ld + 2×hook×d), not overlap length.

**B10 / B23** emit **one** spacer row because left/right extras share the same hooked cut and M.2 `seen_cl` collapses them. Quantity is `ceil(cut_mm/1000)+1`, which **overstates** overlap (cut includes 2Ld + hooks).

W.17-OBS-03 (negative Dvlp.L) is confirmed and **not fixed**.

Classification: **W18A_FORENSIC_COMPLETE_MULTIPLE_CAUSES_IDENTIFIED**

---

## 2. Scope / Read-only status

Dataset: 2nd Set — Galera GF (W.16 L.2 replay file).  
Primary beams: **B1, B10, B23**.  
Additional Galera scan: all 65 L.2 models.

Production mutation: **NO**  
Calculation `.py` modules changed: **NO**  
L.2 / VB.1 / SI.1 / BBS / SpacerRuleEngine: **NOT MODIFIED**

---

## 3. Authoritative spacer rules (investigation oracle)

Hardcoded (not General Notes):

- Diameter = 25 mm  
- Spacing = 1000 mm  
- Required where **at least two reinforcement groups come together** on a face:
  - Top + top extra  
  - Two top groups together  
  - Bottom + bottom extra  
  - Two bottom groups together  
- **Not** required for a single top group or a single bottom group  
- Quantity = `(overlapping_bar_length / 1000) + 1`  
- Cut = `beam_width − 2 × cover`

Historical estimator Excel omissions must **not** override this rule.

**Implementation vs oracle (current code):**

| Rule | Authoritative | Current M.2 |
| --- | --- | --- |
| Dia / spacing | 25 / 1000 hardcoded | Same (`SPACER_DIA_MM`, `SPACER_SPACING_MM`) |
| Trigger | ≥2 groups on a face | Requires **MAIN and EXTRA** (`if not extras: return []`). Two MAINs alone → **no spacers** |
| Quantity | `(L / 1000) + 1` (rounding unspecified) | `ceil(zone_length_mm / 1000) + 1` |
| Overlap length | overlapping bar length | Geometric piece extents **or** extra `cut_length_mm` fallback |
| Cut | width − 2 cover | Same; Galera cover 30 mm |

---

## 4. Current code path

```
DXF / R.1 discovery
    -> GeometryProvider (width, clear_span)
    -> R.1.2C/D intents/details
    -> PieceGenerator (may split BOTH_SUPPORTS extras into LEFT + RIGHT
         and may also emit a CONTINUOUS_BAR for the same label)
    -> EngineeringBarBuilder._bars_from_pieces
    -> R.1.2B consolidation (duplicate physical bars; does not emit spacers)
    -> PipelineIntegrationManager._apply_spacer_rule
         r13_injector.inject_spacers
         spacer_engine.compute_spacers_for_beam
    -> EngineeringBarBuilder.to_l2_compatible   # DROPS piece_start/end and M.2 metadata
    -> W.6 Hybrid handoff (may MOVE longitudinal bars between L.2 buckets)
    -> SteelWeightCompletion._compute_bar (SPACER: use provided cut)
    -> BBSCompletionEngine.generate (1 BBS row per spacer bar_weight)
    -> EstimatorExcelGenerator
```

| Stage | File / symbol | Creates spacer? | Copies? | Merges? | Dedupes? |
| --- | --- | --- | --- | --- | --- |
| Geometry | `geometry_provider.py` | No | width, span | No | No |
| Pieces | `piece_generator.py` `_expand_both_supports`, `_single_piece` | No (unless a DXF bar was already classified SPACER_BAR) | start/end on LEFT/RIGHT/MAIN | Can **split** one extra into L+R | No |
| L.2 lists | `engineering_bar_builder.py` `to_l2_compatible` | No | qty, cut, piece_type | No | No |
| M.2 | `spacer_engine.py` `_zones_for_face` | **YES** | n/a | Overlap sweep can merge stacked extents | Unique extents; unique extra clear_lengths; skip if `already_has_spacer` |
| Inject | `r13_injector.py` `inject_spacers` | Appends `SPACER_BAR` rows | From engine rows | No | Skip beam if M.2 spacer already present |
| VB.1 | `steel_weight_completion.py` | No | L.2 `quantity`; cut from `cut_length_mm` | No | No |
| BBS | `bbs_completion_engine.py` | No | one row per `BarSteelWeight` | No | No |
| Excel | `estimator_excel_generator.py` | No | BBS rows | No | No |

Cover used for spacer **cut** is R.2A beam cover (Galera TABLE 2 = 30 mm). Dia/spacing are **not** from GN.

---

## 5. Current spacer data model

### 5.1 Engine input (`LongitudinalGroup`)

- `role`, `face`, `start_mm`, `end_mm`, `clear_length_mm`, `extent_confidence`, `diameter_mm`, `quantity`
- Injector fills groups from `EngineeringBarModel.bar_role` (not L.2 bucket)
- `piece_start_mm` / `piece_end_mm` from `engineering_metadata` when present
- MAIN without extents: **synthesized** `[0, clear_span_mm]` (confidence LOW)
- EXTRA without extents: `clear_length_mm = cut_length_mm` (the **fabrication cut**, including 2Ld + hooks)

### 5.2 Engine output (`SpacerRow` → metadata)

`source=SpacerRuleEngine`, `rule_version=M.2`, `face`, `zone_start_mm`, `zone_end_mm`, `zone_length_mm`, `extent_fallback`, `cut_length_mm`

### 5.3 What L.2 actually stores

`to_l2_compatible` copies `cut_length_mm`, `piece_type`, `extent`, `spacing_mm`, `quantity`. It does **not** copy:

- `engineering_metadata` (empty `{}` on Galera bars)
- `piece_start_mm` / `piece_end_mm`
- M.2 `zone_start_mm` / `zone_end_mm` / `extent_fallback`

Spacer L.2 rows still show `bar_label = "SPACER 25@1000"`, `piece_type = SPACER_BAR`, `extent = ZONE`, `classification_evidence = "R.1.3 EngineeringBarModel: SPACER 25@1000"` — sufficient to prove M.2 origin, not sufficient to recover overlap intervals.

Parent / trigger bar IDs: **NOT AVAILABLE**.

---

## 6. L.2 spacer record analysis (B1 / B10 / B23)

All three beams: diameter 25, spacing 1000, `l2_key=spacer_bars`, `source_phase` on L.2 row = null (export gap), `source_pipeline_role=R.1.3+PIECE`.

| Beam | Spacer ID | Qty | Cut mm | Width | Cover | Cut check | Trigger | Overlap start/end | Duplicate group |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| B1 | R13-B1-SPACER_BAR-eb6aef | 3 | 140 | 200 | 30 | 200−60=140 CORRECT | TOP_EXTRA_LEFT vs TOP_MAIN (inferred) | NOT AVAILABLE in L.2; inferred 0 → 1039.6 | support-end pair with third row |
| B1 | R13-B1-SPACER_BAR-6eda9b | 7 | 140 | 200 | 30 | CORRECT | CONTINUOUS 2-Y16 cut 5918.3 fallback | NOT AVAILABLE; fallback length = cut | **DUPLICATE/OVERSIZED** vs same extra |
| B1 | R13-B1-SPACER_BAR-31ecd5 | 3 | 140 | 200 | 30 | CORRECT | TOP_EXTRA_RIGHT vs TOP_MAIN | inferred 3118.7 → 4158.3 | support-end pair with first row |
| B10 | R13-B10-SPACER_BAR-* | 4 | 540 | 600 | 30 | 600−60=540 CORRECT | 5-Y16 L+R collapsed | NOT AVAILABLE | one row, not duplicated |
| B23 | R13-B23-SPACER_BAR-* | 5 | 540 | 600 | 30 | CORRECT | 5Y16#L + #R collapsed | NOT AVAILABLE | one row, not duplicated |

---

## 7. B1 detailed investigation

### 7.1 Longitudinal pieces (pre-hybrid role = `bar_id` token)

| Piece | Label | bar_id role | L.2 bucket after hybrid | piece_type | Cut mm | Implied base |
| --- | --- | --- | --- | --- | ---: | --- |
| PCE::B1::0001 | 2-Y20 | TOP_MAIN | top_extra_bars | TOP_MAIN | 6358.3 | span 4158.3 + 2×1000 Ld + 200 hook |
| PCE::B1::0002 | 2-Y16 | TOP_EXTRA | top_main_bars | CONTINUOUS_BAR | 5918.3 | span + 2×800 + 160 |
| PCE::B1::0004 | 2-Y16 | TOP_EXTRA | top_main_bars | TOP_EXTRA_LEFT | 2799.6 | 0.25×span + 2×800 + 160 |
| PCE::B1::0005 | 2-Y16 | TOP_EXTRA | top_main_bars | TOP_EXTRA_RIGHT | 2799.6 | 0.25×span + 2×800 + 160 |

BBS “Top bars” vs “Extra” follow **post-hybrid buckets**. M.2 used **pre-hybrid** `bar_role` = bar_id token: one MAIN (Y20) + three EXTRAS (all 2-Y16).

### 7.2 Why three spacer records?

M.2 path `len(with_extent) ≥ 2` (MAIN synthesized or pieced `[0, span]` + LEFT/RIGHT extras with 0.25L extents) emits two geometric zones.

Extras **without** extent also get a fallback zone per distinct `clear_length`. The CONTINUOUS 2-Y16 contributes `clear = cut_length_mm = 5918.3` → qty 7.

Fingerprint (cannot be a coincidence):

- `ceil(1039.575/1000)+1 = 3`  
- `ceil(5918.3/1000)+1 = 7`  
- `ceil(1039.575/1000)+1 = 3`

`ceil(2799.6/1000)+1 = 4` — **not** the L.2 qty 3. So qty 3 is **not** from the hooked left/right cut; it is from **piece length 0.25L**.

### 7.3 Are they physically distinct?

- Rows qty 3 and 3: **yes**, left vs right support extras — two overlap regions if the drawing has extras only at supports.  
- Row qty 7: **no** as a third physical layer. It is the same 2-Y16 extra represented as `CONTINUOUS_BAR`, with zone length = fabrication cut (Ld + hooks included).

### 7.4 Is qty 7 valid?

**No** against the authoritative overlap rule.

Inputs: `zone_length = 5918.3` (cut), not 4158.3 (span) and not a true overlap.  
Formula used: `ceil(5918.3/1000)+1 = 7`.  
If the extra is full-span with the Y20 main, one zone of span would be `ceil(4158.3/1000)+1 = 6`, and left/right geometric zones should **merge** into that one zone (`compute_overlap_zones` when both full-span extents are counted as two layers). Unique-extent collapse of identical `[0, span]` intervals currently **prevents** that merge if MAIN and extra share the same numeric interval.

### 7.5 Is qty 3 valid?

Against implementation: **yes** (`ceil(0.25L/1000)+1 = 3`).  
Against oracle `(1.040)+1 = 2.04`: **rounding disagreement** (ceil vs unspecified). Flag for estimator: 2 vs 3.

### 7.6 Role inversion (W17-OBS-06)

Hybrid moved Y16 extras into `top_main_bars` and Y20 main into `top_extra_bars`. **M.2 had already run.** Role inversion did **not** create the three spacer rows. It does invert BBS headings.

### 7.7 B1 conclusion

**MIXTURE.** Two support-end spacer groups are explainable. The qty-7 row is a **duplicate/oversized fallback** driven by a third 2-Y16 piece plus use of hooked cut as overlap. First duplication: **M.2 `_zones_for_face`**, fed by **PieceGenerator** emitting CONTINUOUS + L + R for one extra callout.

L.2 cannot distinguish these cases without `piece_start_mm`/`piece_end_mm` (export gap). `piece_type` still can.

---

## 8. B10 investigation

Longitudinal:

- `5Y20` TOP_MAIN, full-span cut 4856.6  
- `5-Y16` TOP_EXTRA_LEFT, cut 2424.2 = 0.25×2656.6 + 1760  
- `5-Y16` TOP_EXTRA_RIGHT, cut 2424.2  

Hybrid: both Y16 extras sit in `top_main_bars` (`semantic_role=TOP_MAIN`). Replay from **buckets** emits **zero** spacers. Replay from **bar_id** roles without extents emits **qty 4**, matching L.2.

So production M.2 used pre-hybrid EXTRA roles and **cut_length fallback** (no usable distinct extents at inject, or extents unused), and `seen_cl` merged the two 2424.2 mm clears into **one** zone.

| Question | Answer |
| --- | --- |
| Why qty 4? | `ceil(2424.2/1000)+1 = 4` |
| Who is “together”? | TOP_MAIN 5Y20 + TOP_EXTRA 5-Y16 (both L and R as one extra length) |
| Two 5-Y16 as separate groups? | Labels/piece_types say L and R. Quantity logic treats them as **one** extra clear length |
| Does 5Y20 trigger? | Yes (MAIN). Without MAIN+EXTRA pairing, engine emits nothing |
| Overlap length assumed | Hooked extra **cut** 2424.2 mm, not 664 mm (0.25L) and not 2656.6 mm span |
| 1 m rule | Implementation ceil formula on that cut — **OVERSIZED** vs overlap |
| Duplication of rows | **No** (single L.2 spacer). Under-count of **zones** (should be two support-end groups if extras are only at supports) |

Engineering expected if L and R extras are real: two zones, `ceil(664.15/1000)+1 = 2` each.  
Current: one zone qty 4. Classification: **OVERSIZED** quantity, **UNDER-COUNTED** zone count.

---

## 9. B23 investigation

- `5-Y20` TOP_MAIN, cut 10000.4 = span 7800.4 + 2Ld + hooks  
- `5Y16#L` / `5Y16#R` TOP_EXTRA_LEFT / RIGHT, cut 3710.1 = 0.25×7800.351 + 1760  
- **No** bar_id vs bucket mismatch on this beam  

M.2 replay from bar_id without extents: **qty 5**, matches L.2.  
Replay with inferred 0.25L extents: **qty 3 + 3**.

`#L` / `#R` are preserved on labels and `piece_type`. They are **not** used as two overlap zones in the production spacer row. `seen_cl` collapses identical 3710.1 mm cuts.

| Authoritative (two support extras) | Current |
| --- | --- |
| Two zones, length 1950 mm, qty `ceil(1.95)+1 = 3` each | One zone, length 3710.1 mm, qty 5 |

Classification: **OVERSIZED** single quantity; **UNDER-COUNTED** zones. Left/right distinction exists in L.2 labels but spacer logic did not consume it (extents missing at inject **or** fallback path won).

---

## 10. Role / bucket consistency

W.6 `handoff.py` may change `semantic_role` and **move** bars between `LONGITUDINAL_BUCKETS`. It **skips** `spacer_bars` and `stirrups`. `bar_id` is not rewritten, so `R13-…-TOP_EXTRA-…` can sit under `top_main_bars`.

| Consumer | Field used |
| --- | --- |
| M.2 inject | `EngineeringBarModel.bar_role` (equals bar_id token at `to_l2` time) |
| VB.1 / BBS | L.2 **list key** via `_L2_ROLE_MAP` |

**ROLE-MAPPING ISSUE** (W17-OBS-06): BBS captions can invert extra vs main.  
**SPACER-GENERATION ISSUE**: separate. Hybrid does not duplicate spacers. Re-running M.2 on **post-hybrid buckets** would miss B10 extras (replay `engine_qtys []`).

B14, B7, B8, B9, B32, … show `top_extra` in buckets but **zero** spacer rows — consistent with pairing that exists only after hybrid, or extras without MAIN at inject, or missing extra clear_length. Not traced drawing-by-drawing in W.18A; listed for W.18B tests.

---

## 11. Overlap geometry availability

| Field | On piece / EngineeringBarModel | In Galera L.2 |
| --- | --- | --- |
| clear_span_mm | geometry | YES |
| cut_length_mm | YES (includes 2Ld+hooks for longitudinal) | YES — **not overlap** |
| piece_start_mm / piece_end_mm | YES on pieces | **NOT AVAILABLE** (dropped) |
| piece_type LEFT/RIGHT/CONTINUOUS | YES | YES |
| zone LEFT_SUPPORT / RIGHT_SUPPORT | YES | `position_zone` YES |
| #L / #R label | YES | YES on B23; B1 L.2 labels stripped to `2-Y16` (evidence string still has `#L`/`#R`) |
| M.2 zone_start/end | YES on spacer metadata | **NOT AVAILABLE** |

**CAN W.18B implement the authoritative rule using current L.2 data?**

**B — YES, but it requires a deterministic derivation from existing fields, and W.18B must run in R.1.3/M.2 (where `piece_start_mm` still exists), not from exported L.2 alone.**

Missing for L.2-only correction: actual `overlap_start` / `overlap_end`.  
Usable proxies: `piece_type` + span (0.25L / 0.75L convention — **same heuristic PieceGenerator already uses**, not measured DXF stations).  
Must not use `cut_length_mm` as overlap.

If W.18B only patches VB.1, overlap **cannot** be recovered rigorously from L.2 → treat as **C** for that layer.

Recommended: fix M.2 + preserve extents in L.2 export.

---

## 12. Duplication lineage (B1)

```
DXF 2Y16 extra callout (one or two groups — drawing not re-read here)
    -> PieceGenerator: CONTINUOUS_BAR + TOP_EXTRA_LEFT + TOP_EXTRA_RIGHT   [FIRST SPLIT]
    -> EngineeringBarModel × 3 extras + 1 main
    -> M.2: 2 geometric zones + 1 cut-length fallback                    [FIRST SPACER DUPLICATION]
    -> to_l2_compatible: 3 spacer_bars (metadata stripped)
    -> Hybrid: moves longitudinal bars; spacers untouched
    -> VB.1: 3 BarSteelWeight SPACER rows                                 [copy]
    -> BBS / Excel: 3 Spacer bars rows                                    [copy]
```

Not duplicated in BBS or Excel.  
W.17 quantity-from-L.2 statement is correct for **VB.1**; quantity itself was already computed in M.2.

---

## 13. Expected vs actual spacer quantities

Implementation rounding: **`math.ceil`**, then `+ 1`. Integer conversion: `int(...)`.

| Beam | Zone | Oracle `(L/1000)+1` if L = true overlap | Current | Class |
| --- | --- | --- | --- | --- |
| B1 left | 1039.6 mm | 2.04 | 3 | rounding SUSPECTED; path CORRECT if extras are support-only |
| B1 right | 1039.6 mm | 2.04 | 3 | same |
| B1 qty 7 | not a true overlap | — | 7 | **DUPLICATE + OVERSIZED** |
| B10 | 664 mm × 2 zones | 1.66 → 2 per zone | 4 in one row | **OVERSIZED**; zones UNDER-COUNTED |
| B23 | 1950 mm × 2 | 2.95 → 3 per zone | 5 in one row | **OVERSIZED**; zones UNDER-COUNTED |

Galera 65-beam histogram of spacer **row counts**: 0→29, 1→12, 2→14, 3→8, 4→2.  
Three-row pattern (same fingerprint family as B1): **B1, B11, B19, B20, B21, B22, B49, B54**.

Cut length on all audited spacers: **CORRECT** (`width − 2×30`). Do not “fix” cut in W.18B unless cover changes.

---

## 14. Root-cause classification

Causes of repeated / wrong spacers (all **W18A_OBSERVATION_ONLY**):

**CAUSE A — Piece split of one extra into CONTINUOUS + LEFT + RIGHT**  
File: `piece_generator.py` `_expand_both_supports` plus a separate `_single_piece` CONTINUOUS/FULL_SPAN detail.  
Effect: B1 and other 3-row beams.

**CAUSE B — Fallback zone length = extra `cut_length_mm` (span+2Ld+hooks)**  
File: `r13_injector.py` `_bar_to_group` (`clear = meta.cut_length_mm`); `spacer_engine.py` extent_fallback.  
Effect: B1 qty 7; B10 qty 4; B23 qty 5.

**CAUSE C — Unique-extent collapse of identical `[0, span]` MAIN and EXTRA**  
File: `spacer_engine.py` `_zones_for_face` `seen_ext`.  
Effect: two stacked full-span layers counted as one interval; mid-span overlap dropped.

**CAUSE D — LEFT/RIGHT extras collapsed by equal fallback clear lengths**  
File: `seen_cl` in `_zones_for_face`.  
Effect: B10 / B23 one row instead of two support zones.

**CAUSE E — Trigger requires EXTRA role, not “two groups on a face”**  
File: `_zones_for_face` `if not extras: return []`.  
Effect: spec example “two top bars together” (two MAINs) is **not** implemented.

**CAUSE F — L.2 export drops extents and M.2 zone fields**  
File: `engineering_bar_builder.py` `to_l2_compatible`.  
Effect: audit/replay gap; not itself a duplicate emitter.

**Not causes:** BBSCompletionEngine cloning; Excel cloning; GN table; stirrup SI.1; W.17 longitudinal span+2Ld (separate issue).

Primary forensic question: **C + B together, with A feeding B1.** First point where one extra condition becomes multiple spacer **records**: **M.2 `_zones_for_face`**.

---

## 15. W.18B implementation requirements

Do **not** implement in W.18A. W.18B should:

1. Keep dia 25 and spacing 1000 hardcoded.  
2. Compute overlap from **piece extents** (start/end), never from fabrication `cut_length_mm`.  
3. Count **layers**, not unique numeric intervals: MAIN `[0,span]` and EXTRA `[0,span]` are two layers.  
4. One maximal overlap zone per face where ≥2 layers coexist (existing sweep is correct **if** extents are not over-deduped).  
5. LEFT+RIGHT extras → two zones when they do not form one continuous ≥2 region; do **not** add a third fallback from a CONTINUOUS duplicate of the same extra label / `detail_id`.  
6. Deduplicate extra pieces that share `detail_id` / same bar_label family before zoning.  
7. Decide trigger: MAIN+EXTRA only vs any two groups on a face (spec).  
8. Freeze quantity rounding with the estimator (`ceil(L/1000)+1` vs `(L/1000)+1` truncated).  
9. Persist `zone_start_mm`, `zone_end_mm`, `extent_fallback`, `piece_start_mm`, `piece_end_mm` on L.2 spacer and longitudinal rows.  
10. Run M.2 on **pre-hybrid** roles (current) or a stable layer field — not post-hybrid buckets.  
11. Leave VB.1 1:1 copy if M.2 output is already one row per real zone.  
12. **Do not** fix negative Dvlp.L, longitudinal span+2Ld, or stirrup dual-path in W.18B unless explicitly scoped.  
13. Do not change production deploy / W.14 UI / Anthropic / hybrid routing except as required to pass a new spacer field through L.2.

---

## 16. Open engineering questions (estimator)

1. B1: is drawing 2-Y16 a support extra only, a full-span extra, or both?  
2. Quantity rounding for overlap 1.04 m → 2 or 3 spacers?  
3. Do two TOP_MAIN groups with no EXTRA role require spacers?  
4. For #L/#R extras, confirm two spacer lines vs one.  
5. Confirm 0.25L / 0.75L piece heuristic vs measured DXF stations.  
6. Beams with extra in L.2 buckets but zero spacers (B14, B7, B8, B9, B32, …): missed spacer vs hybrid-only extra?

---

## 17. Production mutation status

| Item | Status |
| --- | --- |
| Production files changed | NO |
| Calculation modules changed | NO |
| Production mutation | NO |
| Files created | `PHASE_W18A_SPACER_BAR_FORENSIC_INVESTIGATION.md`, `W18A_SPACER_FORENSIC_TRACE.json`, `_w18a_spacer_forensic.py` |
| Files deleted | none |
| Tests | `pytest Version10/src/PhaseV9_spacer_rule/tests/test_spacer_engine.py` — 15 passed (engine unchanged) |
| Forensic replay | `_w18a_spacer_forensic.py` against `galera_l2.json` (W.16 temp L.2) |

---

## Classification

**W18A_FORENSIC_COMPLETE_MULTIPLE_CAUSES_IDENTIFIED**

ESTIMATOR_REVIEW_READY: **YES** (B1 mixture + rounding + #L/#R zoning)  
W18B_IMPLEMENTATION_READY: **YES**, provided W.18B:

- changes M.2 / injector / L.2 export (not a silent VB.1 patch),  
- does not use `cut_length_mm` as overlap,  
- records estimator decisions on rounding and two-MAIN trigger,  
- adds tests listed in the final response.

W.18B is **not** ready if the only allowed surface is post-export L.2 without restoring extents (then classify as data-model blocked for a VB.1-only fix).
