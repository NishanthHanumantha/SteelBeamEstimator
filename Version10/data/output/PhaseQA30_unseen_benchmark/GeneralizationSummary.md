# Generalization Summary — Phase QA.3.0

**MODEL_VERSION:** 10.0.0
**Generated:** 2026-08-06T15:04:23.033357+00:00

Estimator Output Excel used **ONLY during benchmarking** (never during production).

## Overall Metrics

| Metric | Value |
|--------|------:|
| Beam Detection | 82.95% |
| Bar Detection | 46.04% |
| Bar Matching | 36.74% |
| Steel Accuracy | 72.21% |
| Overall Accuracy | 59.48% |

## Drawing Set-wise Results

| Drawing Set | Beam Det | Bar Det | Bar Match | Steel | Overall |
|-------------|---------:|--------:|----------:|------:|--------:|
| Fourth Set Drawings | 78.32% | 39.89% | 37.33% | 58.39% | 53.48% |
| Fifth Set Drawings | 76.47% | 40.25% | 34.3% | 61.69% | 53.18% |
| Sixth Set Drawings | 95.86% | 61.45% | 38.87% | 96.54% | 73.18% |

## Engineering Error Summary

- Missing bars: 2235
- Diameter mismatch: 356
- Extra bars: 255
- Ownership issues: 105
- Missing beams: 81
- Extra beams: 10
- Rendering mismatch: 3
- Stirrup mismatch: 0
- Side-face reinforcement mismatch: 0
- Development Length mismatch: 0

## Generalization Assessment

### Engineering strengths
- Pipeline completes end-to-end on completely unseen DXF sets

### Engineering weaknesses
- Beam detection drops on unseen projects
- Steel accuracy degrades on unseen projects
- Bar matching is the primary generalization gap
- Bar detection incomplete on unseen reinforcement plans

### Largest failure modes
- Missing bars (2235)
- Diameter mismatch (356)
- Extra bars (255)
- Ownership issues (105)
- Missing beams (81)

### Recommended engineering improvements
- Improve bar-role / diameter matching on unfamiliar annotation styles
- Harden beam discovery for novel mark naming / framing conventions
- Review ownership / shared-scope edge cases that drive Missing Bar / Extra Bar
- Investigate diameter mismatches before changing weight formulas
- Keep production DXF-only; use these GT gaps to prioritize Version10 engineering work
