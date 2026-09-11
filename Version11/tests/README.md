# Tests in Version11

Tests were not duplicated into a second tree. Locations:

| Coverage | Path |
|---|---|
| W.2 smoke / adapter / Flask | `webapp/tests/test_w2_smoke.py` |
| W.16 metadata | `webapp/tests/test_w16_metadata_aggregation.py` |
| W.19.1 Excel metadata binding | `webapp/tests/test_w191_excel_metadata_binding.py` |
| W.6 Flask hybrid authority | `webapp/tests/test_w6_hybrid_authority.py` |
| W.6 package unit tests | `src/PhaseW6_hybrid_production_authority/unit_tests.py` |
| W.18B spacer | `src/PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py` |

From repository root:

```
python -m unittest Version11.webapp.tests.test_w2_smoke
python -m unittest Version11.src.PhaseW6_hybrid_production_authority.unit_tests
python -m pytest Version11/src/PhaseV9_spacer_rule/tests/test_w18b_spacer_rule.py
```

Do not point these at Version10. Do not consume Claude credits for casual runs.
