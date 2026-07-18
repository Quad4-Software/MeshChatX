# SPDX-License-Identifier: 0BSD
"""Redact sensitive fragments from diagnostic / bug-report log text."""

from __future__ import annotations

import re

# Absolute Unix/Windows path-like tokens (kept conservative to avoid eating hex).
_ABS_PATH_RE = re.compile(
    r"(?:"
    r"(?:/(?:home|Users|tmp|var|etc|opt|usr|root|run|mnt|media|data|srv|private|"
    r"Volumes|Library|Applications)[^\s\"']*)"
    r"|(?:[A-Za-z]:\\[^\s\"']+)"
    r"|(?:\\\\[^\s\"']+)"
    r")",
    re.IGNORECASE,
)

# Full 32-byte hex hashes (RNS destination / identity). Partial prefixes stay.
_FULL_HEX_HASH_RE = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{64})(?![0-9a-fA-F])")

# Private-key-ish long hex blobs (>= 96 hex chars continuous).
_LONG_HEX_RE = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{96,})(?![0-9a-fA-F])")

# Email-ish tokens.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# IPv4 addresses (not link-local mesh addressing; UI logs should not leak host IPs by default).
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
)

# PEM private key / certificate blocks.
_PEM_RE = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----",
    re.IGNORECASE,
)

# Bearer / JWT-ish tokens and common secret assignments.
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-+=/]{8,}", re.IGNORECASE)
_BASIC_AUTH_RE = re.compile(r"\bBasic\s+[A-Za-z0-9+/=]{8,}", re.IGNORECASE)
_SECRET_ASSIGN_RE = re.compile(
    r"\b(?:alias_identity_private_key|private_key|session|password|passwd|token|"
    r"api[_-]?key|csrf|authorization)\s*[:=]\s*\S+",
    re.IGNORECASE,
)

REDACTED = "[redacted]"


def redact_diagnostic_text(text: str) -> str:
    """Return text with paths, full hashes, emails, and IPv4s replaced.

    Partial destination hashes (shorter than 64 hex chars) are left alone so
    operators can still correlate short display prefixes.
    """
    if not text:
        return text
    out = _PEM_RE.sub(REDACTED, text)
    out = _ABS_PATH_RE.sub(REDACTED, out)
    out = _LONG_HEX_RE.sub(REDACTED, out)
    out = _FULL_HEX_HASH_RE.sub(REDACTED, out)
    out = _EMAIL_RE.sub(REDACTED, out)
    out = _IPV4_RE.sub(REDACTED, out)
    out = _BEARER_RE.sub(f"Bearer {REDACTED}", out)
    out = _BASIC_AUTH_RE.sub(f"Basic {REDACTED}", out)
    out = _SECRET_ASSIGN_RE.sub(REDACTED, out)
    return out
