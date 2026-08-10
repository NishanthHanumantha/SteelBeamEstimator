# P2.1 Architecture Summary

```
QA.4.3 dropped leaders (23)
  ↓
Graph + T18 envelope (read-only)
  ↓
tip_in_envelope / evaluate_leader replay
  ↓
Evidence scorecard A–J
  ↓
Counterfactual policies A–E (diagnostic)
  ↓
Contamination SAFE / AMBIGUOUS / UNSAFE
  ↓
Root-cause + recommendation
  ↓
Regression / determinism gate
```

No production artefacts are written.
T18 ownership rules are not modified.
