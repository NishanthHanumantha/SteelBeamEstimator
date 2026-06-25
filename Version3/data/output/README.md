# Version3 Pipeline Outputs

Generated artifacts live under `data/output/`, grouped by phase subdirectory.

Canonical paths are defined in `src/config/output_paths.py` (`OutputPaths`).

## Reference baseline (copied from Version2)

These JSON files are **reference inputs** for development and comparison. Re-run upstream phases to regenerate.

| Folder | Contents |
|--------|----------|
| `phase_a/` | Framing beams |
| `phase_b/` | Reinforcement headers |
| `phase_c/` | Beam cells |
| `phase_c5/` | Sketch ownership, header occurrences |
| `phase_c_debug/` | Beam sketch geometry |
| `phase_d17g/` | SFR discovery audit summary (read-only reference) |

## Version3 development focus

New outputs for beam group detection and shared ownership will be added here as phases are implemented.

Debug DXF files are generated on demand by runners; they are not stored in the baseline copy.
