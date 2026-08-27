# PHASE W.14 — MEDIUM-SCALE PRODUCTION RUN REPORT

Date: 2026-08-27  
Run ID: **`20260827_093245_a32541a7`**  
Drawing: Galera GF (2nd Set)  
Beam count: **65**

## Result

The production pipeline completed: upload → processing → P2.6.10 evidence → Claude Vision → E.2 → D.2 → R13 semantic patch → VB.1 → Excel → result page → download.

- `status=success`
- `result_lifecycle=DOWNLOAD_READY`
- `hybrid_status=HYBRID_SUCCESS`
- `identity_ok=true`
- `unexplained=0`

## Hybrid lifecycle table

| Metric | Count |
| --- | ---: |
| Total beams | 65 |
| Hybrid eligible | 65 |
| Evidence generated | 64 |
| Evidence unavailable | 1 |
| Claude attempted | 64 |
| Claude API success | 64 |
| Claude API failure | 0 |
| Claude timeout | 0 |
| Parse valid | 64 |
| Parse invalid | 0 |
| Schema valid | 64 |
| Schema invalid | 0 |
| E.2 accepted | 64 |
| E.2 rejected | 0 |
| D.2 resolved | 64 |
| R13 patches applied | 61 |
| Deterministic fallback | 1 |
| Unexplained | 0 |

Accounting identity:

```
Eligible 65
  = D.2 resolved 64
  + deterministic fallback 1
  + unexplained 0
```

R13: 64 patch-eligible, 61 applied, 3 Hybrid-resolved beams had no matching semantic fields to patch. That is an explicit patch-not-applied count, not an unexplained beam state.

## API recovery checkpoint

| Checkpoint | Value |
| --- | --- |
| First API success | attempt 1, beam `B1` |
| 26th API success | attempt 26, beam `B30` |
| 27th API success | attempt 27, beam `B31` |
| Final successful API call number | 64 |
| First API failure | none |

**PREVIOUS_26_CALL_CLIFF_NOT_REPRODUCED**

Claude API success continued substantially beyond the previous W.12/W.13 failure cliff of 26 successful calls. All 64 attempted Vision calls succeeded.

## Beam that did not reach HYBRID_RESOLVED

| Field | Value |
| --- | --- |
| beam_id | `B35` |
| stopping stage | `EVIDENCE_UNAVAILABLE_WITH_REASON` |
| reason code | `EVIDENCE_UNAVAILABLE` |
| provider category | `OTHER` (not a provider API failure) |
| HTTP status | none |
| retry count | none |
| timeout flag | false |
| skip_reason | `NO_USABLE_EVIDENCE` |
| deterministic fallback | yes |

Visual prep recorded `render_failed=1` for this beam. No Claude call was attempted.

## Evidence coverage (inspect only; no crop redesign)

| Source | Count |
| --- | ---: |
| P2.6.10 primary (`P2610B1_ADAPTIVE_CONTEXT_DETAIL`) | 41 |
| W.8 mixed / T1 compatibility (`W8_SELECTED_MIXED`) | 9 |
| W.6 envelope fallback (`W6_ENVELOPE_RENDER`) | 14 |
| Unavailable | 1 |
| Same-SHA context/detail | 14 |
| Distinct context/detail | 50 |

The 14 same-SHA pairs match the 14 `W6_ENVELOPE_RENDER` fallbacks. That is an explicit compatibility/envelope fallback, not unexpected duplication. Vision still resolved those 14 beams.

## Timing (ACTUAL_OBSERVED from production status/progress)

| Interval | Seconds |
| --- | ---: |
| Total wall time (`duration_s`) | 1376.88 |
| Preprocessing before visual evidence (T1 + geometry, to ~77.7 s) | ~78 |
| Evidence generation (“Preparing visual evidence”, ~77.7–680.9 s) | ~603 |
| Average evidence generation per beam (603 / 65) | ~9.3 |
| Hybrid stage (`hybrid_latency_s`) | 695.313 |
| Vision total (same Hybrid live-call window; 0 API failures) | 695.313 |
| Average Vision time per attempted beam (695.313 / 64) | 10.86 |
| Average Vision time per successful beam | 10.86 |
| Excel / result finalization after last Vision poll (~1364.5–1384.7 s) | ~20 |

Historical reference only (different drawing, 143 beams):

- W.11 Sixth Set: evidence ~3707 s, Vision ~1543 s, Claude 143/143 successful
- W.12 Sixth Set: 26 successful, 117 spend-limit failures

W.14 per-beam Vision time (~10.9 s) is similar to the W.11 successful-call rate. This is not claimed as a performance improvement.

## Engineering output

- Steel total: **11532.805 kg**
- Beam count: **65**
- Bar count: **356**
- Calculation method: `IS_456_DETERMINISTIC`
- Formula: `W = (pi*d^2/4) * cut_length * qty * 7850 / 1e9`

Deterministic overwrite check on pre/post Hybrid R13:

- `cut_length_overwrites = 0`
- `geometry_overwrites = 0`
- `stirrup_quantity_overwrites = 0`
