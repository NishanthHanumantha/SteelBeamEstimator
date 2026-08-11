# P2.5.0 Beam Evidence Rendering & Crop QA

- MODEL_VERSION: `10.6.0`
- SCOPE: `FOURTH_SET_ONLY`
- MODE: `DIAGNOSTIC_ONLY`
- ENGINEERING_CHANGES: `NONE`

## Summary metrics

1. MODEL_VERSION: `10.6.0`
2. Fourth Set beams processed: **118**
3. Successful renders: **118**
4. Failed renders: **0**
5. Crop QA pass %: **77.12%**
6. Beam presence %: **100.0%**
7. Reinforcement evidence coverage: **99.15%**
8. Annotation evidence coverage: **99.15%**
9. Leader evidence coverage: **99.15%**
10. Leader-chain completeness: **77.12%**
11. Evidence recall (GT-supported reinforcement presence): **99.11%** — GT annotation/leader recall not claimed — estimator GT lacks annotation/leader entity IDs.
12. Beams requiring crop expansion: **116**
13. Clipped evidence cases: **0**
14. Neighboring-beam ambiguity cases: **0**
15. Rendering failures: **0**
16. Top crop/evidence failure causes: `[('COMPLETE_LEADER_CHAIN', 26), ('RELEVANT_REINFORCEMENT_PRESENT', 1), ('RELEVANT_ANNOTATION_PRESENT', 1)]`

- Determinism: **PASS**
- Regression unchanged: **True**
