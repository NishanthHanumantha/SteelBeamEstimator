# P2.1 Leader Tip / Chain Acceptance QA Report

- MODEL_VERSION: `10.5.3`
- TYPE: DIAGNOSTIC / COUNTERFACTUAL ONLY
- STATUS: `PASS`
- PRODUCTION OWNERSHIP CHANGED: NO
- T18 CHANGED: NO

## Population
- Leaders analysed: `23`
- Recovery-eligible (QA.4.3): `5`

## Root answers
1. R2 too strict? `YES`
2. Problem is tip rule? `YES`
3. Problem is production envelope? `PARTIAL`
4. Chain evidence safely recovers any of 5? `YES`
5. Best policy: `E_STRONG_COMBINED`
6. Leaders per policy: `{'A_CURRENT': 0, 'B_CHAIN_EVIDENCE': 1, 'C_CHAIN_ENDPOINT': 1, 'D_CHAIN_GEOMETRIC': 5, 'E_STRONG_COMBINED': 1}`
7. Annotations reachable: `5`

Recommended next phase: `OPTION 2 - Leader-chain evidence enhancement`

Failed gates: `[]`
