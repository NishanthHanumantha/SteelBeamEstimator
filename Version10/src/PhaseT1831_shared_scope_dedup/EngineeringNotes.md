# T1.8.3.1 Engineering Notes — Shared Scope Deduplication

**MODEL_VERSION:** 9.5.4

## Problem

The DXF contains a single physical Side Face Reinforcement note that governs
B8–B9–B10. The annotation graph may expose that note as more than one
annotation node (different IDs / leaders). T1.8.3 therefore registered two
shared scopes with identical engineering intent:

- Primary B9 → members {B8, B9, B10}
- Primary B10 → members {B8, B9, B10}

Runtime merge already collapsed duplicate **texts**, so rendering stayed
correct. The registry, however, incorrectly listed two shared entries.

## Fix

Registry-stage deduplication only:

```
scope_key = (normalized_text, sorted(member_beams), scope_type)
```

If a key already exists, absorb the duplicate into the surviving scope.
Canonical annotation identity is preserved from the higher-confidence /
higher-Y survivor (matches T1.8.3 merge preference) so effective ownership
and render inputs remain unchanged.

## Non-goals

- No renderer changes
- No ownership-merge semantic changes
- No text-only dedup (independent `Ld` groups stay separate via different
  `member_beams`)
- No edits to T1.7–T1.8.3 production modules
