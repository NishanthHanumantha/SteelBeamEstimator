# What Claude Sees — Cropped Beam Images and JSON Answers

**Live path:** W.8 evidence → W.5 live call → C.5 prompt/schema → Claude Vision → D.2 / W.6 handoff  
**Contract:** exactly **two PNGs per beam** (Image 1 = CONTEXT, Image 2 = DETAIL) and **one JSON object** back. No steel kg, BBS, or cut length from Claude.

---

## 1. The request (what we send)

For each eligible beam, production does **not** send the whole DXF. It sends two cropped PNGs plus a text prompt.

```
Reinforcement DXF
        │
        ▼
T.1 envelopes  +  B.1 adaptive crop extents
        │
        ▼
M.1 renderer  →  two PNGs
        │
        ├─ Image 1  CONTEXT   (neighbours + where this beam sits)
        └─ Image 2  DETAIL    (this beam’s bars, marks, stirrups)
        │
        ▼
encode_png (base64)  →  Anthropic messages.create
        content[0] = image  (context)
        content[1] = image  (detail)
        content[2] = text   (user prompt: TARGET BEAM ID + JSON schema)
        system     = C.5 SYSTEM_PROMPT
```

### On disk (after a Hybrid run)

```
<data/web_runs/<run_id>>/data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence/
  B12/
    evidence_manifest.json
    context/selected.png     ← Image 1 sent to Claude
    detail/selected.png      ← Image 2 sent to Claude
```

Fallback if B.1 adaptive crops fail: copy T.1 `opencv_renders/<beam>_crop.png` as **both** context and detail (same image twice). Manifest records that.

### Code that builds and sends the images

| Step | File | What it does |
|---|---|---|
| Crop extents | `src/PhaseP2610B_adaptive_beam_detail_crop/envelope.py` | Adaptive context vs detail windows on the DXF. |
| Render PNG | `src/PhaseM.1_engineering_vision_dataset/dxf_renderer.py` | Renders those windows to PNG. |
| Package | `src/PhaseW8_production_vision_evidence/generator.py` | Writes `hybrid_evidence/<beam>/{context,detail}/selected.png`. |
| Pick files | `src/PhaseW5_production_hybrid_shadow/visual_sources.py` | Prefers W.8 pair, else T.1, else W.6 crop. |
| Base64 | `src/PhaseP2610C3_visual_completeness_claude_shadow/claude_client.py` `encode_png` | `{ media_type, data_base64, role, path }`. |
| API payload | `src/llm/claude_client.py` `generate_vision_response` | Image block, image block, then text prompt. |
| Prompt | `src/PhaseP2610C5_stratified_vision_semantic_benchmark/vision_prompt.py` | System rules + user schema for this `beam_id`. |

`n_images` is always **2** on the live C.5 path (`claude_call.py`).

---

## 2. What the two images mean

| | CONTEXT (Image 1) | DETAIL (Image 2) |
|---|---|---|
| Purpose | Find the **target beam** among neighbours | Read **that beam’s** reinforcement |
| Typical crop | Wider: neighbouring details + title | Tighter: bars, marks, stirrup notes |
| Claude rule | Use it to identify the beam; do not treat neighbour marks as this beam | Primary evidence for groups and stirrups |

The user prompt always states:

- `TARGET BEAM ID: B12` (example)
- `Image 1 is CONTEXT. Image 2 is DETAIL.`
- Return **only JSON** (no markdown fences)

Claude is told **not** to invent length from labels, **not** to merge two physical groups just because the spec is the same, and **not** to compute steel / BBS / cut length.

---

## 3. The answer (what Claude sends back)

Claude must return **one JSON object**. Production parses it with `vision_contract.parse_and_validate`. If JSON is bad or `target_beam_id` does not match, the beam is **fail-closed** (deterministic R.1.3 is kept).

### Shape of the answer

```json
{
  "target_beam_id": "B12",
  "target_identified": true,
  "association_confidence": 0.94,
  "groups": [
    {
      "physical_group_id": "G1",
      "layer": "TOP",
      "spec": "4-Y20",
      "bar_count": 4,
      "role_hypothesis": "MAIN",
      "role_confidence": 0.93,
      "support_scope": "FULL_SPAN",
      "relative_length_evidence": "UNKNOWN",
      "span_relationship": "FULL_SPAN",
      "confidence": 0.93,
      "evidence": "four Y20 along top of target beam"
    }
  ],
  "stirrups": [
    {
      "spec": "2L-Y8@150C/C",
      "confidence": 0.85,
      "evidence": "stirrup mark at midspan of target beam"
    }
  ],
  "ambiguities": [],
  "neighbour_evidence_detected": false,
  "response_status": "OK"
}
```

### What each field is for

| Field | Meaning |
|---|---|
| `target_beam_id` | Must equal the ID we asked for |
| `target_identified` | Did Claude find that beam in the two images? |
| `groups[]` | Physical bar groups (layer + spec + count). `role_hypothesis` MAIN/EXTRA is **not** required to be confident |
| `stirrups[]` | Visual stirrup **spec** only — not quantity engineering |
| `ambiguities` | What Claude is unsure about |
| `neighbour_evidence_detected` | True if neighbour-beam marks were visible (must not be used as target evidence) |

Forbidden in the Claude payload: production actions, steel quantity, BBS, cut length, recover instructions.

### After the answer

```
raw_text (Claude)
    → parse_and_validate          (C.5 vision_contract)
    → extract_vision_payload      (D.1 normalizer)
    → D.2 hybrid resolver         (Vision vs R.1.3)
    → W.6 handoff.py              patches quantity / diameter / role only
    → VB.1                        still computes kg, BBS, Excel from engineering
```

---

## 4. Where to show a real run

Crops and answers are **per estimation run**, not in git.

| What to show | Path under the run folder |
|---|---|
| Crops sent | `data/output/PhaseW6_hybrid_semantic_resolution/hybrid_evidence/<BEAM>/{context,detail}/selected.png` |
| Crop provenance | `.../hybrid_evidence/<BEAM>/evidence_manifest.json` |
| Per-beam Claude parse / Hybrid | `data/output/PhaseW5_production_hybrid_shadow/hybrid_shadow_report.json` (`beams[]`) |
| Run-level Hybrid | `data/output/PhaseW6_hybrid_semantic_resolution/hybrid_observability.json` |
| What was patched | `.../hybrid_handoff_ledger.json` |

On Lightsail the run folder is:

`Version10/data/web_runs/<run_id>/`

To open context + detail + JSON side by side from a downloaded run:

```
python Version10/tools/view_hybrid_evidence.py <path-to-run-folder>
```

That writes `hybrid_evidence_gallery.html` next to the run and prints the file path. Open it in a browser. It does **not** call Claude.

---

## 5. One-slide story for estimators

1. **We crop** two pictures of one beam from the DXF (wide context + tight detail).  
2. **We send** those two PNGs + “this is beam B12, return this JSON”.  
3. **Claude answers** with groups like `4-Y20` TOP MAIN and a stirrup spec.  
4. **Excel still comes from** the deterministic engine; Hybrid may only change *what* bars (count / diameter / role), never cut length or kg formulas.
