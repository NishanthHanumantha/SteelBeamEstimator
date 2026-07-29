"""
Phase R.2.0 — Engineering-safe MTEXT text recovery engine.

Replaces the production _strip_mtext() in beam_detail_segmenter.py.

Key behaviour difference from production _strip_mtext():
  OLD: {[^{}]*}  ->  removes entire brace block  ->  engineering text lost
  NEW: brace blocks are opened; inner formatting stripped; text preserved

Example:
    OLD: "{\LS.F.R.- 2-Y10(O.E.F)}"  →  ""          (LOST)
    NEW: "{\LS.F.R.- 2-Y10(O.E.F)}"  →  "S.F.R.- 2-Y10(O.E.F)"  (RECOVERED)

Backward compatibility guarantee:
  All text that was previously cleaned correctly remains unchanged.
  Only brace blocks containing engineering content are affected.
"""
from __future__ import annotations

import re

# ── Pattern components ────────────────────────────────────────────────────────

# Format codes that end with semicolon: \A1; \H3.175x; \fArial|b0|i0|c0|p34;
# [^;{}]* must not cross brace or semicolon boundaries
_FMT_SEMI_INNER = re.compile(r"\\[A-Za-z][^;{}]*;")

# Single-char toggle format codes (no semicolon): \L \l \O \o \K \k
_FMT_TOGGLE = re.compile(r"\\[LlOoKk]")

# Escaped backslash → literal backslash (not meaningful for engineering text)
_FMT_ESC_BS = re.compile(r"\\\\")

# Paragraph break: \P or \p (without semicolon)
_FMT_PARA_NOSEMI = re.compile(r"\\P")

# Original production pattern — WITHOUT the brace removal part — for non-brace content
# This is the exact same regex minus \{[^{}]*\}
_MTEXT_NOBRACE = re.compile(r"\\[A-Za-z][^;]*;|\\\\|\\P|\\p[^;]+;")

# %%X special character codes
_PCT_CODE = re.compile(r"%%[A-Za-z]")

# Signal that brace content is engineering (Y/R/T + digits, @, S.F.R., O.E.F., Ld)
_ENG_SIGNAL = re.compile(
    r"[YyRrTt]\s*\d+|S\.?F\.?R|O\.?E\.?F|\bLd\b|@\s*\d",
    re.IGNORECASE,
)

# Brace block: {content}  — non-nested only (matches production regex scope)
_BRACE_BLOCK = re.compile(r"\{([^{}]*)\}")


def _recover_brace_inner(content: str) -> str:
    """
    Strip AutoCAD formatting inside a brace block; return engineering text.

    If the recovered text contains no engineering signal, return "" to
    preserve backward-compatible behaviour for title / font-change blocks.
    """
    text = _FMT_SEMI_INNER.sub("", content)
    text = _FMT_TOGGLE.sub("", text)
    text = _FMT_ESC_BS.sub("", text)
    text = _FMT_PARA_NOSEMI.sub("", text)
    text = text.strip()
    # Only recover if engineering content is present; otherwise preserve old empty result
    return text if _ENG_SIGNAL.search(text) else ""


class EngineeringTextRecovery:
    """Phase R.2.0 engineering-safe MTEXT text cleaner."""

    @staticmethod
    def clean(raw: str) -> str:
        """
        Engineering-safe drop-in replacement for _strip_mtext().

        Public API is identical: accepts raw DXF text, returns cleaned string.
        """
        if not raw:
            return ""
        # Step 1: process brace blocks — extract engineering text, strip formatting
        text = _BRACE_BLOCK.sub(lambda m: _recover_brace_inner(m.group(1)), raw)
        # Step 2: strip remaining format codes using original production logic
        text = _MTEXT_NOBRACE.sub("", text)
        # Step 3: strip %%X special codes
        text = _PCT_CODE.sub("", text)
        return text.strip()

    @staticmethod
    def old_clean(raw: str) -> str:
        """Replicate the ORIGINAL production _strip_mtext() for comparison."""
        _MTEXT_CODE = re.compile(r"\\[A-Za-z][^;]*;|\\\\|\\P|\\p[^;]+;|\{[^{}]*\}")
        cleaned = _MTEXT_CODE.sub("", raw)
        cleaned = re.sub(r"%%[A-Za-z]", "", cleaned)
        return cleaned.strip()

    @classmethod
    def compare(cls, raw: str) -> dict:
        """Return old vs new cleaning result for a given raw text."""
        old = cls.old_clean(raw)
        new = cls.clean(raw)
        return {
            "raw": raw,
            "old_clean": old,
            "new_clean": new,
            "changed": old != new,
            "recovered": bool(new) and not bool(old),
        }
