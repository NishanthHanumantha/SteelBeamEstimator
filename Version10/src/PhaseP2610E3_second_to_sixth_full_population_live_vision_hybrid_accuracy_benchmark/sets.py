"""Set membership tokens for Second–Sixth discovery. First is excluded. No outcome tables."""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

from .config import EXCLUDED_SET_KEYS, INCLUDED_SET_KEYS, SET_TOKENS


def included_set_keys() -> Tuple[str, ...]:
    return INCLUDED_SET_KEYS


def excluded_set_keys() -> Tuple[str, ...]:
    return EXCLUDED_SET_KEYS


def tokens_for(set_key: str) -> Tuple[str, ...]:
    return SET_TOKENS.get(str(set_key), ())


def competing_tokens(set_key: str) -> Tuple[str, ...]:
    out = []
    for key, toks in SET_TOKENS.items():
        if key == set_key:
            continue
        out.extend(toks)
    return tuple(out)


def name_matches_set(name: str, set_key: str) -> bool:
    low = str(name or "").lower().replace("\\", "/")
    own = tokens_for(set_key)
    if not own or not any(tok in low for tok in own):
        return False
    for other_key, toks in SET_TOKENS.items():
        if other_key == set_key:
            continue
        folder_hits = any(
            f"/{tok}_set" in low or f"/{tok} set" in low or f"qa2_{tok}" in low or f"{tok}_set_drawings" in low
            for tok in toks
        )
        if folder_hits and not any(f"/{t}_set" in low or f"qa2_{t}" in low or f"{t}_set_drawings" in low for t in own):
            return False
    return True


def classify_folder_name(name: str, *, keys: Optional[Iterable[str]] = None) -> Optional[str]:
    low = str(name or "").lower()
    order = tuple(keys) if keys is not None else INCLUDED_SET_KEYS + EXCLUDED_SET_KEYS
    hits = [key for key in order if any(tok in low for tok in tokens_for(key))]
    if len(hits) == 1:
        return hits[0]
    if "first" in low or "1st" in low:
        return "First"
    return hits[0] if hits else None


def drawing_set_label(set_key: str) -> str:
    return f"{set_key} Set Drawings"


def is_excluded_set(set_key: str) -> bool:
    return str(set_key) in EXCLUDED_SET_KEYS


__all__ = [
    "classify_folder_name",
    "competing_tokens",
    "drawing_set_label",
    "excluded_set_keys",
    "included_set_keys",
    "is_excluded_set",
    "name_matches_set",
    "tokens_for",
]
