# Track 1 (9.3.0 → 9.3.1) Closure Report

Date: 2026-08-01
Scope: CLOSE-1 (R4), CLOSE-2 (R6), CLOSE-3 (WRONG_QTY attribution), CLOSE-4 (R3 propagation fix)

All numbers below were re-verified **after** the CLOSE-4 code patch landed (fresh 3-set benchmark
re-runs), not just before it — see CLOSE-1/CLOSE-2 "re-verify" rows.

---

## CLOSE-1 — R4: Scope-Leakage Proof — VERDICT: **CLEAN**

Beam-level diff of `beam_reinforcement_models_production.json` (9.2.0 baseline vs 9.3.0/9.3.1) for
every beam **not** in `residual_target_beams.json`, comparing every role's rows (STIRRUP + all
others), ignoring only the non-deterministic `bar_id` hex suffix.

| Set  | Out-of-scope beams checked | Zero-diff | Any diff | Run pair compared |
|------|------|------|------|------|
| Set1 | 5  | 5  | 0 | baseline `103357` vs 9.3.0 `124700` |
| Set2 | 15 | 15 | 0 | baseline `103505` vs 9.3.0 `124747` |
| Set3 | 15 | 15 | 0 | baseline `103630` vs 9.3.0 `124856` |
| **Total** | **35** | **35** | **0** | |

**Re-verified after the CLOSE-4 code patch** (new flag-on runs `152514`/`152612`/`152811`):

| Set  | Checked | Clean | Diff |
|------|------|------|------|
| Set1 | 5  | 5  | 0 |
| Set2 | 15 | 15 | 0 |
| Set3 | 15 | 15 | 0 |

**Verdict: R4 CONFIRMED CLEAN, both before and after CLOSE-4.** Zero out-of-scope beams show any
diff in any role's rows. No leakage from T1.2/T1.3/T1.4 into beams outside the residual target
list. No root-cause investigation needed (there is nothing to root-cause).

---

## CLOSE-2 — R6: Flag-Off Equivalence — VERDICT: **CLEAN**

`beam_reinforcement_models_production.json` with `enable_geometry_stirrup_evidence: false`,
compared against the 9.2.0 baseline (flag didn't exist), for **all** beams (144 total).

| Set  | Beams checked | Identical | Diffs | Flag-off run |
|------|------|------|------|------|
| Set1 | 18 | 18 | 0 | `144703` |
| Set2 | 65 | 65 | 0 | `144805` |
| Set3 | 61 | 61 | 0 | `144952` |
| **Total** | **144** | **144** | **0** | |

**Re-verified after the CLOSE-4 code patch** (new flag-off run `153444`/`153515`/`153556`):

| Set  | Checked | Clean | Diffs |
|------|------|------|------|
| Set1 | 18 | 18 | 0 |
| Set2 | 65 | 65 | 0 |
| Set3 | 61 | 61 | 0 |

**Verdict: R6 CONFIRMED CLEAN, both before and after CLOSE-4.** With the flag off, output is
byte/row-identical to the pre-Track-1 baseline for every beam in all 3 sets. The rollback
guarantee holds; the flag fully gates T1.2/T1.3/T1.4, and the new `_t1_fusion_case` /
`geometry_fusion_case` lookups added in CLOSE-4 are themselves flag-gated (they return `None`
immediately if T1 is disabled — see `_t1_enabled(root)` check).

---

## CLOSE-3 — WRONG_QTY Regression Attribution (100 → 113)

All 113 `STIRRUP` rows with `WRONG_QUANTITY` status in the 9.3.0 flag-on run were matched, row by
row (by GT quantity + diameter), back to their 9.2.0-baseline residual-target row to determine
whether each was already wrong before Track 1, newly broken by Track 1, or out-of-scope.

| Category | Count | Set1 | Set2 | Set3 | Meaning |
|---|---|---|---|---|---|
| **A** — in-scope, expected tradeoff | 81 | 11 | 32 | 38 | Was WRONG_QTY at baseline; T1.4 zone-split changed the numbers but still doesn't match GT |
| **B** — in-scope, newly broken | 30 | 3 | 9 | 18 | Was MISSING (qty=0) at baseline; T1 now produces a nonzero qty that still isn't GT-matching |
| **C** — out-of-scope leakage | 2 | 2 | 0 | 0 | Beam not in residual_target_beams.json at all |
| **D** — Set3 zone-grain/matcher noise | 0 | — | — | — | Investigated, not a distinct artifact (see below) |
| **Total** | **113** | 16 | 41 | 56 | |

**Category A direction** (did the new qty move closer to or further from GT vs. the pre-Track-1
qty error, for the same bar): **14 closer, 12 further, 54 unchanged, 1 unknown.** Net: roughly a
wash — a few beams improved, a similar number regressed, the large majority kept the same
(non-matching) quantity through the zone-split change. Example: Set1 `B2` (dia 8): baseline
qty=67 vs GT=29 (error 38); 9.3.0 qty=45 vs GT=29 (error 16) — **closer**. Set1 `B7` (dia 10):
baseline qty=27 vs GT=13 (error 14); 9.3.0 qty=18 vs GT=13 (error 5) — **closer**. Not all Category
A beams improve, but the category as a whole is "still wrong, differently wrong" — an expected
consequence of T1.4 re-splitting zones on beams that were already broken, not a new failure mode.

**Category B mechanism**: these 30 rows were `MISSING` (qty=0, 100% wrong) at baseline. T1's
geometry-derived tick/pitch-change detection now produces a nonzero quantity for a stirrup zone
that previously had zero bars detected at all. The new qty still doesn't match GT exactly (hence
`WRONG_QUANTITY` rather than `MATCH`), but going from "detected nothing" to "detected something,
imperfectly" is **partial progress**, not a regression — QA.2A's binary MATCH/MISSING/WRONG_QTY
taxonomy has no bucket for "improved but still not exact," so all of this partial-detection
progress lands in the WRONG_QTY count and inflates it, even though the underlying situation
improved. Example: Set1 `B12` (dia 8): baseline MISSING (qty=0) vs GT=11; 9.3.0 qty=4 vs GT=11 —
still wrong, but no longer zero.

**Category C reconciliation with CLOSE-1**: Set1 `B3` and `B18` are pre-existing `WRONG_QTY` beams
from 9.2.0 that were **deliberately excluded** from the Track 1 residual target list (they were
already flagged `WRONG_QTY` before Track 1 and stayed exactly that way — CLOSE-1's beam-diff
proof already confirmed **zero** row-level changes to these two beams between 9.2.0 and 9.3.0).
**No contradiction with CLOSE-1**: these are not "leakage" in the sense of Track 1 code touching
them — they are simply beams that were already wrong and are *counted* in the 9.3.0 WRONG_QTY
total because they were wrong in both runs. This is a counting/labeling nuance, not a code-path
issue.

**Category D investigation**: the original 9.3.0 report's claim of "Set3 zone-grain/EXTRA noise"
was checked beam-by-beam. Set3 beams with multiple `WRONG_QTY` rows (e.g., separate "Stirrups
(Mid.)" and "Stirrups (Sup.)" rows counted individually) were cross-checked against
`residual_target_beams.json` and found to correspond to **genuinely distinct baseline residual
entries** (a main-span stirrup group and a support-zone stirrup group are two separate GT bar
groups with their own qty/diameter, not one GT zone artificially split by the matcher). This is
**not** a QA.2A matcher artifact analogous to the M.2 Y25 cross-role issue — it is real multi-group
beam structure. These rows are correctly classified as Category A/B on their own row-level merits;
there is no separate "Category D" population to carve out.

**Dominant category: A (81/113 = 72%), expected tradeoff.** The second largest, B (30/113 = 27%),
is net-positive (partial detection replacing zero detection). Category C is 2/113 and is a
labeling artifact of already-broken beams, not new leakage (confirmed by CLOSE-1's zero-diff
proof). **No Category B or C regression requires a follow-up fix phase** — the 113 number is
explained: it is dominated by beams that were already wrong before Track 1 and remain wrong (just
differently), plus real progress on previously-undetected beams that QA.2A's taxonomy can't credit
as "improved."

---

## CLOSE-4 — R3: SYNTHESIZED_GEOMETRY Propagation Fix

### Trace: where the flag was dropped

R.2.1D (`phase_r21d_orchestrator.py` → T1.3 fusion, `r21d_fusion.py`) correctly computes and
writes the fusion outcome (`AGREE` / `CONFLICT` / `GEOMETRY_ONLY_SYNTH` / `TEXT_ONLY`) per beam to
`PhaseR2.1D_evidence_hypothesis_engine/t1_geometry_fusion_summary.json`. **This is the only place
the flag/case existed prior to this fix.**

The gap: the actual production bar-building pipeline (`PhaseR1.3_pipeline_integration
/engineering_bar_builder.py`, which builds `beam_reinforcement_models_production.json`) **does not
read `t1_geometry_fusion_summary.json` at all** — R2.1D's fusion output and the R1.3 production
pipeline are two parallel tracks that never join. So the flag was dropped **immediately after
R.2.1D**, before R.3/R.3.1/R.1.2A/R.1.3 ever ran — there was no partial propagation to lose along
the way; it simply never left R.2.1D's own output file. A `SYNTH:` bar-label-prefix check already
existed in `engineering_bar_builder.py` as dead code (no bar was ever labelled that way by the
production path), so it silently always evaluated false.

### Patch (3 files, within the 2–3 file budget)

1. **`src/PhaseT1_geometric_stirrup_evidence/type3_label_repair.py`** — added
   `geometry_fusion_case(beam_id)`: a read-only lookup that loads
   `t1_geometry_fusion_summary.json` (already written, flag-gated, cached) and returns the fusion
   outcome for a beam. No recomputation of any kind.
2. **`src/PhaseR1.3_pipeline_integration/engineering_bar_builder.py`** (`to_l2_compatible`) — for
   each STIRRUP bar already produced by the existing pipeline, if the beam's fusion outcome is
   `AGREE`/`CONFLICT`, tags `classification_evidence` with a
   `GEOMETRY_TEXT_AGREE|GEOMETRY_STIRRUP|...` / `GEOMETRY_TEXT_CONFLICT|GEOMETRY_STIRRUP|...`
   prefix (`CONFLICT` also sets `classification_confidence="WARN"`). For beams where the fusion
   outcome is `GEOMETRY_ONLY_SYNTH` and the production model has **no** STIRRUP bar at all (no
   text-based detection ever found one), a beam-level advisory note is appended to
   `engineering_notes` instead of fabricating a row/quantity. No `quantity`/`diameter_mm`/
   `cut_length_mm` value is read or altered anywhere in this patch.
3. **`src/PhaseSI.1_stirrup_improvement/phase_si1_orchestrator.py`** (`compute_beam`) — looks up
   the same fusion outcome and appends `[GEOMETRY_TEXT_AGREE]` / `[GEOMETRY_TEXT_CONFLICT]` (or
   `[SYNTHESIZED_GEOMETRY]` for `SYNTH:`-labelled bars, dead-path but kept for completeness) to the
   BBS row's `description` field — this is the field that reaches `Estimation_Output.xlsx`.
   Applied uniformly across all `compute_beam` row-generation exits (parsed, legacy, Type3-repeat).

### Before/after: QA.2A metrics (proves no value changed)

| Metric | Before patch | After patch |
|---|---|---|
| Overall accuracy | 70.23% | 70.23% |
| Beam detection | 93.92% | 93.92% |
| Bar detection | 68.52% | 68.52% |
| Bar accuracy | 27.41% | 27.41% |
| Steel accuracy | 91.07% | 91.07% |

Identical to 4 significant figures — confirms the patch is purely additive metadata, no
qty/dia/cut-length value changed.

### Before/after: visibility tags populated

| Tag | Set1 | Set2 | Set3 | Total |
|---|---|---|---|---|
| `classification_evidence` = `GEOMETRY_TEXT_AGREE\|...` (JSON, real bar) | 0 | 1 (`B3`) | 5 (`B5,B26,B37,B47,B53`) | 6 |
| `classification_evidence` = `GEOMETRY_TEXT_CONFLICT\|...` (JSON, real bar) | 0 | 0 | 1 (`B7`) | 1 |
| Beam-level `SYNTHESIZED_GEOMETRY` advisory note (JSON, no bar exists) | 0 | 1 (`B35A`) | 1 (`B25A`) | 2 |
| Excel `[GEOMETRY_TEXT_AGREE]` / `[GEOMETRY_TEXT_CONFLICT]` marker in BBS description | matches JSON rows above | | | 7 rows visible |

Verified directly in `Estimation_Output.xlsx` (Set3): BBS rows for `B5`/`B26`/`B37`/`B47`/`B53`
now read `Stirrups (Mid./Sup.) [GEOMETRY_TEXT_AGREE]`, and `B7` reads
`Stirrups (Sup./Mid.) [GEOMETRY_TEXT_CONFLICT]` — all with dia/spacing/qty/cut-length/weight
columns unchanged from before the patch.

### QA.2A `SYNTHESIZED_GEOMETRY` column (`is_synthesized_geometry` in `bar_matching.json`)

| Set | Before | After |
|---|---|---|
| Set1 | 0 | 0 |
| Set2 | 0 | 0 |
| Set3 | 0 | 0 |

**Still 0, and this is expected, not a residual bug.** `bar_matcher.py`'s `is_synthesized_geometry`
check keys off a bar carrying the `SYNTH:` label prefix, which is only ever produced for
`GEOMETRY_ONLY_SYNTH` cases (a stirrup pattern inferred from geometry with **zero** text-callout
confirmation). Per the explicit "do NOT change value" and "no new detection logic" constraints,
this fix deliberately does **not** materialize a new bar/quantity for those 2 beams (`B35A`,
`B25A`) — doing so would mean *inventing* a quantity from geometry alone, which is exactly the
Track 2 (Vision-LLM arbiter) job called out in the original spec, not this propagation fix. Those
2 beams instead get a JSON-level advisory note (satisfying requirement 2(a) for JSON) but have no
Excel-visible marker (requirement 2(b) is not met for these 2 specific beams, since there is no
row to tag). For every case where a **real, already-existing bar** was involved (`AGREE`/
`CONFLICT`, 7 rows across 3 sets), both JSON and Excel visibility now work end-to-end.

**Qualified verdict on acceptance criterion 4**: the propagation fix lands, is narrow (3 files),
and full JSON+Excel visibility is confirmed for AGREE/CONFLICT evidence. The QA.2A
`SYNTHESIZED_GEOMETRY` column specifically remains 0 because the only rows that would set it
require materializing a new bar from pure geometry — which is out of this fix's permitted scope
(no value changes, no new detection logic) and is explicitly Track 2's responsibility. This is
flagged as a known, narrow, documented carve-out (2 beams total across all 3 sets) rather than a
failure to propagate.

---

## MODEL_VERSION

**Bumped 9.3.0 → 9.3.1.** CLOSE-4 required a code change (3 files), so per the closure spec's own
rule ("bump to 9.3.1 ONLY if the R3 propagation fix requires a code change"), the version bumps.
Only the canonical reporting constant (`PhaseQA.2A_ground_truth_benchmark/phase_qa2a_orchestrator.py
:: MODEL_VERSION`) was updated — the `MODEL_VERSION` constants duplicated inside T1.2/T1.3/T1.4
detection modules, R2.1D, R1.2D, and M.1 were deliberately left untouched to respect the "no
changes beyond the CLOSE-4 propagation fix" constraint; those modules' own logic did not change.

## Final go/no-go recommendation

**GO — Track 1 (9.3.0/9.3.1) is safe to treat as CLOSED.**

1. R4 (scope-leakage): **CLEAN**, re-verified after the code patch. Zero out-of-scope beams
   touched, in either the pre- or post-CLOSE-4 code state.
2. R6 (flag-off equivalence): **CLEAN**, re-verified after the code patch. Flag off = byte-identical
   to 9.2.0 baseline for all 144 beams across 3 sets, in both code states.
3. WRONG_QTY 113: **dominant driver is Category A (72%), an expected tradeoff of already-broken
   beams having their zone split changed** — not a new regression. Category B (27%) is net
   progress mislabelled by a binary taxonomy. Category C (2%) is a pre-existing, unchanged
   (CLOSE-1-verified) labeling artifact, not leakage. No follow-up fix phase is required to accept
   this number.
4. R3 propagation: **fixed for all cases involving a real bar** (visible in both JSON and Excel,
   7 rows/beams across 3 sets); the 2 pure-geometry-only beams get JSON-level advisory visibility
   only, by design, since materializing their quantity is explicitly Track 2 scope. This is a
   narrow, documented, low-volume carve-out and does not block closure.

No open blocking items remain. Track 2 (Vision-LLM arbiter) work may begin.
