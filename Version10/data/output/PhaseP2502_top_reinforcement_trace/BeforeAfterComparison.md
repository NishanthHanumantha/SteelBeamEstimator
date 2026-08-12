# Before / After Comparison

## P2.5.0 (pre spatial fix)
- Crops included rejected far-elevation BAR::* → extreme tall images.
- Top reinforcement OWN::* may have been visible incidentally inside huge crops.

## P2.5.0.1 (accepted-only)
- Rejected BAR::* excluded → crops tight.
- reinforcement=[] because only PhysicalBar accepted IDs were considered.
- OWN::* TOP_BAR still present upstream but not packaged as reinforcement.

## Model belief vs reality
- Model rejected BAR::* (correct).
- Model accepted 4-Y25 → OWN::* (correct).
- Evidence package omitted OWN::* geometry (gap).
