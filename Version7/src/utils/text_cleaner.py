"""AutoCAD TEXT / MTEXT formatting cleanup for downstream beam extraction."""

import re
from typing import Final

# Braced MTEXT groups — payload after ';' is kept; bare groups are removed.
_MTEXT_FORMAT_GROUP: Final[re.Pattern[str]] = re.compile(r"\{([^{}]*)\}")

# Remaining %% control codes after %%P is handled (U=underline, D=overline).
_PERCENT_CONTROL_CODES: Final[re.Pattern[str]] = re.compile(r"%%[UD]", re.IGNORECASE)


def _strip_mtext_groups(text: str) -> str:
    """Unwrap ``{\\format;payload}`` groups, keeping payload text."""
    def _unwrap_group(match: re.Match[str]) -> str:
        inner = match.group(1)
        if ";" in inner:
            return inner.split(";", 1)[1]
        return ""

    return _MTEXT_FORMAT_GROUP.sub(_unwrap_group, text)


def clean_dxf_text(raw_text: str) -> str:
    """
    Remove AutoCAD formatting from raw TEXT / MTEXT content.

    Supported transformations:
        - ``%%U`` — removed (underline toggle)
        - ``%%D`` — removed (overline toggle)
        - ``%%P`` — replaced with newline
        - ``{\\...}`` braced formatting groups — removed

    Args:
        raw_text: Unprocessed string from the DXF entity.

    Returns:
        Cleaned text suitable for beam label parsing.
    """
    if not raw_text:
        return ""

    text = str(raw_text)
    text = _strip_mtext_groups(text)
    text = re.sub(r"%%P", "\n", text, flags=re.IGNORECASE)
    text = _PERCENT_CONTROL_CODES.sub("", text)
    return text.strip()


class TextCleaner:
    """Reusable cleaner that returns raw/clean pairs for entity records."""

    def clean(self, raw_text: str) -> str:
        """Return cleaned text from a raw DXF string."""
        return clean_dxf_text(raw_text)

    def as_pair(self, raw_text: str) -> tuple[str, str]:
        """Return ``(raw_text, clean_text)`` for JSON serialization."""
        raw = str(raw_text) if raw_text else ""
        return raw, self.clean(raw)
