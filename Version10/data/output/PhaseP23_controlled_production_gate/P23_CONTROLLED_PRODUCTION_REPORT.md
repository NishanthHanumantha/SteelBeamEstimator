# Phase P2.3 — Controlled Production Gate + Re-benchmark

- MODEL_VERSION: `10.5.5`
- STATUS: `PASS`
- Decision class: `PASS - DIAGNOSTIC SUCCESS / ENGINEERING IMPACT UNCLEAR`
- Production policy: `E_STRONG_COMBINED`
- Reference candidate: `B16::LDR::7A1FFD68`
- Accepted under Policy E: `1`
- Ready for broader E validation: `False`

## Accuracy delta (overall)

```json
{
  "Beam Detection": {
    "baseline": 82.95,
    "controlled": 82.95,
    "absolute_pp": 0.0,
    "pct_point_change": 0.0,
    "label": "82.95% -> 82.95% (+0.0 percentage points)"
  },
  "Bar Detection": {
    "baseline": 46.04,
    "controlled": 46.04,
    "absolute_pp": 0.0,
    "pct_point_change": 0.0,
    "label": "46.04% -> 46.04% (+0.0 percentage points)"
  },
  "Bar Matching": {
    "baseline": 36.74,
    "controlled": 36.74,
    "absolute_pp": 0.0,
    "pct_point_change": 0.0,
    "label": "36.74% -> 36.74% (+0.0 percentage points)"
  },
  "Steel Accuracy": {
    "baseline": 72.21,
    "controlled": 72.21,
    "absolute_pp": 0.0,
    "pct_point_change": 0.0,
    "label": "72.21% -> 72.21% (+0.0 percentage points)"
  },
  "Overall Accuracy": {
    "baseline": 59.48,
    "controlled": 59.48,
    "absolute_pp": 0.0,
    "pct_point_change": 0.0,
    "label": "59.48% -> 59.48% (+0.0 percentage points)"
  }
}
```

## Bottleneck

Recovered leader/annotation chain already partially owned; Estimation_Output.xlsx not regenerated in P2.3 controlled experiment, so steel accuracy formulas cannot reflect visual ownership recovery yet.

## Causal chain

P2.2 E candidate -> effective ownership overlay -> graph ARR/LTGT propagation -> adaptive render comparison. Steel Excel not regenerated.
