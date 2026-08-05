# Benchmark Summary — Version 9.6.1

**Phase:** QA.2B.1
**MODEL_VERSION:** 9.6.1
**Generated:** 2026-08-05T12:01:28.921033+00:00

Ground-truth benchmark against **freshly regenerated** `Estimation_Output.xlsx` workbooks (no reuse).

## Aggregate

- Recommendation: `A — Ground-truth framework operational; prioritize top error categories for Version9 accuracy work.`
- Compared drawing sets: **3**
- Benchmark elapsed: **53.17s**

## Per drawing set

### First Set Drawings

- Model Excel: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_First_Set_Drawings_20260805_164023\data\output\Production_Output\Estimation_Output.xlsx`
- Beam detection: **100.0%**
- Bar detection: **81.18%**
- Bar matching accuracy: **34.78%**
- Steel accuracy: **99.83%**
- Estimator kg / Model kg: **1423.606** / **1421.211**
- Missing bars: **16**
- False positives / extra: **None**

### Second Set Drawings

- Model Excel: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Second_Set_Drawings_20260805_164750\data\output\Production_Output\Estimation_Output.xlsx`
- Beam detection: **95.52%**
- Bar detection: **71.76%**
- Bar matching accuracy: **35.74%**
- Steel accuracy: **85.5%**
- Estimator kg / Model kg: **10419.298** / **11930.01**
- Missing bars: **109**
- False positives / extra: **None**

### Third Set Drawings

- Model Excel: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Third_Set_Drawings_20260805_170657\data\output\Production_Output\Estimation_Output.xlsx`
- Beam detection: **90.48%**
- Bar detection: **63.52%**
- Bar matching accuracy: **17.91%**
- Steel accuracy: **87.89%**
- Estimator kg / Model kg: **16046.15** / **14103.297**
- Missing bars: **170**
- False positives / extra: **None**

## Statistics

```json
{
  "drawing_sets": 3,
  "pipelines_ok": 3,
  "avg_runtime_s": 1003.28,
  "overall_accuracy_pct": 70.23,
  "total_errors": 949
}
```

