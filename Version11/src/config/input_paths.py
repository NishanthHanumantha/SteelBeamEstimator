"""Canonical input paths for Version3 (copied from Version2 outputs)."""

from pathlib import Path

INPUT_ROOT = Path("data/input")


class InputPaths:
    """Resolve reference input files under data/input/."""

    def __init__(self, root: Path = INPUT_ROOT) -> None:
        self.root = root

    @property
    def beam_cells(self) -> Path:
        return self.root / "beam_cells.json"

    @property
    def beam_sketches(self) -> Path:
        return self.root / "beam_sketches.json"

    @property
    def header_occurrences(self) -> Path:
        return self.root / "header_occurrences.json"

    @property
    def sketch_ownership(self) -> Path:
        return self.root / "sketch_ownership.json"

    @property
    def engineering_annotations_final(self) -> Path:
        return self.root / "engineering_annotations_final.json"

    @property
    def engineering_dataset_d17f(self) -> Path:
        return self.root / "engineering_dataset_phase_d17f.json"

    @property
    def parsed_annotations_master(self) -> Path:
        return self.root / "parsed_annotations_master.json"

    @property
    def beam_annotations_extended(self) -> Path:
        return self.root / "beam_annotations_extended.json"

    @property
    def annotation_types_extended(self) -> Path:
        return self.root / "annotation_types_extended.json"
