# PHASE V11.1.4 — AI Missing Beam Reconciliation

**STATUS: PASS (diagnostic / read-only)**

**Run:** `Version11/data/web_runs/20260915_105617_0178faaa_RECOVERY`  
**Source forensic run (untouched):** `20260915_105617_0178faaa`  
**AI Excel:** `data/output/Production_Output/Estimation_Output.xlsx`  
**Estimator (read-only):** `Test_Input/5th Set Drawings-Inizio_9F/Estimator_Output_5thSet/EstimatorOutput_9TH FLOOR.xlsx`

No accuracy, quantity, or steel-weight comparison is included.

---

## 1. Executive Summary

The recovery pipeline processed **exactly 143 beams** from V.ROOT.1 through VB.1. The AI Bar Bending Schedule contains **the same 143 IDs**. **Zero catalogued beams were dropped** by Hybrid, deterministic fallback, VB.1, or V11.1 spatial ordering.

B5–B13 (except B9) are **genuinely absent from the AI BBS** because they were **never admitted to the 143-beam catalog**. They are present as reinforcement-detail titles `B5(350X1100)` … `B13(350X1100)` (B9 has no such title) **inside DXF INSERT blocks**. V.ROOT.1 `DynamicBeamDiscovery` reads modelspace `TEXT`/`MTEXT` only and does not explode `INSERT` virtual entities. P2.6.10 `collect_beam_titles` does explode INSERTs, which is why W.8 can see marks that V.ROOT.1 never registered.

This is **TYPE 1 (absent from AI BBS)**, not a Claude miss, not an alternate-ID mapping, and not a V11.1 ordering loss.

**Three failure types (do not combine):**

| Type | Meaning | Count in this run |
|---|---|---|
| TYPE 1 | Beam absent from AI final BBS | **46** reinforcement-detail title IDs (includes B5–B8, B10–B13) |
| TYPE 2 | Same physical beam under an alternate AI ID | **0 confirmed** (no centroid/geometry match) |
| TYPE 3 | In AI BBS, but Claude skipped (`EVIDENCE_TIMEOUT`) | **13 / 13 present in AI BBS** |

---

## 2. B5–B13 Verification

Artifacts:

- Framing DXF TEXT layer `Beam Nos` (Test_Input framing plan)
- Reinforcement titles via production parser `collect_beam_titles` (INSERT-aware) on the recovery reinforcement DXF
- Estimator `Sheet1` Description column
- AI `Bar Bending Schedule` and `Beam Summary`
- V.ROOT.1 `beam_registry.json` / `initialization_report.json`
- R.1 `beam_details.json` (source: V.ROOT.1 registry)
- W.6 `hybrid_coverage.json`
- VB.1 `bbs_beam_order_trace.json`

| Beam | A Framing | B Reinf. title `B#(WXD)` | C Estimator | D AI BBS | E AI Beam Summary | F Other AI sheets | G Geometry registry / VROOT | H R.1 / R1.3 | I W.6 | J VB.1 / BBS trace |
|---|---|---|---|---|---|---|---|---|---|---|
| B5 | YES (`B5` on `Beam Nos`) | YES (`B5(350X1100)`, 2 INSERT copies, y≈-21125072) | YES | NO | NO | NO | NO | NO | NO | NO |
| B6 | YES | YES (`B6(350X1100)`, INSERT) | YES | NO | NO | NO | NO | NO | NO | NO |
| B7 | YES | YES (`B7(350X1100)`, INSERT) | YES (also `B7 & B8`) | NO | NO | NO | NO | NO | NO | NO |
| B8 | YES | YES (`B8(350X1100)`, INSERT) | YES (`B7 & B8` at estimator row 23) | NO | NO | NO | NO | NO | NO | NO |
| B9 | YES | **NO** (0 reinforcement titles) | YES (row 33 `B9`) | NO | NO | NO | NO | NO | NO | NO |
| B10 | YES | YES (`B10(350X1100)`, INSERT) | YES | NO | NO | NO | NO | NO | NO | NO |
| B11 | YES | YES (`B11(350X1100)`, INSERT) | YES | NO | NO | NO | NO | NO | NO | NO |
| B12 | YES | YES (`B12(350X1100)`, INSERT) | YES | NO | NO | NO | NO | NO | NO | NO |
| B13 | YES | YES (`B13(350X1100)`, INSERT) | YES | NO | NO | NO | NO | NO | NO | NO |

Native modelspace `TEXT`/`MTEXT` parsed as `B#(WXD)`: **0** for B5–B13.  
INSERT virtual `TEXT` parsed as `B#(WXD)`: **2 copies each** for B5–B8 and B10–B13; **0** for B9.

---

## 3. Complete 143-Beam Reconciliation

Authoritative catalog: `PhaseL.2.2_geometry_recovery/geometry_registry.json` → `beam_ids` (143). Identical membership in V.ROOT.1, R.1, W.6 coverage, VB.1 order trace, AI BBS unique IDs, and AI Beam Summary unique IDs.

**All 143 catalog beams: Drawing YES (reinforcement native TEXT title) · Estimator YES · AI BBS YES · AI Beam Summary YES · Alternate ID NONE · Final Status MATCHED.**

Catalog IDs:

`B1, B2, B3, B4, B4A, B14, B15, B16, B17, B18, B41–B50, B53–B66, B68–B90, B91–B103, B119–B123, B126–B130, B133, B135–B148, B150–B154, B156, B157, B159, B161–B164, B166, B168–B170, B172–B182, B185–B189, B191–B197, B70A, B83A, B96A–B101A, B162A`

AI BBS first IDs after V11.1 spatial order: `B14, B15, B16, B17, B18, B41, …` (visually top of the **detected** detail sheet). That is presentation order, not membership change.

`catalog − ordered = ∅`, `ordered − AI BBS = ∅`, `AI BBS − catalog = ∅`.

R2A JSON did not store `beam_id` keys in a form the scanner counted (`stage_counts R2A = 0`). R2.1B/C/D still have 143 IDs, so this is a schema/scan artifact, not disappearance.

---

## 4. Genuine Missing Beam List (TYPE 1)

Relative to the **143-beam catalog**, AI BBS missing count is **0**.

Relative to **reinforcement-detail titles** (`collect_beam_titles` = 189 unique `B#(WXD)` marks), **46 IDs are absent from AI BBS**:

1. B5  
2. B6  
3. B7  
4. B8  
5. B10  
6. B11  
7. B12  
8. B13  
9. B19  
10. B20  
11. B21  
12. B22  
13. B23  
14. B24  
15. B25  
16. B26  
17. B27  
18. B28  
19. B29  
20. B30  
21. B31  
22. B32  
23. B33  
24. B34  
25. B35  
26. B36  
27. B37  
28. B38  
29. B39  
30. B52  
31. B52A  
32. B104  
33. B105  
34. B106  
35. B107  
36. B108  
37. B109  
38. B110  
39. B111  
40. B112  
41. B113  
42. B114  
43. B115  
44. B116  
45. B117  
46. B118  

**B9 is not in this 46.** It has no reinforcement `B9(WXD)` title. It is framing-plan + estimator only.

**Beyond B5–B11:** B12, B13, plus the 38 IDs from B19 onward in the list above (38 = 46 − 8).

Of those 46:

- **44** exist **only** as INSERT virtual titles (not native TEXT).
- **B52** and **B52A** also parse as native TEXT titles but are still absent from the 143 V.ROOT.1 registry (`label_entities = 143`). That pair needs a separate V.ROOT.1 filter/cluster check; it is not the INSERT-only mechanism.

---

## 5. Alternate ID Findings (TYPE 2)

No confirmed alternate-ID cases.

Checks used:

- R.1 centroids for catalogued neighbours (B1–B4A at y≈-21252150; B14–B18 at y≈-21131044)
- INSERT title positions for B5–B13 at y≈-21125072 (distinct row **above** B14–B18)
- No mapping table in R.1 / R1.3 renaming B5→another ID
- Naming similarity alone was not used

B5 is not B14/B48/etc. Different title text and different detail-sheet coordinates.

---

## 6. 13 Evidence-Timeout Beams (TYPE 3)

`B2, B3, B4, B147, B148, B189, B191, B192, B193, B194, B195, B196, B197`

| Check | Result |
|---|---|
| In AI BBS | **13 / 13 YES** |
| In AI Beam Summary | **13 / 13 YES** |
| In VB.1 order trace | **13 / 13 YES** |
| Claude invoked | NO (`skip_reason=EVIDENCE_TIMEOUT`) |

Classification: `VISION_EVIDENCE_TIMEOUT_BUT_AI_OUTPUT_PRESENT`.  
These are **not** missing-BBS beams. They used deterministic R13/VB.1 output.

---

## 7. First-Disappearance Stage Analysis

For every TYPE 1 beam in the 46-ID list:

| Stage | Present? | Evidence |
|---|---|---|
| Reinforcement DXF INSERT titles | YES (except B9, not in the 46) | `collect_beam_titles` |
| Framing DXF | YES for B5–B13 | layer `Beam Nos` |
| **V.ROOT.1 beam_registry** | **NO — first absence** | `beam_count=143`, `label_entities=143` |
| R.1 | NO | `source: V.ROOT.1 beam_registry`; 143 IDs; no B5–B13 |
| T1 / R2.1B–D / L2.2 / R3 / R1.2A / R1.3 | NO | 143 IDs, none of the 46 |
| W.6 / Hybrid | NO | never eligible |
| VB.1 / Excel | NO | cannot emit IDs that were never catalogued |

**Last confirmed:** reinforcement-detail INSERT title (and framing label).  
**First missing:** **V.ROOT.1 dynamic beam discovery**.

V11.1 spatial ordering did not remove IDs (`ordered_beam_ids` length 143 = catalog).

---

## 8. Spatial / Pattern Analysis

Observed pattern (not claimed as a second root cause):

- B5, B6, B7, B8, B10, B11, B12, B13 sit on one reinforcement-detail row at **y ≈ -21125072**, x increasing left→right. That is **visually above** the first catalogued row B14–B18 (y ≈ -21131044) when `y_increases_visually_up` is true.
- The same INSERT-only set continues as **B19–B39** and **B104–B118** — additional detail-sheet blocks whose titles live in INSERT blocks.
- Duplicate copies exist (~28400 mm x-offset) for those INSERT titles (2 hits each).
- Catalogued B1–B4A occupy the **bottom** detected row (y ≈ -21252150). Numeric ID gap B4 → B14 matches the missing INSERT row B5–B13, not a VB.1 sort bug.
- B9 is **not** on that INSERT row.

---

## 9. Root-Cause Classification

| Group | Category | Confidence | Evidence |
|---|---|---|---|
| B5–B8, B10–B13, B19–B39, B104–B118 (44 IDs) | **B. Drawing detection failure** at V.ROOT.1 (`TEXT`/`MTEXT` only; no `INSERT` explode) | HIGH | INSERT-only `B#(WXD)` titles; VROOT `label_entities=143`; P2610 parser finds 189 unique titles |
| B52, B52A | **B. Drawing detection failure** (native TEXT present, still not in 143 registry) | MEDIUM | Native TEXT titles exist; absent from `beam_registry.json`; mechanism inside VROOT clustering/filter not fully isolated |
| B9 | **A. Not present in reinforcement-detail title catalog** (framing + estimator only) | HIGH | 0 `B9(WXD)` titles; framing `B9`; estimator row 33 |
| TYPE 3 timeout 13 | **F. Evidence-generation failure** (timeout), output still present | HIGH | V11.1.3; all 13 in BBS |
| V11.1 spatial order | **Not a membership failure** | HIGH | 143 in = 143 out |
| Alternate ID | None classified | HIGH | No geometry match |

Not supported: Hybrid/Vision as the reason B5 is missing from BBS; VB.1 generation loss; presentation-only hiding of a catalogued ID.

---

## 10. Summary Counts (coverage only)

| Metric | Count |
|---|---|
| Total authoritative pipeline beams | **143** |
| AI BBS unique beam IDs | **143** |
| Matched (catalog ∩ AI BBS) | **143** |
| Missing from AI BBS vs catalog | **0** |
| Alternate/mapped IDs confirmed | **0** |
| Reinforcement-detail titles unique | **189** |
| TYPE 1: drawing-title IDs missing from AI BBS | **46** |
| Estimator `Sheet1` unique B# tokens (first-token parse) | **187** |
| Estimator-only vs catalog (first-token parse) | **44** (B8 under-counted as `B7 & B8`) |
| Drawing-only (title present, not in estimator token set) | includes **B29, B104–B116, B8-as-combined-row** |
| Framing unique B# TEXT labels | **200** |
| 13 evidence-timeout beams | **13** |
| Of the 13: present in AI BBS | **13** |
| Of the 13: absent from AI BBS | **0** |

No steel / bar / diameter / overall accuracy figures.

---

## 11. Recommended Investigation Targets

Diagnosis only — no fixes in this phase.

1. **V.ROOT.1 `dynamic_beam_discovery._extract_labels`** — add INSERT virtual-entity title discovery (already implemented in `PhaseP2610A_beam_region_crop_audit.title_localizer.iter_text_inserts`), then rebuild the beam registry. This is the stage that first loses B5–B8 / B10–B13 and the other 44 INSERT-only IDs.
2. **V.ROOT.1 handling of native TEXT B52 / B52A** — why 145 native parsed titles become 143 registered beams.
3. **B9** — framing/estimator identity with no reinforcement detail title; do not treat as the same INSERT-row defect.
4. **Estimator combined marks** (`B7 & B8`) — identity coverage, not quantity.
5. Do **not** investigate V11.1 ordering, W.6 Claude, or VB.1 as the cause of B5–B13 BBS absence.

---

## 12. Integrity Check

| Item | Status |
|---|---|
| Version10 modified | NO |
| Lightsail modified | NO |
| V11 source modified | NO |
| Original forensic run modified | NO |
| Recovery run modified | NO |
| AI Excel modified | NO |
| Estimator workbook modified | NO |
| Claude called | NO |
| W.6 rerun | NO |
| Vision evidence regenerated | NO |
| Pipeline rerun | NO |
| New file | this report only |

---

## Answers to the required questions

1. **Are B5–B11 genuinely absent from the AI BBS?**  
   YES for B5, B6, B7, B8, B10, B11. B9 is also absent, but it is not a reinforcement `B9(WXD)` title.

2. **Are any of B5–B11 present under another AI beam ID?**  
   NO confirmed alternate ID. Geometry does not match B14–B18 or other catalogued marks.

3. **How many additional beams beyond B5–B11 are genuinely missing (drawing titles vs AI)?**  
   B12, B13, plus 38 further title IDs in the TYPE 1 list (46 − 8 INSERT-row IDs that overlap B5–B11 excluding B9).

4. **Complete list of genuinely missing AI BBS beams vs drawing titles:**  
   the 46 IDs in section 4.

5. **Disappearance stage:** V.ROOT.1 beam discovery. Present on DXF INSERT titles; absent from `beam_registry.json` onward.

6. **Spatially clustered?** YES — B5–B8 and B10–B13 share y≈-21125072 (top INSERT row). Broader INSERT-only set includes B19–B39 and B104–B118.

7. **One reinforcement section?** YES — INSERT-hosted detail titles on the beam-details DXF, not a VB.1 sheet split.

8. **Related to the 13 EVIDENCE_TIMEOUT beams?** NO. Those 13 are in the AI BBS.

9. **Systematic detection/matching problem?** YES at **detection** (V.ROOT.1 misses INSERT titles). Not a Hybrid matching miss for these IDs.

10. **Did V11.1 spatial ordering cause beam loss?** NO. Membership 143→143. Ordering only starts the BBS at B14 (top detected row), which made the B5–B13 gap more visible.
