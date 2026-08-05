# QA.2B.1 — Production Regeneration Summary

**MODEL_VERSION:** 9.6.1
**Generated:** 2026-08-05T12:01:28.908983+00:00
**Overall PASS:** True
**Overall elapsed:** 3065.66s

## Purpose

Fresh production workbooks from DXF using the integrated 9.6.0 pipeline, then QA.2A ground-truth benchmark on those workbooks only.

## Per drawing set

### First Set Drawings (`First`)

- Pipeline execution time: **447.3s**
- Workbook generation: included in pipeline (VB1)
- Benchmark time: **10.38s**
- Workbook: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_First_Set_Drawings_20260805_164023\data\output\Production_Output\Estimation_Output.xlsx`
- Pipeline success: `True`

### Second Set Drawings (`Second`)

- Pipeline execution time: **1147.01s**
- Workbook generation: included in pipeline (VB1)
- Benchmark time: **20.24s**
- Workbook: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Second_Set_Drawings_20260805_164750\data\output\Production_Output\Estimation_Output.xlsx`
- Pipeline success: `True`

### Third Set Drawings (`Third`)

- Pipeline execution time: **1415.52s**
- Workbook generation: included in pipeline (VB1)
- Benchmark time: **21.49s**
- Workbook: `C:\Users\nishanth.h\SteelBeamEstimator\Version9\data\web_runs\qa2_Third_Set_Drawings_20260805_170657\data\output\Production_Output\Estimation_Output.xlsx`
- Pipeline success: `True`

## Validation

- [x] all_sets_reprocessed
- [x] all_workbooks_regenerated
- [x] no_reuse_detected
- [x] benchmark_executed
- [x] hashes_differ_from_prior
- [x] reuse_flag_false

