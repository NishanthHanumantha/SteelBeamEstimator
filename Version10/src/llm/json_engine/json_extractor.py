"""Extract JSON payloads from Claude text responses."""

from __future__ import annotations

import json
import re
from typing import Any, List, Tuple

from src.llm.json_engine.response_models import JSONExtractionError

_CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class JSONExtractor:
    """Deterministically extract the first valid JSON object from text."""

    def extract(self, response_text: str) -> Any:
        if not response_text or not response_text.strip():
            raise JSONExtractionError("Response text is empty.")

        candidates = self._candidate_strings(response_text)
        errors: List[str] = []
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as exc:
                errors.append(str(exc))
                continue

        raise JSONExtractionError(
            "Unable to extract valid JSON from response. "
            f"Attempts={len(candidates)}; last_error={errors[-1] if errors else 'none'}"
        )

    def _candidate_strings(self, response_text: str) -> List[str]:
        ordered: List[str] = []
        seen: set[str] = set()

        def _add(candidate: str) -> None:
            normalized = candidate.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                ordered.append(normalized)

        _add(response_text)
        for match in _CODE_BLOCK_PATTERN.finditer(response_text):
            _add(match.group(1))

        for block in self._balanced_object_strings(response_text):
            _add(block)

        return ordered

    @staticmethod
    def _balanced_object_strings(text: str) -> List[str]:
        blocks: List[str] = []
        for opener, closer in (("{", "}"), ("[", "]")):
            start = 0
            while True:
                start_index = text.find(opener, start)
                if start_index < 0:
                    break
                for end_index in range(start_index + 1, len(text) + 1):
                    fragment = text[start_index:end_index]
                    if fragment.count(opener) == fragment.count(closer) and fragment.endswith(closer):
                        try:
                            json.loads(fragment)
                            blocks.append(fragment)
                            break
                        except json.JSONDecodeError:
                            continue
                start = start_index + 1
        return blocks
