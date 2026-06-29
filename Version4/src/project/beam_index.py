"""Beam mark index for constant-time context lookup within a Drawing Set."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class BeamIndex:
    """Maps beam marks to engineering context IDs for a drawing set."""

    def __init__(
        self,
        drawing_set_id: str,
        mark_to_context: Dict[str, str],
        contexts_by_id: Dict[str, dict[str, Any]],
    ) -> None:
        self._drawing_set_id = drawing_set_id
        self._mark_to_context = dict(mark_to_context)
        self._contexts_by_id = dict(contexts_by_id)

    @property
    def drawing_set_id(self) -> str:
        return self._drawing_set_id

    def get_context_id(self, beam_mark: str) -> Optional[str]:
        return self._mark_to_context.get(str(beam_mark).upper())

    def get_beam_context(self, beam_mark: str) -> Optional[dict[str, Any]]:
        cid = self.get_context_id(beam_mark)
        if not cid:
            return None
        return self._contexts_by_id.get(cid)

    def contains(self, beam_mark: str) -> bool:
        return str(beam_mark).upper() in self._mark_to_context

    def count(self) -> int:
        return len(self._mark_to_context)

    def list_marks(self) -> List[str]:
        return sorted(self._mark_to_context.keys())

    def to_dict(self) -> dict[str, Any]:
        return {
            "drawing_set_id": self._drawing_set_id,
            "beam_count": self.count(),
            "index": dict(self._mark_to_context),
            "marks": self.list_marks(),
        }

    def lookup_registry(self) -> List[dict[str, Any]]:
        return [
            {
                "beam_mark": mark,
                "context_id": self._mark_to_context[mark],
                "beam_id": self._contexts_by_id.get(self._mark_to_context[mark], {}).get("beam_id"),
            }
            for mark in self.list_marks()
        ]
