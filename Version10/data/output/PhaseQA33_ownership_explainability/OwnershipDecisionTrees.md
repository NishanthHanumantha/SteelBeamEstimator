# QA.3.3 Ownership Decision Trees

### B14 Decision Tree Summary

**LDR::FC909F97** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B14'], 'winning_beam': 'B14', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**ANN-1ccca39c** (Chain) text=4-Y16

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B14'], 'winning_beam': 'B14', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**BAR::SYN::B14::1213668** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B14'], 'winning_beam': 'B14', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B14', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B14::121366D** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B14'], 'winning_beam': 'B14', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B14', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B14::11C88FB** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B14'], 'winning_beam': 'B14', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B14', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B14::11C891E** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B14'], 'winning_beam': 'B14', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B14', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**


### B15 Decision Tree Summary

**LDR::798CE590** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::749B70DC** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::8534C4B8** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::167CC70D** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**ANN-9d3b965f** (Chain) text=4-Y20

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R3_ANNOTATION_VIA_CHAIN'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R3_ANNOTATION_VIA_CHAIN', 'result': False, 'meaning': 'Annotation ownership only via Leader→Bar (or DESCRIBES bar)', 'ownership_reason': 'no_owned_leader_bar_chain', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'no_owned_leader_bar_chain'}
  => **REJECTED**

**ANN-d910b071** (Chain) text=2-Y16

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R3_ANNOTATION_VIA_CHAIN'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R3_ANNOTATION_VIA_CHAIN', 'result': False, 'meaning': 'Annotation ownership only via Leader→Bar (or DESCRIBES bar)', 'ownership_reason': 'no_owned_leader_bar_chain', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'no_owned_leader_bar_chain'}
  => **REJECTED**

**ANN-66b919f1** (Chain) text=4-Y25

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**ANN-c569e3e8** (Chain) text=7-Y20

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**BAR::SYN::B15::11C88FB** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B15', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B15::12136C0** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B15', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B15::11C8922** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B15', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**LDR::4A5B63BC** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R2_LEADER_TIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R2_LEADER_TIP'}, {'name': 'rule:R5_NEIGHBOUR_REJECT', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R2_LEADER_TIP', 'result': True, 'meaning': 'Leader tip inside Envelope or support extension'}
  - {'step': 'rule_pass:R5_NEIGHBOUR_REJECT', 'result': True, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B15'], 'winning_beam': 'B15', 'margin': None, 'reason_winner_selected': 'tip_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B15', 'accepted': True, 'ownership_reason': 'tip_inside_concrete_envelope'}
  => **OWNED**


### B16 Decision Tree Summary

**LDR::7A1FFD68** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::50092321** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::DE845955** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::49842AC8** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**ANN-26e9834b** (Chain) text=4-Y20

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**ANN-9cfeb712** (Chain) text=4-Y25

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**ANN-b98a0bbe** (Chain) text=2-Y16

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**BAR::SYN::B16::1213735** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B16', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B16::1213781** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B16', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B16::11C88FB** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B16', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B16::11C894B** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B16'], 'winning_beam': 'B16', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B16', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**


### B18 Decision Tree Summary

**BAR::59B0AF37** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'bar_y_outside_reinforcement_elevation', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'bar_y_outside_reinforcement_elevation'}
  => **REJECTED**

**BAR::A5E16B4D** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'bar_y_outside_reinforcement_elevation', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'bar_y_outside_reinforcement_elevation'}
  => **REJECTED**

**BAR::7CD782B5** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'bar_y_outside_reinforcement_elevation', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'bar_y_outside_reinforcement_elevation'}
  => **REJECTED**

**BAR::1D706A9A** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'bar_y_outside_reinforcement_elevation', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'bar_y_outside_reinforcement_elevation'}
  => **REJECTED**

**LDR::0A172EB7** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::FCC2C11A** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::77270BAC** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::1EDDB869** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**BAR::3EBA65BF** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B18', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**LDR::E476EF66** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R2_LEADER_TIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R2_LEADER_TIP'}, {'name': 'rule:R5_NEIGHBOUR_REJECT', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R2_LEADER_TIP', 'result': True, 'meaning': 'Leader tip inside Envelope or support extension'}
  - {'step': 'rule_pass:R5_NEIGHBOUR_REJECT', 'result': True, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'tip_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B18', 'accepted': True, 'ownership_reason': 'tip_inside_concrete_envelope'}
  => **OWNED**

**LDR::D9243008** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R2_LEADER_TIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R2_LEADER_TIP'}, {'name': 'rule:R5_NEIGHBOUR_REJECT', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R2_LEADER_TIP', 'result': True, 'meaning': 'Leader tip inside Envelope or support extension'}
  - {'step': 'rule_pass:R5_NEIGHBOUR_REJECT', 'result': True, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'tip_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B18', 'accepted': True, 'ownership_reason': 'tip_inside_concrete_envelope'}
  => **OWNED**

**ANN-5731b151** (Chain) text=4-Y20

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R3_ANNOTATION_VIA_CHAIN', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R3_ANNOTATION_VIA_CHAIN'}, {'name': 'rule:R5_NEIGHBOUR_REJECT', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R3_ANNOTATION_VIA_CHAIN', 'result': True, 'meaning': 'Annotation ownership only via Leader→Bar (or DESCRIBES bar)'}
  - {'step': 'rule_pass:R5_NEIGHBOUR_REJECT', 'result': True, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B18'], 'winning_beam': 'B18', 'margin': None, 'reason_winner_selected': 'leader_bar_chain_owned'}
  - {'step': 'final_ownership', 'owned_by': 'B18', 'accepted': True, 'ownership_reason': 'leader_bar_chain_owned'}
  => **OWNED**


### B19 Decision Tree Summary

**LDR::4D6F2B85** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::056CE421** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::1EE8C99E** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::027AB042** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::C82E1DB9** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**ANN-ceb59daf** (Chain) text=7-Y20

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R3_ANNOTATION_VIA_CHAIN'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R3_ANNOTATION_VIA_CHAIN', 'result': False, 'meaning': 'Annotation ownership only via Leader→Bar (or DESCRIBES bar)', 'ownership_reason': 'no_owned_leader_bar_chain', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'no_owned_leader_bar_chain'}
  => **REJECTED**

**ANN-2be5bdb3** (Chain) text=4L-Y10@100/150/100C/C

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**ANN-200a87b5** (Chain) text=4-Y25

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**BAR::SYN::B19::1234487** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B19', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B19::1234488** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B19', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B19::1240D04** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B19', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**LDR::83E16CC5** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R2_LEADER_TIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R2_LEADER_TIP'}, {'name': 'rule:R5_NEIGHBOUR_REJECT', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R2_LEADER_TIP', 'result': True, 'meaning': 'Leader tip inside Envelope or support extension'}
  - {'step': 'rule_pass:R5_NEIGHBOUR_REJECT', 'result': True, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B19'], 'winning_beam': 'B19', 'margin': None, 'reason_winner_selected': 'tip_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B19', 'accepted': True, 'ownership_reason': 'tip_inside_concrete_envelope'}
  => **OWNED**


### B22 Decision Tree Summary

**LDR::11835717** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B22'], 'winning_beam': 'B22', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**ANN-bf887457** (Chain) text=4-Y25

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B22'], 'winning_beam': 'B22', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**BAR::SYN::B22::1234489** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B22'], 'winning_beam': 'B22', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B22', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B22::123449F** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B22'], 'winning_beam': 'B22', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B22', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B22::123449E** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B22'], 'winning_beam': 'B22', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B22', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**LDR::23D45FBD** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R2_LEADER_TIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R2_LEADER_TIP'}, {'name': 'rule:R5_NEIGHBOUR_REJECT', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R2_LEADER_TIP', 'result': True, 'meaning': 'Leader tip inside Envelope or support extension'}
  - {'step': 'rule_pass:R5_NEIGHBOUR_REJECT', 'result': True, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B22'], 'winning_beam': 'B22', 'margin': None, 'reason_winner_selected': 'tip_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B22', 'accepted': True, 'ownership_reason': 'tip_inside_concrete_envelope'}
  => **OWNED**


### B23 Decision Tree Summary

**BAR::SYN::B23::1234480** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B23'], 'winning_beam': 'B23', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B23', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B23::123447D** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B23'], 'winning_beam': 'B23', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B23', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B23::123449F** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B23'], 'winning_beam': 'B23', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B23', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B23::123449D** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B23'], 'winning_beam': 'B23', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B23', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**


### B29 Decision Tree Summary

**LDR::58F9C249** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B29'], 'winning_beam': 'B29', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**LDR::F05FF82C** (Leader) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B29'], 'winning_beam': 'B29', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**BAR::SYN::B29::1241225** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B29'], 'winning_beam': 'B29', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B29', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B29::1239C3E** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B29'], 'winning_beam': 'B29', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B29', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B29::1239BC9** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B29'], 'winning_beam': 'B29', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B29', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B29::1239BDC** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B29'], 'winning_beam': 'B29', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B29', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**


### B42A Decision Tree Summary

**BAR::SYN::B42A::1230CC6** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B42A'], 'winning_beam': 'B42A', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B42A', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B42A::1230CC8** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B42A'], 'winning_beam': 'B42A', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B42A', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B42A::1230CD5** (Bar) text=None

  - {'step': 'nearby', 'result': False}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B42A'], 'winning_beam': 'B42A', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B42A', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B42A::1230CC5** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B42A'], 'winning_beam': 'B42A', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B42A', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**


### B45 Decision Tree Summary

**BAR::SYN::B45::11CCBA5** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B45'], 'winning_beam': 'B45', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B45', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B45::11CCBA7** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B45'], 'winning_beam': 'B45', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B45', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B45::11CCBA4** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B45'], 'winning_beam': 'B45', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B45', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B45::11CCBAE** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B45'], 'winning_beam': 'B45', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B45', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**


### B46 Decision Tree Summary

**LDR::FE5B8017** (Leader) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R2_LEADER_TIP'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R2_LEADER_TIP', 'result': False, 'meaning': 'Leader tip inside Envelope or support extension', 'ownership_reason': 'tip_outside_envelope_and_supports', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B46'], 'winning_beam': 'B46', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'tip_outside_envelope_and_supports'}
  => **REJECTED**

**ANN-3aa2fdac** (Chain) text=4-Y20

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.0, 'score_breakdown': {'components': [{'name': 'rejection', 'raw_score': 0.0, 'normalised_score': 0.0, 'weight': 1.0, 'contribution': 0.0, 'detail': 'R5_NEIGHBOUR_REJECT'}], 'computed_total': 0.0, 'persisted_ownership_score': 0.0, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_reject:R5_NEIGHBOUR_REJECT', 'result': False, 'meaning': 'Reject chain if bar/leader resolves outside envelope / neighbour side', 'ownership_reason': 'annotation_on_neighbour_side_of_mark', 'neighbour_beam_source': None}
  - {'step': 'conflict_resolution', 'competing_beams': ['B46'], 'winning_beam': 'B46', 'margin': None, 'reason_winner_selected': 'highest_score_among_considering_beams_or_sole_accepter'}
  - {'step': 'final_ownership', 'owned_by': None, 'accepted': False, 'ownership_reason': 'annotation_on_neighbour_side_of_mark'}
  => **REJECTED**

**BAR::SYN::B46::11CCD91** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B46'], 'winning_beam': 'B46', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B46', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B46::11CCD93** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B46'], 'winning_beam': 'B46', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B46', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B46::11CCD90** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B46'], 'winning_beam': 'B46', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B46', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

**BAR::SYN::B46::11CCD9A** (Bar) text=None

  - {'step': 'nearby', 'result': True}
  - {'step': 'candidate', 'result': True}
  - {'step': 'scored', 'result': True, 'total_ownership_score': 0.65, 'score_breakdown': {'components': [{'name': 'base_acceptance', 'raw_score': 0.55, 'normalised_score': 0.55, 'weight': 1.0, 'contribution': 0.55, 'detail': 'T18 score_from_rules base'}, {'name': 'rule:R1_PHYSICAL_BAR', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R1_PHYSICAL_BAR'}, {'name': 'rule:R6_VERTICAL_OWNERSHIP', 'raw_score': 0.05, 'normalised_score': 0.05, 'weight': 1.0, 'contribution': 0.05, 'detail': 'R6_VERTICAL_OWNERSHIP'}], 'computed_total': 0.65, 'persisted_ownership_score': 0.65, 'score_matches_persisted': True, 'formula': '0.0 if rejected else min(1.0, 0.55 + 0.05 * n_accepted_rules)'}}
  - {'step': 'rule_pass:R1_PHYSICAL_BAR', 'result': True, 'meaning': 'PhysicalBar centre inside Beam Envelope'}
  - {'step': 'rule_pass:R6_VERTICAL_OWNERSHIP', 'result': True, 'meaning': 'PhysicalBar Y in beam reinforcement elevation'}
  - {'step': 'conflict_resolution', 'competing_beams': ['B46'], 'winning_beam': 'B46', 'margin': None, 'reason_winner_selected': 'bar_inside_concrete_envelope'}
  - {'step': 'final_ownership', 'owned_by': 'B46', 'accepted': True, 'ownership_reason': 'bar_inside_concrete_envelope'}
  => **OWNED**

