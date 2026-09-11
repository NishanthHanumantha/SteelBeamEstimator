# Version11 Development Rules

These rules are permanent for the Version11 generation. They are not optional local conventions.

---

## RULE 1 — Version10 is the immutable baseline

Do not modify Version10 production source, prompts, hybrid logic, engineering formulas, Excel generation, production configuration, or the live Lightsail deployment while developing Version11.

Version10 remains the exact pipeline demonstrated to the Estimation Team.

---

## RULE 2 — All new accuracy development happens in Version11

Edit only files under `Version11/`.

If a change appears to require a Version10 edit, stop and report. Do not “quickly patch” Version10.

---

## RULE 3 — Every accuracy change must be isolated and measurable

One workstream, one hypothesis, one comparison against the V10 baseline.

Do not bundle detection, matching, diameter, and engineering changes in a single commit/milestone unless each is separately measurable.

---

## RULE 4 — Do not modify deterministic engineering formulas merely to compensate for reinforcement interpretation errors

Geometry, spacers/cover, development length, anchorage, hooks/bends, cut lengths, stirrup quantity, piece generation, unit weight, steel kg, BBS, and Excel remain deterministic engineering authority.

If Vision/matching is wrong, fix interpretation — do not retune kg formulas to hide it.

---

## RULE 5 — Vision is evidence/interpretation support, not uncontrolled quantity authority

Hybrid/Vision may inform **what** reinforcement exists (count / diameter / role within the W.6 handoff contract).

Deterministic engineering determines **how** it is quantified.

W.6 must continue to protect cut length, stirrup quantity, geometry, spacers, kg, and BBS.

---

## RULE 6 — Every new rule must have regression coverage

No new detection, matching, diameter, or engineering rule is accepted without a test that would fail if the rule is removed or inverted.

---

## RULE 7 — No change is accepted solely because aggregate accuracy improves

A pooled % increase is not sufficient. Inspect beam-level winners and losers.

---

## RULE 8 — Evaluate both improvements and regressions at beam level

Report:

- beams improved
- beams unchanged
- beams regressed
- missing / extra / diameter / ownership error counts

---

## RULE 9 — Use Version10 as the comparison baseline for every Version11 milestone

Compare V11 output to the frozen V10 W.19.1 behaviour, not to an intermediate V11 experiment, unless the milestone explicitly names a prior V11 checkpoint.

---

## RULE 10 — Do not deploy Version11 to the production URL until an explicit deployment phase is authorized

Do not SSH to Lightsail, restart Gunicorn, change Nginx, change systemd, change `:8001` files, or consume Claude credits for casual validation.

Local V11 execution is development-only.
