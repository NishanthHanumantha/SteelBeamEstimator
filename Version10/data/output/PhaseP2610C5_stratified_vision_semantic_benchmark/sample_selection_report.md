# C.5 sample selection report

- Fourth Set ok=True count=0
- candidate records=135
- selected=['B119', 'B68', 'B133', 'B139', 'B103', 'B100', 'B17', 'B129', 'B46', 'B100A']
- notes=['PRIOR_CONTROL_EXCLUDED_GENERIC']
- strata coverage=['LIMITED_RENDER', 'MAIN_EXTRA_COMPLEXITY', 'MULTI_GROUP_LONGITUDINAL', 'OTHER_HIGH_INFORMATION_COMPLEXITY', 'SAME_SPEC_DISTINCT_GROUPS', 'SIMPLE_LONGITUDINAL', 'STIRRUP_SEMANTIC_COMPLEXITY']

## Why each beam was selected

### B119

- strata: ['SIMPLE_LONGITUDINAL', 'STIRRUP_SEMANTIC_COMPLEXITY', 'LIMITED_RENDER']
- newly covered: ['LIMITED_RENDER', 'SIMPLE_LONGITUDINAL', 'STIRRUP_SEMANTIC_COMPLEXITY']
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: True
- deterministic_group_count: 3

### B68

- strata: ['MULTI_GROUP_LONGITUDINAL', 'MAIN_EXTRA_COMPLEXITY', 'STIRRUP_SEMANTIC_COMPLEXITY']
- newly covered: ['MAIN_EXTRA_COMPLEXITY', 'MULTI_GROUP_LONGITUDINAL']
- gate: VISION_READY
- mixed_source: True
- deterministic_group_count: 4

### B133

- strata: ['MULTI_GROUP_LONGITUDINAL', 'MAIN_EXTRA_COMPLEXITY', 'SAME_SPEC_DISTINCT_GROUPS', 'STIRRUP_SEMANTIC_COMPLEXITY', 'LIMITED_RENDER', 'OTHER_HIGH_INFORMATION_COMPLEXITY']
- newly covered: ['OTHER_HIGH_INFORMATION_COMPLEXITY', 'SAME_SPEC_DISTINCT_GROUPS']
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: False
- deterministic_group_count: 5

### B139

- strata: ['MULTI_GROUP_LONGITUDINAL', 'MAIN_EXTRA_COMPLEXITY']
- newly covered: []
- gate: VISION_READY
- mixed_source: True
- deterministic_group_count: 2

### B103

- strata: ['MULTI_GROUP_LONGITUDINAL', 'MAIN_EXTRA_COMPLEXITY', 'STIRRUP_SEMANTIC_COMPLEXITY', 'LIMITED_RENDER', 'OTHER_HIGH_INFORMATION_COMPLEXITY']
- newly covered: []
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: True
- deterministic_group_count: 5

### B100

- strata: ['MULTI_GROUP_LONGITUDINAL', 'MAIN_EXTRA_COMPLEXITY', 'STIRRUP_SEMANTIC_COMPLEXITY', 'LIMITED_RENDER']
- newly covered: []
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: True
- deterministic_group_count: 4

### B17

- strata: ['MULTI_GROUP_LONGITUDINAL', 'MAIN_EXTRA_COMPLEXITY', 'SAME_SPEC_DISTINCT_GROUPS', 'LIMITED_RENDER']
- newly covered: []
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: False
- deterministic_group_count: 4

### B129

- strata: ['MULTI_GROUP_LONGITUDINAL', 'MAIN_EXTRA_COMPLEXITY', 'LIMITED_RENDER']
- newly covered: []
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: True
- deterministic_group_count: 3

### B46

- strata: ['SIMPLE_LONGITUDINAL', 'SAME_SPEC_DISTINCT_GROUPS', 'LIMITED_RENDER']
- newly covered: []
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: True
- deterministic_group_count: 2

### B100A

- strata: ['STIRRUP_SEMANTIC_COMPLEXITY', 'LIMITED_RENDER']
- newly covered: []
- gate: VISION_READY_WITH_LIMITATIONS
- mixed_source: False
- deterministic_group_count: 2
