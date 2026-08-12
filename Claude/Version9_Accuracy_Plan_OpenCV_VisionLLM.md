# Version 9 Accuracy Plan — OpenCV + Vision LLM Adoption

**Baseline:** MODEL\_VERSION 8.9.5 (frozen V8) · QA.2A benchmark 8.9.1
**Current accuracy:** Overall 58.07% · Beam detection 93.92% · Bar detection 41.52% · Bar match 24.16% · Steel KG 72.69%
**Goal:** Bar detection ≥ 85%, bar match ≥ 70%, steel KG ≥ 92% across all 3 benchmark sets, without modifying the certified V8 spine.

\---

## 1\. What the QA.2A data actually says

The 993 errors decompose into four independent root causes:

|#|Root cause|Evidence|Fix class|
|-|-|-|-|
|RC-1|Stirrups \& stirrup hooks not reaching output|182 STIRRUP + 81 STIRRUP\_HOOK missing rows ≈ 6,700 pieces; Y10 98–99% missing, Y8 72–97% missing (Sets 2/3)|Discovery + association + piece generation|
|RC-2|Spacer bars never computed|98/98 SPACER\_BAR missing; Y25 82–100% missing (\~436 pieces)|**Pure rule computation — no CV needed**|
|RC-3|Main-bar diameter swaps (top↔bottom / view confusion)|137/176 Wrong-Diameter rows are TOP\_MAIN/BOTTOM\_MAIN with qty correct; paired with the "missing" counterpart on the other face|Spatial association|
|RC-4|TOP\_EXTRA / BOTTOM\_EXTRA over-generation|114 + 40 EXTRA rows with est\_qty=0|Deduplication + role placement|

Cross-check: Y16/Y20 aggregate quantities are within 2.5–6.5% of ground truth → **text reading of main-bar annotations is essentially solved**. The losses are (a) derived pieces never computed, (b) stirrup annotations lost before piece generation, (c) annotations attached to the wrong beam face/span.

**Implication:** CV/Vision should be aimed at RC-1, RC-3, RC-4. RC-2 is a deterministic rule fix and should ship first because it is the cheapest large KG recovery.

\---

## 2\. Architecture principle

The deterministic V8 engine stays **authoritative and reproducible**. OpenCV and Vision LLM enter as **evidence providers** feeding the existing hypothesis machinery — specifically Phase R.2.1D (Evidence \& Hypothesis Engine) and R.3.1 (Drawing Relationship Engine) — never as direct mutators of `beam\\\_reinforcement\\\_models\\\_production.json`.

```
DXF ─→ V.ROOT.1 ─→ R.1 (text discovery) ─────────────┐
        │                                             ▼
        ├─→ NEW V9.RENDER  beam-tile PNG renderer     R.2.1D  Evidence \\\& Hypothesis
        │        │                                    (now consumes 3 evidence types:
        │        ├─→ NEW V9.CV   OpenCV geometric      TEXT + GEOMETRY + VISION)
        │        │              evidence (stirrup           │
        │        │              rectangles, bar lines,      ▼
        │        │              leader arrows)         R.3 / R.3.1 association
        │        └─→ NEW V9.VLM  Vision-LLM                 │
        │                       independent read            ▼
        │                                             R.1.2A → R.1.3 → V.B.1
        └────────────────────────────────────→ NEW V9.SPACER rule engine (RC-2)
```

All new stages are additive runners under `Version9/Run\\\_PY/` with their own `src/PhaseV9\\\_\\\*` packages, run-context aware (`STEEL\\\_RUN\\\_ROOT` / `STEEL\\\_OUTPUT\\\_ROOT`), soft-exit semantics like every other stage.

\---

## 3\. Tracks and sequence

### Track 0 — Deterministic recoveries (weeks 1–2, no CV) — target +12–15 pts overall

**T0.1 Spacer bar rule engine (RC-2).** Implement `Requirement\\\_Rules.txt` verbatim: wherever ≥2 longitudinal bars overlap in a span, Ø25 @ 1 m, `N = ceil(overlap\\\_length/1m)+1`, cutting length = beam width − 2×cover (cover from R.2A context). Inputs already exist: bar spans from R.1.3, cover from EngineeringContext. Output: SPACER\_BAR pieces injected at R.1.3 piece-generation stage behind a config flag `enable\\\_spacer\\\_rule`.
**T0.2 Stirrup hook derivation (RC-1b).** For every stirrup group that reaches output, emit the hook pieces (135° hook length per General Notes anchorage table / grade). 81 missing rows are recoverable the moment their parent stirrups exist — so land T0.2 with Track 1.
**T0.3 Diameter sanity gate.** Rule: a TOP\_MAIN/BOTTOM\_MAIN pair on the same beam cannot silently share one annotation. When R.3.1 assigns the same source annotation to both faces, or leaves one face empty while the other has 2 candidates, raise a `FACE\\\_CONFLICT` hypothesis instead of committing — consumed by Track 2 arbitration.
**Acceptance:** re-run QA.2A; SPACER\_BAR missing 98→<10; Y25 diff % <15 on all sets.

### Track 1 — Stirrup recovery: OpenCV geometric evidence (weeks 2–5) — target +10–14 pts

**T1.1 Beam-tile renderer (`V9.RENDER`).** Render each beam's detail region (elevation + section) from DXF to PNG at fixed scale (e.g., 30 px/inch of paper space; \~200 DPI equivalent) using `ezdxf.addons.drawing` with the matplotlib backend. Tile bounds come from `beam\\\_registry.json` centroids + R.1.1A detail segmentation. Cache tiles under `<output\\\_root>/PhaseV9\\\_render/<beam\\\_id>.png` with a manifest mapping pixel↔DXF coordinates (needed to project findings back).
**T1.2 OpenCV stirrup detector (`V9.CV`).** Two complementary detectors, both deterministic:

* **Vector-space first:** query DXF entities directly (LWPOLYLINE closed rectangles with aspect ratio ≈ beam section minus cover, small closed polygons in section views, evenly-spaced short vertical LINE clusters in elevation = stirrup tick marks). Evenly-spaced tick spacing measured geometrically is an independent estimate of `@spacing` — cross-checks the parsed `2L-Y8@150C/C` value.
* **Raster fallback (OpenCV on the tile):** `cv2.findContours` + `minAreaRect` for closed stirrup rectangles in section views; Hough line clustering for tick trains where geometry was exploded/blocked. Only fires when vector query finds nothing.
* Output per beam: `stirrup\\\_geometry\\\_evidence.json` — {legs, section rectangle found y/n, tick count, measured pitch mm, zone boundaries for Type3}.
**T1.3 Evidence fusion in R.2.1D.** New evidence type `GEOMETRY\\\_STIRRUP`. Fusion rules: text annotation present + geometry confirms → confidence HIGH, commit. Text present, geometry absent → commit with WARN (current behavior). **Geometry present, text missing/unassociated → synthesize a stirrup hypothesis** with dia from nearest text or general-notes minimum, flag for VLM confirmation (Track 2). This directly attacks the 182 missing stirrup rows, which are mostly "annotation exists but never associated to this beam."
**T1.4 Type3 zone resolution.** Use measured tick pitch changes / support locations (R.3 `SupportLocations.json`) to place the 100/200/100 zone boundaries physically instead of equal-thirds fallback.
**Acceptance:** STIRRUP missing 182→<30; Y8/Y10 diff % <20 per set; R.1.6.2 stirrup coverage PASS on all 3 sets.

### Track 2 — Vision LLM association arbiter (weeks 4–8) — target +8–12 pts

Scope it to the three judgments text parsing provably fails at:
**T2.1 Face assignment (RC-3).** For every beam with a `FACE\\\_CONFLICT` hypothesis or WRONG\_DIAMETER-prone pattern (both faces present, diameters differ), send the beam tile + the candidate annotations (with pixel boxes drawn on the image) to a vision-capable Claude call. Ask one narrow structured question: *"For each numbered annotation, is it attached to the TOP chord, BOTTOM chord, side face, or a section detail? Return JSON."* Constrained single-purpose prompts keep it reliable and cheap.
**T2.2 Extra vs main disambiguation (RC-4).** Same tile, question: which annotations denote full-span bars vs curtailed extras (leader points to a shorter bar segment / has a length dimension like `2150`); flag duplicates pointing at the same physical bar across views. Targets the 114 phantom TOP\_EXTRA rows.
**T2.3 Orphan stirrup confirmation.** Confirms/denies Track 1's synthesized stirrup hypotheses ("does this section view show a closed stirrup? how many legs?").
**Operating rules:**

* VLM runs **only on flagged beams** (conflict/orphan/low-confidence), not all beams — expected ≤30% of beams, keeping cost and latency bounded.
* Responses must validate against a JSON schema (`jsonschema` already in requirements); non-conforming → retry once → fall back to deterministic answer.
* Every VLM verdict is logged with the tile image hash into `vision\\\_evidence.json` — auditable, and disagreements feed R.1.5 (Error Intelligence) and R.1.6 (Rule Synthesis) as the backlog for new deterministic rules. **The long-term goal is the VLM teaching the rule engine, shrinking VLM reliance over time.**
* Config flag `enable\\\_vision\\\_arbiter`; offline runs work without network (deterministic fallback), preserving reproducibility of the certified path.
**Acceptance:** WRONG\_DIAMETER 176→<40; TOP\_EXTRA EXTRA 114→<25; WRONG\_ROLE 58→<20.

### Track 3 — Continuous measurement (parallel, week 1 onward)

* Promote QA.2A into a one-command regression gate: `run\\\_phase\\\_qa2a` on all 3 sets after every track lands; store the role×status matrix per run so we can attribute each accuracy point to a change.
* Add per-track KPI dashboards (missing-by-role trend) to the QA.2A workbook.
* Definition of done for V9.0.0: overall ≥ 80% on Sets 1–2, ≥ 72% on Set 3, no regression in beam detection.

### Deliberately deferred

* **OCR:** inputs are native DXF text; only revisit if a set arrives with exploded SHX text or raster underlays (add a detector in V.ROOT.1 that flags IMAGE entities / zero TEXT count).
* **YOLO:** needs labeled raster data; ROI is poor while inputs are vector. If ever needed, training data can be auto-generated by projecting V9's validated bar model onto rendered tiles (weak labels). Park until a scanned-drawing requirement exists.

\---

## 4\. Projected impact vs error ledger

|Fix|Error rows addressed|Expected recovery|
|-|-|-|
|T0.1 spacer rule|98 missing + 9 wrong-dia|\~95%|
|T0.2 + T1 stirrups/hooks|263 missing + 11 wrong-qty|75–85%|
|T2.1 face arbiter|\~137 wrong-dia + paired "missing" mains (\~90 rows)|70–80%|
|T2.2 extra dedup|154 extra + 58 wrong-role|70%|
|Residual (notation gaps via R.2.0.1 backlog)|remainder|rule-by-rule|

Recovering the stirrup/spacer mass alone moves steel-KG accuracy from \~73% into the high 80s, because Y8/Y10/Y25 losses are the bulk of the KG gap on Sets 2–3.

## 5\. First concrete steps (this week)

1. Create `Version9/src/PhaseV9\\\_spacer\\\_rule/` + runner; wire behind `enable\\\_spacer\\\_rule`; re-run QA.2A → confirm SPACER\_BAR row recovery.
2. Prototype `V9.RENDER` on Set 1 (18 beams) with `ezdxf.addons.drawing`; verify pixel↔DXF manifest round-trips.
3. Run the vector-space stirrup query (T1.2) on the 3 sets read-only and count how many of the 182 missing stirrup beams show detectable stirrup geometry — this quantifies Track 1's ceiling before writing fusion code.
4. Hand-pick 10 WRONG\_DIAMETER beams, run a manual Vision-LLM prompt on their tiles, and measure face-assignment agreement with the estimator sheet — validates Track 2's prompt design before building the stage.

