# T1.8.3 Architecture — Shared Engineering Ownership

**MODEL_VERSION:** 9.5.3

## Problem

Nearest-beam ownership is wrong for annotations that describe a continuous
engineering condition across multiple beams (e.g. side-face reinforcement on
B8–B9–B10).

## Workflow

```
AnnotationGraph + BeamOwnership + geometry envelopes
        |
        v
shared_scope_detector   (SFR via T1.7 classify_annotation_text)
        |
        v
engineering_scope_builder  (collinear / gap / depth / tip rules)
        |
        v
multi_owner_assignment     (SharedEngineeringAnnotation)
        |
        v
shared_annotation_registry
        |
        v
ownership_merger           (owned + shared → effective)
        |
        v
shared_render_adapter      (runtime scoped graph for render host)
        |
        v
T1.8.2 adaptive extent + T1.8.1 ownership renderer  (imported, unmodified)
        |
        v
QA / Diff / RenderedBeams
```

## Scope types (`EngineeringScopeType`)

| Type | Active in 9.5.3 |
|------|-----------------|
| SIDE_FACE_REINFORCEMENT | Yes |
| DEVELOPMENT_LENGTH | Enum only |
| CONTINUATION_REINFORCEMENT | Enum only |
| CURTAILMENT | Enum only |
| SUPPORT_REINFORCEMENT | Enum only |
| SHARED_BARS | Enum only |

## SFR sharing rules

1. Beam axes approximately collinear (`mark_y` within 150 mm)
2. Neighbouring X-gap below 800 mm
3. Depth difference within 120 mm
4. Leader tip inside shared group envelope
5. Text classified as SideFaceReinforcement
6. No exclusive conflict (additive shared list; owned ids not duplicated)

## Data model

```
SharedEngineeringAnnotation
  annotation_id, annotation_text, leader_ids
  scope_type, owner_beams[], confidence, reason

EngineeringScope
  scope_id, scope_type, member_beams[], member_annotations[]
  confidence, reason, shared
```

Per beam (runtime merge only):

```
owner_annotations   ← T1.8 accepted (unchanged)
shared_annotations  ← additive
effective_annotations = owned ∪ shared
```
