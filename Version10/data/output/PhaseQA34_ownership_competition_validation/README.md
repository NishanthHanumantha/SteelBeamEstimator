# Phase QA.3.4 — Ownership Competition Validation

MODEL_VERSION: `10.0.4`

Answers: when an entity is rejected, did another beam win it, or did it disappear?

## Key outputs
- `OwnershipCompetitionRegistry.json`
- `DroppedEntities.json` (most important)
- `OwnershipMigration.json`
- `CompetitionMatrix.json`
- `RegressionReport.json`
- `Visualisations/`

## Stats
- Rejected: 123
- Owned elsewhere: 19
- Dropped: 104

## Visuals
- sankey: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Sankey_ownership_flow.png`
- competition_matrix: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Beam_competition_matrix.png`
- network: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Competition_network.png`
- dropped_heatmap: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Dropped_entity_heatmap.png`
- margin_hist: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Ownership_margin_histogram.png`
- scatter: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Winner_vs_loser_scatter.png`
- top20_dropped: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Top20_disappearing_entities.png`
- beam_summary: `C:\Users\nishanth.h\SteelBeamEstimator\Version10\data\output\PhaseQA34_ownership_competition_validation\Visualisations\Beam_competition_summary.png`
