# QA.3.3 Beam Ownership Cards

MODEL_VERSION: 10.0.3

## B14

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `48` / `46`
- T18 scored: `28` avg_score=`0.5768`
- Coverage%: `184.0` Ownership%: `67.86` Conflict%: `17.86`
- Owned / Rejected / Elsewhere: `19` / `2` / `0`
- Primary failure cause: **Conflict Resolution** (High)
- Detail: Neighbour/conflict reasons dominate: [('annotation_on_neighbour_side_of_mark', 2), ('tip_outside_envelope_and_supports', 1)]
- T18 stats: `{'accepted_annotation_count': 6, 'rejected_annotation_count': 1, 'accepted_bar_count': 8, 'rejected_bar_count': 0, 'accepted_leader_count': 5, 'cross_beam_leakage_count': 1}`

Rejected entities:
  - `LDR::FC909F97`  -> tip_outside_envelope_and_supports
  - `ANN-1ccca39c` 4-Y16 -> annotation_on_neighbour_side_of_mark

## B15

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `29` / `27`
- T18 scored: `23` avg_score=`0.3065`
- Coverage%: `158.82` Ownership%: `34.78` Conflict%: `26.09`
- Owned / Rejected / Elsewhere: `8` / `8` / `0`
- Primary failure cause: **Conflict Resolution** (High)
- Detail: Neighbour/conflict reasons dominate: [('no_owned_leader_bar_chain', 4), ('annotation_on_neighbour_side_of_mark', 4), ('tip_outside_envelope_and_supports', 4)]
- T18 stats: `{'accepted_annotation_count': 3, 'rejected_annotation_count': 4, 'accepted_bar_count': 3, 'rejected_bar_count': 0, 'accepted_leader_count': 2, 'cross_beam_leakage_count': 2}`

Rejected entities:
  - `LDR::798CE590`  -> tip_outside_envelope_and_supports
  - `LDR::749B70DC`  -> tip_outside_envelope_and_supports
  - `LDR::8534C4B8`  -> tip_outside_envelope_and_supports
  - `LDR::167CC70D`  -> tip_outside_envelope_and_supports
  - `ANN-9d3b965f` 4-Y20 -> no_owned_leader_bar_chain

## B16

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `56` / `48`
- T18 scored: `34` avg_score=`0.4559`
- Coverage%: `160.0` Ownership%: `52.94` Conflict%: `14.71`
- Owned / Rejected / Elsewhere: `18` / `7` / `0`
- Primary failure cause: **Conflict Resolution** (High)
- Detail: Neighbour/conflict reasons dominate: [('annotation_on_neighbour_side_of_mark', 6), ('tip_outside_envelope_and_supports', 4)]
- T18 stats: `{'accepted_annotation_count': 6, 'rejected_annotation_count': 3, 'accepted_bar_count': 8, 'rejected_bar_count': 0, 'accepted_leader_count': 4, 'cross_beam_leakage_count': 3}`

Rejected entities:
  - `LDR::7A1FFD68`  -> tip_outside_envelope_and_supports
  - `LDR::50092321`  -> tip_outside_envelope_and_supports
  - `LDR::DE845955`  -> tip_outside_envelope_and_supports
  - `LDR::49842AC8`  -> tip_outside_envelope_and_supports
  - `ANN-26e9834b` 4-Y20 -> annotation_on_neighbour_side_of_mark

## B18

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `37` / `29`
- T18 scored: `25` avg_score=`0.23`
- Coverage%: `193.33` Ownership%: `24.0` Conflict%: `16.0`
- Owned / Rejected / Elsewhere: `6` / `12` / `0`
- Primary failure cause: **Conflict Resolution** (High)
- Detail: Neighbour/conflict reasons dominate: [('no_owned_leader_bar_chain', 6), ('tip_outside_envelope_and_supports', 4), ('bar_y_outside_reinforcement_elevation', 4)]
- T18 stats: `{'accepted_annotation_count': 3, 'rejected_annotation_count': 4, 'accepted_bar_count': 1, 'rejected_bar_count': 4, 'accepted_leader_count': 2, 'cross_beam_leakage_count': 1}`

Rejected entities:
  - `BAR::59B0AF37`  -> bar_y_outside_reinforcement_elevation
  - `BAR::A5E16B4D`  -> bar_y_outside_reinforcement_elevation
  - `BAR::7CD782B5`  -> bar_y_outside_reinforcement_elevation
  - `BAR::1D706A9A`  -> bar_y_outside_reinforcement_elevation
  - `LDR::0A172EB7`  -> tip_outside_envelope_and_supports

## B19

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `36` / `30`
- T18 scored: `28` avg_score=`0.2518`
- Coverage%: `142.86` Ownership%: `28.57` Conflict%: `14.29`
- Owned / Rejected / Elsewhere: `8` / `11` / `0`
- Primary failure cause: **Conflict Resolution** (High)
- Detail: Neighbour/conflict reasons dominate: [('annotation_on_neighbour_side_of_mark', 10), ('tip_outside_envelope_and_supports', 5), ('no_owned_leader_bar_chain', 2)]
- T18 stats: `{'accepted_annotation_count': 3, 'rejected_annotation_count': 6, 'accepted_bar_count': 3, 'rejected_bar_count': 0, 'accepted_leader_count': 2, 'cross_beam_leakage_count': 5}`

Rejected entities:
  - `LDR::4D6F2B85`  -> tip_outside_envelope_and_supports
  - `LDR::056CE421`  -> tip_outside_envelope_and_supports
  - `LDR::1EE8C99E`  -> tip_outside_envelope_and_supports
  - `LDR::027AB042`  -> tip_outside_envelope_and_supports
  - `LDR::C82E1DB9`  -> tip_outside_envelope_and_supports

## B22

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `23` / `21`
- T18 scored: `14` avg_score=`0.5036`
- Coverage%: `131.25` Ownership%: `57.14` Conflict%: `21.43`
- Owned / Rejected / Elsewhere: `8` / `2` / `0`
- Primary failure cause: **Conflict Resolution** (High)
- Detail: Neighbour/conflict reasons dominate: [('annotation_on_neighbour_side_of_mark', 2), ('tip_outside_envelope_and_supports', 1)]
- T18 stats: `{'accepted_annotation_count': 3, 'rejected_annotation_count': 1, 'accepted_bar_count': 3, 'rejected_bar_count': 0, 'accepted_leader_count': 2, 'cross_beam_leakage_count': 1}`

Rejected entities:
  - `LDR::11835717`  -> tip_outside_envelope_and_supports
  - `ANN-bf887457` 4-Y25 -> annotation_on_neighbour_side_of_mark

## B23

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `20` / `20`
- T18 scored: `11` avg_score=`0.6409`
- Coverage%: `250.0` Ownership%: `81.82` Conflict%: `18.18`
- Owned / Rejected / Elsewhere: `9` / `0` / `0`
- Primary failure cause: **Mixed** (Low)
- Detail: No clear ownership failures recorded; residual may be missing entities never discovered
- T18 stats: `{'accepted_annotation_count': 2, 'rejected_annotation_count': 0, 'accepted_bar_count': 6, 'rejected_bar_count': 0, 'accepted_leader_count': 1, 'cross_beam_leakage_count': 0}`

## B29

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `30` / `30`
- T18 scored: `20` avg_score=`0.575`
- Coverage%: `375.0` Ownership%: `65.0` Conflict%: `20.0`
- Owned / Rejected / Elsewhere: `13` / `2` / `0`
- Primary failure cause: **Mixed** (Low)
- Detail: No clear ownership failures recorded; residual may be missing entities never discovered
- T18 stats: `{'accepted_annotation_count': 5, 'rejected_annotation_count': 0, 'accepted_bar_count': 7, 'rejected_bar_count': 0, 'accepted_leader_count': 1, 'cross_beam_leakage_count': 0}`

Rejected entities:
  - `LDR::58F9C249`  -> tip_outside_envelope_and_supports
  - `LDR::F05FF82C`  -> tip_outside_envelope_and_supports

## B42A

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `25` / `25`
- T18 scored: `14` avg_score=`0.6429`
- Coverage%: `166.67` Ownership%: `78.57` Conflict%: `7.14`
- Owned / Rejected / Elsewhere: `11` / `0` / `0`
- Primary failure cause: **Mixed** (Low)
- Detail: No clear ownership failures recorded; residual may be missing entities never discovered
- T18 stats: `{'accepted_annotation_count': 3, 'rejected_annotation_count': 0, 'accepted_bar_count': 6, 'rejected_bar_count': 0, 'accepted_leader_count': 2, 'cross_beam_leakage_count': 0}`

## B45

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `25` / `25`
- T18 scored: `14` avg_score=`0.6429`
- Coverage%: `156.25` Ownership%: `78.57` Conflict%: `14.29`
- Owned / Rejected / Elsewhere: `11` / `0` / `0`
- Primary failure cause: **Mixed** (Low)
- Detail: No clear ownership failures recorded; residual may be missing entities never discovered
- T18 stats: `{'accepted_annotation_count': 3, 'rejected_annotation_count': 0, 'accepted_bar_count': 6, 'rejected_bar_count': 0, 'accepted_leader_count': 2, 'cross_beam_leakage_count': 0}`

## B46

- Has ownership: `True`
- Search method: T18 Beam Ownership Envelope (crop U concrete U annotation_reach)
- Side of mark: `ABOVE_MARK` body_reason=`annotation_nearest_bar_cluster`
- Nearby / Candidates: `35` / `33`
- T18 scored: `20` avg_score=`0.5475`
- Coverage%: `165.0` Ownership%: `70.0` Conflict%: `10.0`
- Owned / Rejected / Elsewhere: `14` / `2` / `0`
- Primary failure cause: **Conflict Resolution** (High)
- Detail: Neighbour/conflict reasons dominate: [('annotation_on_neighbour_side_of_mark', 2), ('tip_outside_envelope_and_supports', 1)]
- T18 stats: `{'accepted_annotation_count': 3, 'rejected_annotation_count': 1, 'accepted_bar_count': 9, 'rejected_bar_count': 0, 'accepted_leader_count': 2, 'cross_beam_leakage_count': 1}`

Rejected entities:
  - `LDR::FE5B8017`  -> tip_outside_envelope_and_supports
  - `ANN-3aa2fdac` 4-Y20 -> annotation_on_neighbour_side_of_mark
